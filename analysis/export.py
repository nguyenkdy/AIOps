"""Export metric tu Prometheus ra CSV de phan tich offline."""
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

PROM = "http://localhost:9090"
STEP = "30s"
CHUNK_SECONDS = 6 * 3600

# Gom theo nhan 'container' thay vi 'pod'.
# Ten pod doi moi lan rollout/podkill, ten container thi khong -> chuoi lien tuc.
QUERIES = {
    "latency_p95": 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{path="/api/data"}[2m])) by (le, service))',
    "request_rate": 'sum(rate(http_requests_total{path="/api/data"}[2m])) by (service)',
    "error_rate": '(sum(rate(http_requests_total{path="/api/data",status=~"5.."}[2m])) by (service) or sum(rate(http_requests_total{path="/api/data"}[2m])) by (service) * 0) / sum(rate(http_requests_total{path="/api/data"}[2m])) by (service)',
    "cpu": 'sum(rate(container_cpu_usage_seconds_total{namespace="default",container!=""}[2m])) by (container)',
    "memory": 'sum(container_memory_working_set_bytes{namespace="default",container!=""}) by (container)',
    "restarts": 'sum(increase(kube_pod_container_status_restarts_total{namespace="default"}[5m])) by (container)',
}


def fetch(query, start, end):
    resp = requests.get(
        PROM + "/api/v1/query_range",
        params={"query": query, "start": start, "end": end, "step": STEP},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["data"]["result"]


def to_frame(name, series_list):
    frames = []
    for series in series_list:
        metric = series["metric"]
        label = metric.get("service") or metric.get("container") or "unknown"
        rows = []
        for ts, value in series["values"]:
            rows.append({
                "time": pd.to_datetime(float(ts), unit="s", utc=True),
                name + "__" + label: float(value),
            })
        if rows:
            frames.append(pd.DataFrame(rows).set_index("time"))
    if not frames:
        return None
    return pd.concat(frames, axis=1)


def main(start_iso, end_iso):
    start = datetime.fromisoformat(start_iso).replace(tzinfo=timezone.utc).timestamp()
    end = datetime.fromisoformat(end_iso).replace(tzinfo=timezone.utc).timestamp()

    all_frames = []
    for name, query in QUERIES.items():
        chunks = []
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + CHUNK_SECONDS, end)
            result = fetch(query, cursor, chunk_end)
            frame = to_frame(name, result)
            if frame is not None:
                chunks.append(frame)
            cursor = chunk_end

        if chunks:
            merged = pd.concat(chunks)
            merged = merged[~merged.index.duplicated(keep="first")]
            all_frames.append(merged)
            print(name + ":", len(merged), "diem, cot", list(merged.columns))
        else:
            print(name + ": KHONG CO DU LIEU")

    df = pd.concat(all_frames, axis=1).sort_index()
    out = "data/metrics.csv"
    df.to_csv(out)
    print("\nDa ghi " + out + ":", len(df), "hang,", len(df.columns), "cot")
    print("Tu", df.index.min(), "den", df.index.max())


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Cach dung: python analysis/export.py 2026-08-15T00:00:00 2026-08-19T00:00:00")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
