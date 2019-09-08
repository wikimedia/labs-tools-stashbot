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

import datetime
import re
import time
import twitter

from . import acls
from . import ldap
from . import mediawiki

RE_PHAB = re.compile(r"\b(T\d+)\b")


class Logger(object):
    """Handle server admin logs"""

    def __init__(self, irc, phab, es, config, logger):
        self.irc = irc
        self.phab = phab
        self.es = es
        self.config = config
        self.logger = logger

        self.ldap = ldap.Client(self.config["ldap"]["uri"], self.logger)
        self._cached_wikis = {}
        self._cached_twitter = {}
        self._cached_projects = None

    def log(self, conn, event, doc, respond_to_channel=True):
        """Process a !log message"""
        bang = dict(doc)
        channel = bang["channel"]

        channel_conf = self._get_sal_config(channel)

        if "use_config" in channel_conf:
            channel = channel_conf["use_config"]
            channel_conf = self._get_sal_config(channel)

        if "project" not in channel_conf:
            self.logger.warning(
                "!log message on unexpected channel %s", channel
            )
            if respond_to_channel:
                self.irc.respond(
                    conn,
                    event,
                    "%s: Not expecting to hear !log here" % bang["nick"],
                )
            return

        if not self._check_sal_acl(channel, event.source):
            self.logger.warning(
                "Ignoring !log from %s in %s", event.source, channel
            )
            if respond_to_channel:
                self.irc.respond(
                    conn,
                    event,
                    "%s: !log ACLs in this channel blocked your message"
                    % (bang["nick"]),
                )
            return

        # Trim '!log ' from the front of the message
        bang["message"] = bang["message"][5:].strip()
        bang["type"] = "sal"
        bang["project"] = channel_conf["project"]

        if bang["message"] == "":
            if respond_to_channel:
                self.irc.respond(
                    conn,
                    event,
                    "%s: Message missing. Nothing logged." % bang["nick"],
                )
            return

        if bang["nick"] == "logmsgbot":
            # logmsgbot is expected to tell us who is running the command
            bang["nick"], bang["message"] = bang["message"].split(None, 1)

        if channel in ["#wikimedia-labs", "#wikimedia-cloud"]:
            parts = bang["message"].split(None, 1)
            if len(parts) < 2:
                if respond_to_channel:
                    self.irc.respond(
                        conn,
                        event,
                        (
                            "%s: Missing project or message? "
                            "Expected !log <project> <message>"
                        )
                        % bang["nick"],
                    )
                return

            bang["project"], bang["message"] = parts
            if bang["project"] not in self._get_projects():
                self.logger.warning('Invalid project "%s"', bang["project"])
                if respond_to_channel:
                    self.irc.respond(
                        conn,
                        event,
                        '%s: Unknown project "%s"'
                        % (bang["nick"], bang["project"]),
                    )
                    tool = "tools.%s" % bang["project"]
                    if tool in self._get_projects():
                        self.irc.respond(
                            conn,
                            event,
                            '%s: Did you mean to say "%s" instead?'
                            % (bang["nick"], tool),
                        )
                return

            if bang["project"] in ["deployment-prep", "contintcloud"]:
                # We got a message that the releng folks would like to see in
                # their unified SAL too. Munge the message and call ourself
                # again, but don't say anything on irc about it.
                self._log_duplicate(
                    conn,
                    event,
                    bang,
                    channel="#wikimedia-releng",
                    message="!log %s" % bang["message"],
                )

            elif channel == "#wikimedia-operations":
                if "#releng" in bang["message"]:
                    self._log_duplicate(
                        conn, event, bang, channel="#wikimedia-releng"
                    )

        self._store_in_es(bang, do_phab=respond_to_channel)

        if "wiki" in channel_conf:
            try:
                url = self._write_to_wiki(bang, channel_conf)
                if respond_to_channel:
                    self.irc.respond(
                        conn, event, "Logged the message at %s" % url
                    )
            except Exception:
                self.logger.exception("Error writing to wiki")
                if respond_to_channel:
                    self.irc.respond(
                        conn,
                        event,
                        (
                            "%s: Failed to log message to wiki. "
                            "Somebody should check the error logs."
                        )
                        % bang["nick"],
                    )

        if "twitter" in channel_conf:
            try:
                self._tweet(bang, channel_conf)
            except Exception:
                self.logger.exception("Error writing to twitter")

    def _log_duplicate(self, conn, event, doc, **kwargs):
        if not kwargs:
            self.logger.warning(
                "Cowardly refusing to re-log an unmodified message"
            )
            return
        new_doc = dict(doc)
        new_doc.update(kwargs)
        self.log(conn, event, new_doc, respond_to_channel=False)

    def _get_sal_config(self, channel):
        """Get SAL configuration for given channel."""
        if "channels" not in self.config["sal"]:
            return {}
        if channel not in self.config["sal"]["channels"]:
            return {}
        return self.config["sal"]["channels"][channel]

    def _check_sal_acl(self, channel, source):
        """Check a message source against a channel's acl list"""
        conf = self._get_sal_config(channel)
        if "acl" not in conf:
            return True
        if channel not in conf["acl"]:
            return True
        return acls.check(conf["acl"], source)

    def _get_projects(self):
        """Get a list of valid Labs projects"""
        if self._cached_projects and self._cached_projects[0] < time.time():
            # Clear expired cache
            self._cached_projects = None
            self.logger.info("Cleared stale project cache")

        if self._cached_projects is None:
            projects = self._get_ldap_names("projects")
            servicegroups = self._get_ldap_names("servicegroups")
            if projects and servicegroups:
                self._cached_projects = (
                    time.time() + 300,
                    projects + servicegroups,
                )
                self.logger.info(
                    "Caching project list until %d", self._cached_projects[0]
                )
            else:
                # One or both lists empty probably means LDAP failures
                # Don't cache the result.
                self.logger.warning("Returning partial project list")
                return projects + servicegroups

        return self._cached_projects[1]

    def _get_ldap_names(self, ou):
        """Get a list of cn values from LDAP for a given ou."""
        dn = "ou=%s,%s" % (ou, self.config["ldap"]["base"])
        try:
            res = self.ldap.search(
                dn, "(objectclass=groupofnames)", attributes=["cn"]
            )
            if res:
                return [g["attributes"]["cn"][0] for g in res]
            else:
                self.logger.error("Failed to get LDAP data for %s", dn)
        except Exception:
            self.logger.exception("Exception getting LDAP data for %s", dn)
        return []

    def _store_in_es(self, bang, do_phab=True):
        """Save a !log message to elasticsearch."""
        ret = self.es.index(index="sal", doc_type="sal", body=bang)
        if (
            do_phab
            and "phab" in self.config["sal"]
            and "created" in ret
            and ret["created"] is True
        ):
            m = RE_PHAB.findall(bang["message"])
            msg = self.config["sal"]["phab"] % dict(
                {"href": self.config["sal"]["view_url"] % ret["_id"]}, **bang
            )
            for task in m:
                try:
                    self.phab.comment(task, msg)
                except Exception:
                    self.logger.exception("Failed to add note to phab task")

    def _write_to_wiki(self, bang, channel_conf):
        """Write a !log message to a wiki page."""
        now = datetime.datetime.utcnow()
        leader = channel_conf.get("leader", "==")
        target_section = now.strftime(
            "%(leader)s %(date_format)s %(leader)s"
            % {"leader": leader, "date_format": "%Y-%m-%d"}
        )
        logline = "* {{safesubst:SAL entry|1=%02d:%02d %s: %s}}" % (
            now.hour,
            now.minute,
            bang["nick"],
            bang["message"].replace("|", "{{!}}"),
        )
        summary = "%(nick)s: %(message)s" % bang

        site = self._get_mediawiki_client(channel_conf["wiki"])
        page = site.get_page(channel_conf["page"] % bang)

        text = page.text()
        lines = text.split("\n")
        first_header = 0

        for pos, line in enumerate(lines):
            if line.startswith("%s " % leader):
                first_header = pos
                break

        if lines[first_header] == target_section:
            lines.insert(first_header + 1, logline)
        else:
            lines.insert(first_header, "")
            lines.insert(first_header, logline)
            lines.insert(first_header, target_section)

        if "category" in channel_conf:
            cat = channel_conf["category"]
            if not re.search(r"\[\[Category:%s\]\]" % cat, text):
                lines.append("<noinclude>[[Category:%s]]</noinclude>" % cat)

        resp = page.save("\n".join(lines), summary=summary, bot=True)
        return site.get_url_for_revision(resp["newrevid"])

    def _tweet(self, bang, channel_conf):
        """Post a tweet."""
        update = ("%(nick)s: %(message)s" % bang)[:280]
        client = self._get_twitter_client(channel_conf["twitter"])
        client.PostUpdate(update)

    def _get_mediawiki_client(self, name):
        """Get a mediawiki client for the given name."""
        if name not in self._cached_wikis:
            conf = self.config["mediawiki"][name]
            self._cached_wikis[name] = mediawiki.Client(
                conf["url"],
                consumer_token=conf["consumer_token"],
                consumer_secret=conf["consumer_secret"],
                access_token=conf["access_token"],
                access_secret=conf["access_secret"],
            )
        return self._cached_wikis[name]

    def _get_twitter_client(self, name):
        """Get a twitter client."""
        if name not in self._cached_twitter:
            conf = self.config["twitter"][name]
            self._cached_twitter[name] = twitter.Api(
                consumer_key=conf["consumer_key"],
                consumer_secret=conf["consumer_secret"],
                access_token_key=conf["access_token_key"],
                access_token_secret=conf["access_token_secret"],
            )
        return self._cached_twitter[name]
