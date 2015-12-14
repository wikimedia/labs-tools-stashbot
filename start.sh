#!/usr/bin/env bash
# Submit a job to the grid to start stashbot
jsub -once -continuous -mem 512m -l release=trusty -N stashbot run_bot.sh
