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

import yaml


def yaml_unicode_str(self, node):
    """Create unicode objects for YAML string nodes."""
    # From http://stackoverflow.com/a/2967461/8171
    return self.construct_scalar(node)


# Attach custom unicode factory to string events
yaml.Loader.add_constructor("tag:yaml.org,2002:str", yaml_unicode_str)
yaml.SafeLoader.add_constructor("tag:yaml.org,2002:str", yaml_unicode_str)


def load(filename):
    return yaml.load(open(filename, "r"))
