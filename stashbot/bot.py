# -*- coding: utf-8 -*-
#
# This file is part of bd808's stashbot application
# Copyright (C) 2015 Bryan Davis and contributors
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
"""IRC bot"""

import elasticsearch
import irc.bot
import irc.buffer
import irc.client
import irc.strings
import ldap
import re
import time

from . import phab

RE_STYLE = re.compile(r'[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?')
RE_PHAB = re.compile(r'\b(T\d+)\b')
RE_PHAB_NOURL = re.compile(r'(?:^|[^/%])\b([DMPT]\d+)\b')


class Stashbot(irc.bot.SingleServerIRCBot):
    def __init__(self, config, logger):
        """Create bot.

        :param config: Dict of configuration values
        :param logger: Logger
        """
        self.config = config
        self.logger = logger

        self.es = elasticsearch.Elasticsearch(
            self.config['elasticsearch']['servers'],
            **self.config['elasticsearch']['options']
        )

        self.phab = phab.Client(
            self.config['phab']['url'],
            self.config['phab']['user'],
            self.config['phab']['key']
        )

        self.ldap = ldap.initialize(self.config['ldap']['uri'])
        self.projects = None

        # Ugh. A UTF-8 only world is a nice dream but the real world is all
        # yucky and full of legacy encoding issues that should not crash my
        # bot.
        irc.buffer.LenientDecodingLineBuffer.errors = 'replace'
        irc.client.ServerConnection.buffer_class = \
            irc.buffer.LenientDecodingLineBuffer

        super(Stashbot, self).__init__(
            [(self.config['irc']['server'], self.config['irc']['port'])],
            self.config['irc']['nick'],
            self.config['irc']['realname']
        )

        # Setup a connection check ping
        self.pings = 0
        self.connection.execute_every(300, self.do_ping)

    def get_version(self):
        return 'Stashbot'

    def on_pong(self, conn, event):
        self.pings = 0

    def on_nicknameinuse(self, conn, event):
        nick = conn.get_nickname()
        self.logger.warning('Requested nick "%s" in use', nick)
        conn.nick(nick + '_')
        if 'password' in self.config['irc']:
            conn.execute_delayed(30, self.do_reclaim_nick)

    def on_welcome(self, conn, event):
        self.logger.info('Connected to server %s', conn.get_server_name())
        if 'password' in self.config['irc']:
            self.do_identify()
        else:
            conn.execute_delayed(1, self.do_join)

    def on_join(self, conn, event):
        nick = event.source.nick
        if nick == conn.get_nickname():
            self.logger.info('Joined %s', event.target)

    def on_error(self, conn, event):
        self.logger.warning(str(event))
        conn.disconnect()

    def on_privnotice(self, conn, event):
        self.logger.warning(str(event))
        msg = event.arguments[0]
        if event.source.nick == 'NickServ':
            if 'NickServ identify' in msg:
                self.logger.info('Authentication requested by Nickserv')
                if 'password' in self.config['irc']:
                    self.do_identify()
                else:
                    self.logger.error('No password in config!')
                    self.die()
            elif 'You are now identified' in msg:
                self.logger.debug('Authenticating succeeded')
                conn.execute_delayed(1, self.do_join)
            elif 'Invlid password' in msg:
                self.logger.error('Password invalid. Check your config!')
                self.die()

    def on_pubnotice(self, conn, event):
        self.logger.warning(str(event))

    def on_pubmsg(self, conn, event):
        # Log all public channel messages we receive
        doc = self._event_to_doc(conn, event)
        self.do_logmsg(conn, event, doc)

        msg = event.arguments[0]
        if ('ignore' in self.config['irc'] and
            self._clean_nick(doc['nick']) in self.config['irc']['ignore']
        ):
            return

        # Look for special messages
        if msg.startswith('!log '):
            self.do_banglog(conn, event, doc)

        elif msg.startswith('!bash '):
            self.do_bash(conn, event, doc)

        if (event.target not in self.config['phab'].get('notin', []) and
            'echo' in self.config['phab'] and
            RE_PHAB_NOURL.search(msg)
        ):
            self.do_phabecho(conn, event, doc)

    def on_privmsg(self, conn, event):
        msg = event.arguments[0]
        if msg.startswith('!bash '):
            doc = self._event_to_doc(conn, event)
            self.do_bash(conn, event, doc)
        else:
            self._respond(conn, event, event.arguments[0][::-1])

    def on_kick(self, conn, event):
        """Attempt to rejoin if kicked from a channel."""
        nick = event.arguments[0]
        channel = event.target
        if nick == conn.get_nickname():
            self.logger.warn(
                'Kicked from %s by %s', channel, event.source.nick)
            conn.execute_delayed(30, conn.join, (channel,))

    def on_bannedfromchan(self, conn, event):
        """Attempt to rejoin if banned from a channel."""
        self.logger.warning(str(event))
        conn.execute_delayed(60, conn.join, (event.arguments[0],))

    def do_ping(self):
        """Send a ping or disconnect if too many pings are outstanding."""
        if self.pings >= 2:
            self.logger.warning('Connection timed out. Disconnecting.')
            self.disconnect()
            self.pings = 0
        else:
            try:
                self.connection.ping('keep-alive')
                self.pings += 1
            except irc.client.ServerNotConnectedError:
                pass

    def do_identify(self):
        """Send NickServ our username and password."""
        self.logger.info('Authentication requested by Nickserv')
        self.connection.privmsg('NickServ', 'identify %s %s' % (
            self.config['irc']['nick'], self.config['irc']['password']))

    def do_join(self, channels=None):
        """Join the next channel in our join list."""
        if channels is None:
            channels = self.config['irc']['channels']
        try:
            car, cdr = channels[0], channels[1:]
        except (IndexError, TypeError):
            self.logger.exception('Failed to find channel to join.')
        else:
            self.logger.info('Joining %s', car)
            self.connection.join(car)
            if cdr:
                self.connection.execute_delayed(1, self.do_join, (cdr,))

    def do_reclaim_nick(self):
        nick = self.connection.get_nickname()
        if nick != self.config['irc']['nick']:
            self.connection.nick(self.config['irc']['nick'])

    def do_logmsg(self, conn, event, doc):
        """Log an IRC channel message to Elasticsearch."""
        fmt = self.config['elasticsearch']['index']
        self._index(
            index=time.strftime(fmt, time.gmtime()),
            doc_type='irc', body=doc)

    def do_banglog(self, conn, event, doc):
        """Process a !log message"""
        bang = dict(doc)
        channel = bang['channel']
        # Trim '!log ' from the front of the message
        msg = bang['message'][5:]
        bang['type'] = 'sal'

        if channel == '#wikimedia-labs':
            project, msg = msg.split(None, 1)
            bang['project'] = project
            bang['message'] = msg
            if project not in self._getProjects():
                self.logger.warning('Invalid project %s', project)
                tool = 'tools.%s' % project
                if tool in self._getProjects():
                    self._respond(
                        conn,
                        event,
                        'Did you mean %s instead of %s?' % (tool, project)
                    )
                return

            if project == 'deployment-prep':
                bang['project'] = 'releng'
                if self._clean_nick(bang['nick']) != 'krenair':
                    # Stop whining at Alex.
                    self._respond(
                        conn,
                        event,
                        'Please !log in #wikimedia-releng for beta cluster SAL'
                    )

        elif channel == '#wikimedia-releng':
            bang['project'] = 'releng'
            bang['message'] = msg

        elif channel == '#wikimedia-analytics':
            bang['project'] = 'analytics'
            bang['message'] = msg

        elif channel in ['#wikimedia-operations', '#wikimedia-fundraising']:
            bang['project'] = 'production'
            bang['message'] = msg
            if bang['nick'] == 'logmsgbot':
                nick, msg = msg.split(None, 1)
                bang['nick'] = nick
                bang['message'] = msg

        else:
            self.logger.warning(
                '!log message on unexpected channel %s', channel)
            self._respond(conn, event, 'Not expecting to hear !log here')
            return

        ret = self._index(index='sal', doc_type='sal', body=bang)

        if ('phab' in self.config['sal'] and
            'created' in ret and ret['created'] is True
        ):
            m = RE_PHAB.findall(bang['message'])
            msg = self.config['sal']['phab'] % dict(
                {'href': self.config['sal']['view_url'] % ret['_id']},
                **bang
            )
            for task in m:
                try:
                    self.phab.comment(task, msg)
                except:
                    self.logger.exception('Failed to add note to phab task')

    def _getProjects(self):
        """Get a list of valid Labs projects"""
        if self.projects and self.projects[0] + 300 > time.time():
            # Expire cache
            self.projects = None

        if self.projects is None:
            projects = self._getLdapNames('projects')
            servicegroups = self._getLdapNames('servicegroups')
            self.projects = (time.time(), projects + servicegroups)

        return self.projects[1]

    def _getLdapNames(self, ou):
        dn = 'ou=%s,%s' % (ou, self.config['ldap']['base'])
        data = self.ldap.search_s(
            dn,
            ldap.SCOPE_SUBTREE,
            '(objectclass=groupofnames)',
            attrlist=['cn']
        )
        if data:
            return [g[1]['cn'][0] for g in data]
        else:
            self.logger.error('Failed to get LDAP data for %s', dn)
            return []

    def _clean_nick(self, nick):
        """Remove common status indicators and normlize to lower case."""
        return nick.split('|', 1)[0].rstrip('`_').lower()

    def do_bash(self, conn, event, doc):
        """Process a !bash message"""
        bash = dict(doc)
        # Trim '!bash ' from the front of the message
        msg = bash['message'][6:]
        # Expand tabs to line breaks
        bash['message'] = msg.replace("\t", "\n").strip()
        bash['type'] = 'bash'
        bash['up_votes'] = 0
        bash['down_votes'] = 0
        bash['score'] = 0
        # Remove unneeded irc fields
        del bash['user']
        del bash['channel']
        del bash['server']
        del bash['host']

        ret = self._index(index='bash', doc_type='bash', body=bash)

        if 'created' in ret and ret['created'] is True:
            self._respond(conn, event,
                '%s: Stored quip at %s' % (
                    event.source.nick,
                    self.config['bash']['view_url'] % ret['_id']
                )
            )
        else:
            self.logger.error('Failed to save document: %s', ret)
            self._respond(conn, event,
                '%s: Yuck. Something blew up when I tried to save that.' % (
                    event.source.nick,
                )
            )

    def do_phabecho(self, conn, event, doc):
        """Give links to Phabricator tasks"""
        for task in set(RE_PHAB_NOURL.findall(doc['message'])):
            try:
                info = self.phab.taskInfo(task)
            except:
                self.logger.exception('Failed to lookup info for %s', task)
            else:
                self._respond(conn, event, self.config['phab']['echo'] % info)

    def _respond(self, conn, event, msg):
        to = event.target
        if to == self.connection.get_nickname():
            to = event.source.nick
        conn.privmsg(to, msg.replace("\n", ' '))

    def _event_to_doc(self, conn, event):
        """Make an Elasticsearch document from an IRC event."""
        return {
            'message': RE_STYLE.sub('', event.arguments[0]),
            '@timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'type': 'irc',
            'user': event.source,
            'channel': event.target,
            'nick': event.source.nick,
            'server': conn.get_server_name(),
            'host': event.source.host,
        }

    def _index(self, index, doc_type, body):
        """Store a document in Elasticsearch."""
        try:
            return self.es.index(index=index, doc_type=doc_type, body=body,
                                 consistency="one")
        except elasticsearch.ConnectionError as e:
            self.logger.exception(
                'Failed to log to elasticsearch: %s', e.error)
            return {}
