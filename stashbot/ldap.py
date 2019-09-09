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

import ldap3
import ldap3.core.exceptions


class Client(object):
    """LDAP client"""

    def __init__(self, uri, logger):
        self._uri = uri
        self.logger = logger
        self.conn = None

    def _connect(self):
        return ldap3.Connection(
            self._uri,
            auto_bind=ldap3.AUTO_BIND_NO_TLS,
            auto_range=True,
            read_only=True,
            raise_exceptions=True,
        )

    def search(self, *args, **kwargs):
        """A fairly thin wrapper around ldap3.Connection.search.

        Rather then just returning a boolean status as
        ldap3.Connection.search does, this method returns the fetched results
        if the search succeeded.

        We also try to handle some LDAP errors related to the connection
        itself by discarding the current connection and possibly retrying the
        request. Only one retry will be done. Consecutive
        ldap3.core.exceptions.LDAPCommunicationError exceptions will result in
        a raised exception to the caller. If you do not want the default
        single retry, pass `retriable=False` as a named argument to the
        initial call.
        """
        if "retriable" in kwargs:
            retriable = kwargs["retriable"]
            del kwargs["retriable"]
        else:
            retriable = True

        if "time_limit" not in kwargs:
            # Do not allow any search to take over 60 seconds
            kwargs["time_limit"] = 60

        # Get a list of results rather than a generator so that all the LDAP
        # error handling happens right here.
        kwargs["generator"] = False

        try:
            if self.conn is None:
                self.conn = self._connect()
            return self.conn.extend.standard.paged_search(*args, **kwargs)
        except ldap3.core.exceptions.LDAPCommunicationError:
            self.conn = None
            if retriable:
                self.logger.exception(
                    "LDAP server connection barfed; retrying"
                )
                return self.search(*args, retriable=False, **kwargs)
            else:
                raise
        except Exception:
            # If anything at all goes wrong, ditch the connection out of
            # paranoia. We really don't want to have to restart the bot for
            # dumb things like LDAP hiccups.
            self.conn = None
            raise
