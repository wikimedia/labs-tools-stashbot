# -*- coding: utf-8 -*-
#
# This file is part of bd808's stashbot application
# Copyright (C) 2016 Bryan Davis and contributors
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

import elasticsearch
import re
import time

RE_STYLE = re.compile(r"[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?")


class Client(object):
    """Elasticsearch client"""

    def __init__(self, servers, options, logger):
        self.es = elasticsearch.Elasticsearch(servers, **options)
        self.logger = logger

    def event_to_doc(self, conn, event):
        """Make an Elasticsearch document from an IRC event."""
        return {
            "message": RE_STYLE.sub("", event.arguments[0]),
            "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "type": "irc",
            "user": event.source,
            "channel": event.target,
            "nick": event.source.nick,
            "server": conn.get_server_name(),
            "host": event.source.host,
        }

    def index(self, index, body):
        """Store a document in Elasticsearch."""
        try:
            return self.es.index(index=index, body=body)
        except elasticsearch.ConnectionError as e:
            self.logger.exception(
                "Failed to log to elasticsearch: %s", e.error
            )
            return {}
