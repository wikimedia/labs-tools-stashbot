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

import fnmatch
import irc.client


def check(config, source):
    """Check a message source against an acl collection.

    The dict of acls can contain these keys:
    - 'order': order to process directives ('allow,deny' or 'deny,allow')
    - 'default': 'allow' or 'deny'
    - 'allow': list of account masks to allow
    - 'deny': list of account masks to deny

    Account masks have three parts: nick!user@host
    Each part can use shell style "glob" pattern matching.

    :param config: dict of access control rules
    :param source: message source to check
    :return: bool
    """
    order = config.get('order', 'allow,deny').split(',')
    for check_type in order:
            action = check_list(
                config.get(check_type, []), source, check_type == 'allow')
            if action is not None:
                return action

    return config.get('default', 'allow') == 'allow'


def check_list(masks, source, match_action):
    """Check a message source against a list of masks.

    :param masks: list of masks
    :param source: message source to check
    :return: match_action or None
    """
    for mask in masks:
        if check_mask(mask, source):
            return match_action
        return None


def check_mask(mask, source):
    """Compare a mask to a source.

    :param mask: nick mask
    :param source: message source to check
    :return: bool
    """
    nick_mask = irc.client.NickMask(mask)
    return (
        fnmatch.fnmatch(source.nick, nick_mask.nick) and
        fnmatch.fnmatch(source.user, nick_mask.user) and
        fnmatch.fnmatch(source.host, nick_mask.host)
    )
