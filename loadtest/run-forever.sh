#!/bin/bash
# Chi cho phep mot ban chay tai mot thoi diem.
# flock giu file khoa; neu da co tien trinh khac giu thi thoat ngay.
exec 200>/tmp/k6-runner.lock
if ! flock -n 200; then
  echo "Da co mot ban run-forever.sh dang chay, thoat."
  exit 1
fi

# Khi script bi kill, giet luon k6 con
trap 'pkill -P $$ k6; exit 0' TERM INT

while true; do
  k6 run --quiet ~/aiops-k8s/loadtest/k6-normal.js
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] chu ky hoan tat, bat dau lai"
done
