#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

import argparse
import logging
import logging.handlers
import os.path

import stashbot
import stashbot.config

parser = argparse.ArgumentParser(description="Stashbot")
parser.add_argument(
    "-c", "--config", default="etc/config.yaml", help="Configuration file"
)
parser.add_argument(
    "-v",
    "--verbose",
    action="count",
    default=0,
    dest="loglevel",
    help="Increase logging verbosity",
)
args = parser.parse_args()

logging.basicConfig(
    level=max(logging.DEBUG, logging.WARNING - (10 * args.loglevel)),
    format="%(asctime)s %(name)-12s %(levelname)-8s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logging.captureWarnings(True)

# Write a log file of severe errors
# FIXME: make this configurable
fh = logging.handlers.FileHandler(
    os.path.expanduser("~/stashbot.log"), delay=True
)
fh.setLevel(logging.ERROR)
logging.getLogger().addHandler(fh)

log = logging.getLogger("Stashbot")
bot = stashbot.Stashbot(stashbot.config.load(args.config), log)
try:
    bot.start()
except KeyboardInterrupt:
    bot.disconnect()
except Exception:
    log.exception("Killed by unhandled exception")
    bot.disconnect()
    raise SystemExit()
