#!/usr/bin/env bash
# This is a job script for the Stashbot tool on whatever node it
# ends up running on. It is not designed to just 'be run'.

source ./virtenv/bin/activate
python ./stashbot.py
