# -*- coding: utf-8 -*-
#
# This file is part of bd808's stashbot application
# Copyright (C) 2022 Bryan Davis and contributors
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

from . import bot


def test_RE_PHAB_NOURL():
    tests = (
        ("T1", False),
        ("T12", False),
        ("T123", True),
        ("T1234", True),
        ("https://phabricator.wikimedia.org/T325381", False),
        ("/T325381", False),
        ("[[phab:T325381]]", True),
        ("2022-12-16T19:00", False),
    )
    for args in tests:
        yield run_RE_PHAB_NOURL, args[0], args[1]


def run_RE_PHAB_NOURL(text, expect):
    match = bot.RE_PHAB_NOURL.search(text) is not None
    assert expect == match, "{} != {}".format(expect, match)
