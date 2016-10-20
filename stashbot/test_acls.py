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

from . import acls
import irc.client


def test_check():
    common_rules = {
        'allow': ['*!*@test/allowed'],
        'deny': ['*!*@test/denied'],
    }
    tests = [
        [
            {},
            'nick!user@host',
            True
        ],
        [
            common_rules,
            'nick!user@host',
            True
        ],
        [
            common_rules,
            'nick!user@test/allowed',
            True
        ],
        [
            dict(common_rules, default=False),
            'nick!~user@test/allowed',
            True
        ],
        [
            {'default': False},
            'nick!user@host',
            False
        ],
        [
            common_rules,
            'nick!user@test/denied',
            False
        ],
        [
            dict(common_rules, allow=[], default=False),
            'nick!user@test/allowed',
            False
        ],
    ]
    for args in tests:
        yield run_check, args[0], args[1], args[2]


def run_check(config, source, expect):
    source = irc.client.NickMask(source)
    assert expect == acls.check(config, source)


def test_check_mask():
    source = irc.client.NickMask('nick!user@host')
    tests = [
        ['nick!user@host', True],
        ['*!user@host', True],
        ['*!*user@host', True],
        ['*!*@*host', True],
        ['*!*@*', True],
        ['*!*user@*', True],
        ['*!user@host2', False],
    ]
    for args in tests:
        yield run_check_mask, args[0], source, args[1]


def run_check_mask(mask, source, expect):
    assert expect == acls.check_mask(mask, source)
