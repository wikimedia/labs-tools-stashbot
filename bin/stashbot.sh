#!/usr/bin/env bash
# Management script for stashbot kubernetes processes

set -e

DEPLOYMENT=stashbot.libera
POD_NAME=stashbot.libera

CONFIG=etc/config-libera.yaml

TOOL_DIR=$(cd $(dirname $0)/.. && pwd -P)
VENV=${TOOL_DIR}/venv-k8s-py39
if [[ -f ${VENV}/bin/activate ]]; then
    # Enable virtualenv
    source ${VENV}/bin/activate
fi

KUBECTL=/usr/bin/kubectl

_get_pod() {
    $KUBECTL get pods \
        --output=jsonpath={.items..metadata.name} \
        --selector=name=${POD_NAME}
}

case "$1" in
    start)
        echo "Starting stashbot k8s deployment..."
        $KUBECTL create --validate=true -f ${TOOL_DIR}/etc/deployment-libera.yaml
        ;;
    run)
        date +%Y-%m-%dT%H:%M:%S
        echo "Running stashbot..."
        cd ${TOOL_DIR}
        exec python3 -m stashbot --config ${CONFIG}
        ;;
    stop)
        echo "Stopping stashbot k8s deployment..."
        $KUBECTL delete deployment ${DEPLOYMENT}
        # FIXME: wait for the pods to stop
        ;;
    restart)
        echo "Restarting stashbot pod..."
        exec $KUBECTL delete pod $(_get_pod)
        ;;
    status)
        echo "Active pods:"
        exec $KUBECTL get pods -l name=${POD_NAME}
        ;;
    tail)
        exec $KUBECTL logs -f $(_get_pod)
        ;;
    update)
        echo "Updating git clone..."
        cd ${TOOL_DIR}
        git fetch &&
        git --no-pager log --stat HEAD..@{upstream} &&
        git rebase @{upstream}
        ;;
    attach)
        echo "Attaching to pod..."
        exec $KUBECTL exec -i -t $(_get_pod) -- /bin/bash
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|tail|update|attach}"
        exit 1
        ;;
esac

exit 0
# vim:ft=sh:sw=4:ts=4:sts=4:et:
