#!/bin/bash
# Chi cho phep mot ban chay tai mot thoi diem.
exec 200>/tmp/k6-runner.lock
if ! flock -n 200; then
  echo "Da co mot ban run-forever.sh dang chay, thoat."
  exit 1
fi

# Don k6 con khi script thoat vi bat ky ly do gi
cleanup() {
  pkill -P $$ k6 2>/dev/null
  exit 0
}
trap cleanup EXIT TERM INT

while true; do
  k6 run --quiet ~/aiops-k8s/loadtest/k6-normal.js
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] chu ky hoan tat, bat dau lai"
done
