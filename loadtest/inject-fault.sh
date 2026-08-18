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
mkdir -p ~/aiops-k8s/docs

if [ ! -f "$LOG" ]; then
  echo "start_utc,end_utc,type,target,param,duration_s,note" > "$LOG"
fi

# Goi endpoint chaos tu ngoai qua port-forward tam thoi
set_latency() {
  local ms=$1
  kubectl port-forward deploy/$TARGET 18000:8000 > /dev/null 2>&1 &
  local pf_pid=$!
  sleep 3
  curl -sX POST localhost:18000/chaos/latency/$ms > /dev/null
  kill $pf_pid 2>/dev/null
  wait $pf_pid 2>/dev/null || true
}

START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$START] bat dau: $TYPE tren $TARGET (param=$PARAM, duration=$DURATION)"

case $TYPE in
  latency)
    set_latency $PARAM
    sleep $DURATION
    set_latency 0
    ;;

  cpu)
    POD=$(kubectl get pod -l app=$TARGET -o jsonpath='{.items[0].metadata.name}')
    kubectl exec $POD -- stress-ng --cpu $PARAM --timeout ${DURATION}s || true
    ;;

  memory)
    POD=$(kubectl get pod -l app=$TARGET -o jsonpath='{.items[0].metadata.name}')
    kubectl exec $POD -- stress-ng --vm 1 --vm-bytes ${PARAM}M --timeout ${DURATION}s || true
    ;;

  outage)
    kubectl scale deploy/$TARGET --replicas=0
    sleep $DURATION
    kubectl scale deploy/$TARGET --replicas=1
    kubectl rollout status deploy/$TARGET
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
echo "$START,$END,$TYPE,$TARGET,$PARAM,$DURATION," >> "$LOG"
echo "[$END] ket thuc, da ghi nhan"
