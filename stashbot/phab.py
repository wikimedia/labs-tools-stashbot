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

import hashlib
import json
import requests
import time

class Client(object):
    """Phabricator client"""
    def __init__(self, url, username, certificate):
        self.url = url
        self.username = username
        self.certificate = certificate
        self.session = None

    def getSessionKey(self):
        token = int(time.time())
        sig = hashlib.sha1(str(token) + self.certificate).hexdigest()
        data = {
            'client': 'stashbot',
            'clientVersion': 0,
            'user': self.username,
            'authToken': token,
            'authSignature': sig,
        }

        r = requests.post( '%s/api/conduit.connect' % self.url, data={
            'params': json.dumps(data),
            'output': 'json',
            '__conduit__': True,
        })
        resp = r.json()
        if resp['error_code'] is not None:
            print resp
            raise Exception(resp['error_info'])

        return {
            'sessionKey': resp['result']['sessionKey'],
            'connectionID': resp['result']['connectionID'],
        }

    def post(self, path, data):
        if self.session is None:
            self.session = self.getSessionKey()
        data['__conduit__'] = self.session
        r = requests.post( '%s/api/%s' % (self.url, path), data={
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
