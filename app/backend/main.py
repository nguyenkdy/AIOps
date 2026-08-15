import asyncio
import random
import time

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import Counter, Histogram
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()

SERVICE_NAME = "backend"

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Tong so HTTP request da xu ly",
    ["service", "method", "path", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Thoi gian xu ly mot request",
    ["service", "method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.2, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# bien dieu khien chaos, doi duoc luc runtime
extra_latency_seconds = 0.0


@app.middleware("http")
async def track_metrics(request: Request, call_next):
    path = request.url.path

    if path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    REQUEST_COUNT.labels(
        service=SERVICE_NAME,
        method=request.method,
        path=path,
        status=str(response.status_code),
    ).inc()

    REQUEST_DURATION.labels(
        service=SERVICE_NAME,
        method=request.method,
        path=path,
    ).observe(duration)

    return response


@app.get("/api/data")
async def get_data():
    base_delay = random.uniform(0.05, 0.15)
    await asyncio.sleep(base_delay + extra_latency_seconds)
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/chaos/latency/{ms}")
async def set_latency(ms: int):
    global extra_latency_seconds
    extra_latency_seconds = ms / 1000
    return {"extra_latency_ms": ms}


@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
