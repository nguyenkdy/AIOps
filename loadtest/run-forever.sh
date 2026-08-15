#!/bin/bash
while true; do
  k6 run --quiet ~/aiops-k8s/loadtest/k6-normal.js
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] chu ky hoan tat, bat dau lai"
done
