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
import irc.client

import pytest

from . import acls


COMMON_RULES = {"allow": ["*!*@test/allowed"], "deny": ["*!*@test/denied"]}


@pytest.mark.parametrize(
    "config,source,expect",
    [
        [{}, "nick!user@host", True],
        [COMMON_RULES, "nick!user@host", True],
        [COMMON_RULES, "nick!user@test/allowed", True],
        [dict(COMMON_RULES, default=False), "nick!~user@test/allowed", True],
        [{"default": False}, "nick!user@host", False],
        [COMMON_RULES, "nick!user@test/denied", False],
        [
            dict(COMMON_RULES, allow=[], default=False),
            "nick!user@test/allowed",
            False,
        ],
    ],
)
def test_check(config, source, expect):
    source = irc.client.NickMask(source)
    assert expect == acls.check(config, source)


@pytest.mark.parametrize(
    "mask,expect",
    [
        ["nick!user@host", True],
        ["*!user@host", True],
        ["*!*user@host", True],
        ["*!*@*host", True],
        ["*!*@*", True],
        ["*!*user@*", True],
        ["*!user@host2", False],
    ],
)
def test_check_mask(mask, expect):
    source = irc.client.NickMask("nick!user@host")
    assert expect == acls.check_mask(mask, source)
