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
import re
import time

RE_STYLE = re.compile(r'[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?')

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

        # Ugh. A UTF-8 only world is a nice dream but the real world is all
        # yucky and full of legacy encoding issues that should not crash my
        # bot.
        irc.client.ServerConnection.buffer_class = \
            irc.buffer.LenientDecodingLineBuffer

        super(Stashbot, self).__init__(
            [(self.config['irc']['server'], self.config['irc']['port'])],
            self.config['irc']['nick'],
            self.config['irc']['realname']
        )

    def get_version(self):
        return 'Stashbot'

    def on_nicknameinuse(self, conn, event):
        nick = conn.get_nickname()
        self.logger.warning('Requested nick "%s" in use', nick)
        conn.nick(nick + '_')

    def on_welcome(self, conn, event):
        self.logger.debug('Connected to server')
        if 'password' in self.config['irc']:
            self.logger.debug('Authenticating with Nickserv')
            conn.privmsg('NickServ', 'identify %s %s' % (
                self.config['irc']['nick'], self.config['irc']['password']))

        for c in self.config['irc']['channels']:
            self.logger.debug('Joining %s', c)
            conn.join(c)

    def on_join(self, conn, event):
        self.logger.info('Joined channel %s', event.target)

    def on_pubmsg(self, conn, event):
        # Log all public channel messages we receive
        doc = self._event_to_doc(conn, event)
        self.do_logmsg(conn, event)

        # Look for special messages
        msg = event.arguments[0]
        if msg.startswith('!log '):
            self.do_banglog(conn, event, doc)
        elif msg.startswith('!bash '):
            self.do_bash(conn, event, doc)

    def on_privmsg(self, conn, event):
        msg = event.arguments[0]
        if msg.startswith('!bash '):
            doc = self._event_to_doc(conn, event)
            self.do_bash(conn, event, doc)

    def do_logmsg(self, conn, event, doc):
        """Log an IRC channel message to Elasticsearch."""
        fmt = self.config['elasticsearch']['index']
        self.es.index(
            index=time.strftime(fmt, time.gmtime()),
            doc_type='irc',
            body=doc,
            consistency='one'
        )

    def do_banglog(self, conn, event, doc):
        """Process a !log message"""
        # Trim '!log ' from the front of the message
        msg = doc['message'][5:]
        doc['type'] = 'sal'

        if doc['channel'] == '#wikimedia-labs':
            project, msg = msg.split(None, 1)
            doc['project'] = project
            doc['message'] = msg
        elif doc['channel'] == '#wikimedia-releng':
            doc['project'] = 'releng'
            doc['message'] = msg
        elif doc['channel'] == '#wikimedia-analytics':
            doc['project'] = 'analytics'
            doc['message'] = msg
        elif doc['channel'] == '#wikimedia-operations':
            doc['project'] = 'production'
            doc['message'] = msg
            if doc['nick'] == 'logmsgbot':
                nick, msg = msg.split(None, 1)
                doc['nick'] = nick
                doc['msg'] = msg
        else:
            self.logger.info(
                '!log message on unexpected channel %s', doc['channel'])
            return

        self.es.index(
            index='sal', doc_type='sal', body=doc, consistency='one')

    def do_bash(self, conn, event, doc):
        """Process a !bash message"""
        # Trim '!bash ' from the front of the message
        msg = doc['message'][6:]
        doc['type'] = 'bash'
        doc['message'] = msg.replace("\t", "\n").strip()

        ret = self.es.index(
            index='bash', doc_type='bash', body=doc, consistency='one')

        if ret['_shards']['successful'] > 0:
            conn.privmsg(
                event.target,
                '%s: Stored quip at %s' % (
                    event.source.nick,
                    self.config['bash']['view_url'] % ret['_id']
                )
            )

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
