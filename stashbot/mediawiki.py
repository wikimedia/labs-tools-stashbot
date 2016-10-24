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

import mwclient
import urlparse


class Client(object):
    """MediaWiki api client."""

    def __init__(
        self, url,
        consumer_token=None, consumer_secret=None,
        access_token=None, access_secret=None
    ):
        self.url = url
        self.site = self._site_for_url(
            url, consumer_token, consumer_secret, access_token, access_secret)

    @classmethod
    def _site_for_url(
        cls, url,
        consumer_token=None, consumer_secret=None,
        access_token=None, access_secret=None
    ):
        parts = urlparse.urlparse(url)
        host = parts.netloc
        if parts.scheme != 'https':
            host = (parts.scheme, parts.netloc)
        force_login = consumer_token is not None
        return mwclient.Site(
            host,
            consumer_token=consumer_token,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_secret=access_secret,
            clients_useragent='https://tools.wmflabs.org/stashbot/',
            force_login=force_login
        )

    def get_page(self, title, follow_redirects=True):
        """Get a Page object."""
        page = self.site.Pages[title]
        while follow_redirects and page.redirect:
            page = next(page.links())
        return page

    def get_url_for_revision(self, revision):
        result = self.site.api(
            'query', formatversion=2,
            prop='info',
            inprop='url', revids=revision)
        return result['query']['pages'][0]['canonicalurl']
