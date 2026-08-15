#!/bin/bash
# Gay loi co kiem soat va tu ghi nhan vao docs/fault-log.csv
# Cach dung:
#   ./inject-fault.sh latency backend 800 300
#   ./inject-fault.sh cpu backend 1 300
#   ./inject-fault.sh memory backend 250 120
#   ./inject-fault.sh podkill backend - -
#   ./inject-fault.sh drain agent-0 - 180

set -e

TYPE=$1
TARGET=$2
PARAM=$3
DURATION=$4

LOG=~/aiops-k8s/docs/fault-log.csv

if [ ! -f "$LOG" ]; then
  echo "start_utc,end_utc,type,target,param,duration_s" > "$LOG"
fi

START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$START] bat dau: $TYPE tren $TARGET (param=$PARAM, duration=$DURATION)"

case $TYPE in
  latency)
    POD=$(kubectl get pod -l app=$TARGET -o jsonpath='{.items[0].metadata.name}')
    kubectl exec $POD -- curl -sX POST localhost:8000/chaos/latency/$PARAM > /dev/null
    sleep $DURATION
    kubectl exec $POD -- curl -sX POST localhost:8000/chaos/latency/0 > /dev/null
    ;;

  cpu)
    POD=$(kubectl get pod -l app=$TARGET -o jsonpath='{.items[0].metadata.name}')
    kubectl exec $POD -- stress-ng --cpu $PARAM --timeout ${DURATION}s || true
    ;;

  memory)
    POD=$(kubectl get pod -l app=$TARGET -o jsonpath='{.items[0].metadata.name}')
    kubectl exec $POD -- stress-ng --vm 1 --vm-bytes ${PARAM}M --timeout ${DURATION}s || true
    ;;

  podkill)
    POD=$(kubectl get pod -l app=$TARGET -o jsonpath='{.items[0].metadata.name}')
    kubectl delete pod $POD --wait=false
    sleep 60
    DURATION=60
    ;;

  drain)
    kubectl drain k3d-aiops-$TARGET --ignore-daemonsets --delete-emptydir-data --force
    sleep $DURATION
    kubectl uncordon k3d-aiops-$TARGET
    ;;

  *)
    echo "Loai loi khong hop le: $TYPE"
    exit 1
    ;;
esac

END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "$START,$END,$TYPE,$TARGET,$PARAM,$DURATION" >> "$LOG"
echo "[$END] ket thuc, da ghi nhan"
