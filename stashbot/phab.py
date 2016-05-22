#!/usr/bin/env python
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

import json
import requests


class Client(object):
    """Phabricator client"""
    def __init__(self, url, username, key):
        self.url = url
        self.username = username
        self.session = {
            'token': key,
        }

    def post(self, path, data):
        data['__conduit__'] = self.session
        r = requests.post('%s/api/%s' % (self.url, path), data={
            'params': json.dumps(data),
            'output': 'json',
        })
        resp = r.json()
        if resp['error_code'] is not None:
            raise Exception(resp['error_info'])
        return resp['result']

    def taskInfo(self, task):
        r = self.post('phid.lookup', {'names': [task]})
        if task in r:
            return r[task]
        raise Exception('Task %s not found' % task)

    def comment(self, task, comment):
        """Add a comment to a task.
        :param task: Task number (e.g. T12345)
        :param comment: Comment to add to task
        """
        phid = self.taskInfo(task)['phid']
        self.post('maniphest.update', {
            'phid': phid,
            'comments': comment,
        })
