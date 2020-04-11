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

import collections
import ib3
import ib3.auth
import ib3.connection
import ib3.mixins
import ib3.nick
import re
import time

from . import es
from . import phab
from . import sal

RE_PHAB_NOURL = re.compile(r"(?:^|[^/%])\b([DMT]\d+)\b")


class Stashbot(
    ib3.auth.SASL,
    ib3.connection.SSL,
    ib3.mixins.DisconnectOnError,
    ib3.mixins.PingServer,
    ib3.mixins.RejoinOnBan,
    ib3.mixins.RejoinOnKick,
    ib3.nick.Regain,
    ib3.Bot,
):
    def __init__(self, config, logger):
        """Create bot.

        :param config: Dict of configuration values
        :param logger: Logger
        """
        self.config = config
        self.logger = logger

        self.es = es.Client(
            self.config["elasticsearch"]["servers"],
            self.config["elasticsearch"]["options"],
            self.logger,
        )

        self.phab = phab.Client(
            self.config["phab"]["url"],
            self.config["phab"]["user"],
            self.config["phab"]["key"],
        )

        self.sal = sal.Logger(
            self, self.phab, self.es, self.config, self.logger
        )

        self.recent_phab = collections.defaultdict(dict)

        super(Stashbot, self).__init__(
            server_list=[
                (self.config["irc"]["server"], self.config["irc"]["port"])
            ],
            nickname=self.config["irc"]["nick"],
            realname=self.config["irc"]["realname"],
            ident_password=self.config["irc"]["password"],
            channels=self.config["irc"]["channels"],
        )

        # Clean phab recent cache every once in a while
        self.reactor.scheduler.execute_every(
            period=3600, func=self.do_clean_recent_phab
        )

    def get_version(self):
        return "Stashbot"

    def on_join(self, conn, event):
        nick = event.source.nick
        if nick == conn.get_nickname():
            self.logger.info("Joined %s", event.target)

    def on_privnotice(self, conn, event):
        self.logger.warning(str(event))

    def on_pubnotice(self, conn, event):
        self.logger.warning(str(event))

    def on_pubmsg(self, conn, event):
        if not self.has_primary_nick():
            # Don't do anything if we haven't aquired the primary nick
            return

        # Log all public channel messages we receive
        doc = self.es.event_to_doc(conn, event)
        self.do_write_to_elasticsearch(conn, event, doc)

        # Look for special messages
        msg = event.arguments[0]

        if msg.startswith("!log help"):
            self.do_help(conn, event)

        elif msg.startswith(conn.get_nickname()):
            self.do_help(conn, event)

        elif msg.startswith(self.config["irc"]["nick"]):
            self.do_help(conn, event)

        elif msg.startswith("!log "):
            self.sal.log(conn, event, doc)

        elif msg.startswith("!bash "):
            self.do_bash(conn, event, doc)

        ignore = self.config["irc"].get("ignore", [])
        if self._clean_nick(doc["nick"]) in ignore:
            return

        if (
            event.target not in self.config["phab"].get("notin", [])
            and "echo" in self.config["phab"]
            and RE_PHAB_NOURL.search(msg)
        ):
            self.do_phabecho(conn, event, doc)

    def on_privmsg(self, conn, event):
        msg = event.arguments[0]
        if msg.startswith("!bash "):
            doc = self.es.event_to_doc(conn, event)
            self.do_bash(conn, event, doc)
        else:
            self.respond(conn, event, event.arguments[0][::-1])

    def do_write_to_elasticsearch(self, conn, event, doc):
        """Log an IRC channel message to Elasticsearch."""
        fmt = self.config["elasticsearch"]["index"]
        self.es.index(index=time.strftime(fmt, time.gmtime()), body=doc)

    def do_help(self, conn, event):
        """Handle a help message request"""
        self.respond(
            conn,
            event,
            "See https://wikitech.wikimedia.org/wiki/Tool:Stashbot for help.",
        )

    def do_bash(self, conn, event, doc):
        """Process a !bash message"""
        bash = dict(doc)
        # Trim '!bash ' from the front of the message
        msg = bash["message"][6:]
        # Expand tabs to line breaks
        bash["message"] = msg.replace("\t", "\n").strip()
        bash["type"] = "bash"
        bash["up_votes"] = 0
        bash["down_votes"] = 0
        bash["score"] = 0
        # Remove unneeded irc fields
        del bash["user"]
        del bash["channel"]
        del bash["server"]
        del bash["host"]

        ret = self.es.index(index="bash", body=bash)

        if "result" in ret and ret["result"] == "created":
            self.respond(
                conn,
                event,
                "%s: Stored quip at %s"
                % (
                    event.source.nick,
                    self.config["bash"]["view_url"] % ret["_id"],
                ),
            )
        else:
            self.logger.error("Failed to save document: %s", ret)
            self.respond(
                conn,
                event,
                "%s: Yuck. Something blew up when I tried to save that."
                % (event.source.nick,),
            )

    def do_phabecho(self, conn, event, doc):
        """Give links to Phabricator objects"""
        channel = event.target
        now = time.time()
        cutoff = self.get_phab_echo_cutoff(channel)
        for label in set(RE_PHAB_NOURL.findall(doc["message"])):
            if label in self.recent_phab[channel]:
                if self.recent_phab[channel][label] > cutoff:
                    # Don't spam a channel with links
                    self.logger.debug(
                        "Ignoring %s; last seen @%d",
                        label,
                        self.recent_phab[channel][label],
                    )
                    continue
            try:
                info = self.phab.lookupPhid(label)
            except Exception:
                self.logger.exception("Failed to lookup info for %s", label)
            else:
                self.respond(conn, event, self.config["phab"]["echo"] % info)
                self.recent_phab[channel][label] = now

    def get_phab_echo_cutoff(self, channel):
        """Get phab echo delay for the given channel."""
        return time.time() - self.config["phab"]["delay"].get(
            channel, self.config["phab"]["delay"]["__default__"]
        )

    def do_clean_recent_phab(self):
        """Clean old items out of the recent_phab cache."""
        for channel in list(self.recent_phab.keys()):
            cutoff = self.get_phab_echo_cutoff(channel)
            for item in list(self.recent_phab[channel].keys()):
                if self.recent_phab[channel][item] < cutoff:
                    del self.recent_phab[channel][item]

    def _clean_nick(self, nick):
        """Remove common status indicators and normlize to lower case."""
        return nick.split("|", 1)[0].rstrip("`_").lower()

    def respond(self, conn, event, msg):
        """Respond to an event with a message."""
        to = event.target
        if to == self.connection.get_nickname():
            to = event.source.nick
        conn.privmsg(to, msg.replace("\n", " "))
