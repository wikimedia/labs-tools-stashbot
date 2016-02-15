#!/usr/bin/env bash
# Management script for atashbot SGE job

set -e

MEM=512m
REL=trusty
JOB=stashbot

TOOL_DIR=$(cd $(dirname $0) && pwd -P)
if [[ -f ${TOOL_DIR}/virtenv/bin/activate ]]; then
    # Enable virtualenv
    source ./virtenv/bin/activate
fi

_get_job_id() {
    # The job command is a bit goofy. It uses non-0 exit codes to indicate
    # that the requested job is running or queued. I'm sure that made sense to
    # somebody as some point.
    /usr/bin/job $JOB || true
}

case "$1" in
    start)
        echo "Starting stashbot..."
        jsub -once -continuous -stderr -mem $MEM -l release=$REL -N $JOB \
            ${TOOL_DIR}/stashbot.sh run
        ;;
    run)
        date +%Y-%m-%dT%H:%M:%S
        echo "Running stashbot..."
        cd ${TOOL_DIR}
        exec python ./stashbot.py
        ;;
    stop)
        echo "Stopping stashbot..."
        JID=$(_get_job_id)
        if [[ -n $JID ]]; then
            qdel $JID
            sleep 1
        fi
        while true; do
            JID=$(_get_job_id)
            if [[ -n $JID ]]; then
                sleep 1
            else
                break
            fi
        done
        ;;
    restart)
        echo "Restarting stashbot..."
        JID=$(_get_job_id)
        if [[ -n $JID ]]; then
            qmod -rj $JOB
        else
            $0 start
        fi
        ;;
    status)
        JID=$(_get_job_id)
        if [[ -n $JID ]]; then
            qstat -j $JID
        else
            echo "Job $JOB is stopped"
            exit 1
        fi
        ;;
    tail)
        exec tail -F ${TOOL_DIR}/${JOB}.???
        ;;
    logrotate)
        exec logrotate --verbose --force \
            --state ${TOOL_DIR}/archive/logrotate.state \
            ${TOOL_DIR}/logrotate.conf
        ;;
    update)
        echo "Updating git clone..."
        cd ${TOOL_DIR}
        git fetch &&
        git --no-pager log --stat HEAD..@{upstream} &&
        git rebase @{upstream}
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|tail|logrotate|update}"
        exit 1
        ;;
esac

exit 0
# vim:ft=sh:sw=4:ts=4:sts=4:et:
