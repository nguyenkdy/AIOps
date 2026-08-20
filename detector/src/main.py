"""Detector service: query Prometheus, cham diem bat thuong, expose thanh metric."""
import json
import logging
import os
import time
from pathlib import Path

import joblib
import pandas as pd
import requests
from prometheus_client import Counter, Gauge, start_http_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("detector")

PROM_URL = os.environ.get("PROM_URL", "http://monitoring-kube-prometheus-prometheus.monitoring.svc:9090")
MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/app/models"))
INTERVAL = int(os.environ.get("INTERVAL_SECONDS", "30"))
WINDOW_MINUTES = 30

# Cac truy van phai khop chinh xac voi luc train
QUERIES = {
    "latency_p95__backend": 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service="backend",path="/api/data"}[2m])) by (le))',
    "cpu__backend": 'sum(rate(container_cpu_usage_seconds_total{namespace="default",container="backend"}[2m]))',
    "memory__backend": 'sum(container_memory_working_set_bytes{namespace="default",container="backend"})',
    "error_rate__frontend": '(sum(rate(http_requests_total{service="frontend",path="/api/data",status=~"5.."}[2m])) or sum(rate(http_requests_total{service="frontend",path="/api/data"}[2m])) * 0) / sum(rate(http_requests_total{service="frontend",path="/api/data"}[2m]))',
}

ANOMALY_SCORE = Gauge(
    "aiops_anomaly_score",
    "Diem bat thuong tu Isolation Forest (cao = bat thuong)",
    ["target"],
)
THRESHOLD_GAUGE = Gauge(
    "aiops_anomaly_threshold",
    "Nguong canh bao lay tu tap huan luyen",
)
INFERENCE_ERRORS = Counter(
    "aiops_inference_errors_total",
    "So lan chay suy luan that bai",
    ["reason"],
)
INFERENCE_DURATION = Gauge(
    "aiops_inference_duration_seconds",
    "Thoi gian mot lan suy luan",
)


def load_model():
    model = joblib.load(MODEL_DIR / "isolation_forest.joblib")
    meta = json.loads((MODEL_DIR / "metadata.json").read_text())
    log.info(
        "Da nap model: %d dac trung, nguong %.4f, train tren %d diem",
        len(meta["feature_names"]), meta["threshold"], meta["train_points"],
    )
    return model, meta


def query_range(query, minutes):
    end = time.time()
    start = end - minutes * 60
    resp = requests.get(
        PROM_URL + "/api/v1/query_range",
        params={"query": query, "start": start, "end": end, "step": "30s"},
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()["data"]["result"]
    if not result:
        return pd.Series(dtype=float)
    values = result[0]["values"]
    index = pd.to_datetime([float(t) for t, _ in values], unit="s", utc=True)
    return pd.Series([float(v) for _, v in values], index=index)


def build_window():
    """Lay du lieu gan nhat, tra ve DataFrame theo cac cot goc."""
    series = {}
    for name, query in QUERIES.items():
        s = query_range(query, WINDOW_MINUTES)
        if s.empty:
            raise ValueError("khong co du lieu cho " + name)
        series[name] = s
    df = pd.DataFrame(series)
    return df.interpolate(limit_direction="both")


def make_features(df, cols):
    """Phai giong het ham cung ten luc train."""
    parts = {}
    for col in cols:
        s = df[col]
        parts[col] = s
        parts[col + "_mean15"] = s.rolling(15, min_periods=1).mean()
        parts[col + "_std15"] = s.rolling(15, min_periods=1).std()
        parts[col + "_diff"] = s.diff()
    X = pd.DataFrame(parts, index=df.index)
    return X.bfill().fillna(0)


def score_once(model, meta):
    df = build_window()
    X = make_features(df, meta["feature_cols"])

    # Hop dong schema: thu tu cot phai khop luc train
    missing = set(meta["feature_names"]) - set(X.columns)
    if missing:
        raise ValueError("thieu dac trung: " + str(sorted(missing)))
    X = X[meta["feature_names"]]

    score = float(-model.score_samples(X.tail(1))[0])
    return score, df.index[-1]


def main():
    model, meta = load_model()
    THRESHOLD_GAUGE.set(meta["threshold"])

    start_http_server(8000)
    log.info("Expose metric tren cong 8000, chu ky %ds", INTERVAL)

    while True:
        began = time.time()
        try:
            score, ts = score_once(model, meta)
            ANOMALY_SCORE.labels(target="backend").set(score)
            state = "BAT THUONG" if score > meta["threshold"] else "binh thuong"
            log.info("diem=%.4f nguong=%.4f %s (moc %s)",
                     score, meta["threshold"], state, ts)
        except requests.RequestException as exc:
            INFERENCE_ERRORS.labels(reason="prometheus").inc()
            log.warning("khong query duoc Prometheus: %s", exc)
        except ValueError as exc:
            INFERENCE_ERRORS.labels(reason="data").inc()
            log.warning("du lieu khong hop le: %s", exc)
        except Exception as exc:
            INFERENCE_ERRORS.labels(reason="unknown").inc()
            log.exception("loi khong xac dinh: %s", exc)
        finally:
            INFERENCE_DURATION.set(time.time() - began)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
