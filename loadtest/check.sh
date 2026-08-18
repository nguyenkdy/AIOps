#!/bin/bash
q() {
  curl -s --get http://localhost:9090/api/v1/query \
    --data-urlencode "query=$1" \
  | python3 -c "
import json, sys
for r in json.load(sys.stdin)['data']['result']:
    m = r['metric']
    label = m.get('service') or m.get('pod') or '?'
    print('  {:35s} {:.3f}'.format(label, float(r['value'][1])))
"
}

echo "== Request rate (req/s) =="
q 'sum(rate(http_requests_total{path="/api/data"}[2m])) by (service)'

echo "== p95 latency (s) =="
q 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{path="/api/data"}[2m])) by (le, service))'

echo "== CPU (core) =="
q 'sum(rate(container_cpu_usage_seconds_total{namespace="default",container!=""}[2m])) by (pod)'
