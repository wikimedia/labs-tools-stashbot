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
        self.session = {"token": key}

    def post(self, path, data):
        data["__conduit__"] = self.session
        r = requests.post(
            "%s/api/%s" % (self.url, path),
            data={"params": json.dumps(data), "output": "json"},
        )
        resp = r.json()
        if resp["error_code"] is not None:
            raise Exception(resp["error_info"])
        return resp["result"]

    def lookupPhid(self, label):
        """Lookup information on a Phab object by name."""
        r = self.post("phid.lookup", {"names": [label]})
        if label in r:
            obj = r[label]
            if obj["type"] == "TASK":
                # T180081: Ensure that we don't leak information about
                # security tasks even if the bot somehow has access to the
                # task.
                info = self.taskDetails(obj["phid"])
                aux = info.get("auxiliary", {})
                st = aux.get("std:maniphest:security_topic")
                if st and st != "default":
                    raise Exception("Task %s is a security bug." % label)
            return obj
        raise Exception("No object found for %s" % label)

    def taskDetails(self, phid):
        """Lookup details of a Maniphest task."""
        r = self.post("maniphest.query", {"phids": [phid]})
        if phid in r:
            return r[phid]
        raise Exception("No task found for phid %s" % phid)

    def comment(self, task, comment):
        """Add a comment to a task.
        :param task: Task number (e.g. T12345)
        :param comment: Comment to add to task
        """
        phid = self.lookupPhid(task)["phid"]
        self.post("maniphest.update", {"phid": phid, "comments": comment})
