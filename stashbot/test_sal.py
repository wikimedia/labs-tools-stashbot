# -*- coding: utf-8 -*-
#
# This file is part of bd808's stashbot application
# Copyright (C) 2019 Bryan Davis and contributors
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

from . import sal


def test_safe_arg():
    tests = (
        ("a{b, c}d", "a<nowiki>{</nowiki>b, c<nowiki>}</nowiki>d"),
        ("a{{b, c}}d", "a{{b, c}}d"),
        ("a{{{b, c}}}d", "a{{{b, c}}}d"),
        ("a|b", "a{{!}}b"),
        (
            "k8s-{etcd,master,worker}",
            "k8s-<nowiki>{</nowiki>etcd,master,worker<nowiki>}</nowiki>",
        ),
    )
    for args in tests:
        yield run_safe_arg, args[0], args[1]


def run_safe_arg(source, expect):
    clean = sal.Logger.safe_arg(source)
    assert expect == clean, "{} != {}".format(expect, clean)
