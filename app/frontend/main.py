import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import Counter, Histogram
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

SERVICE_NAME = "frontend"
BACKEND_URL = "http://backend:8000/api/data"

# Mot client dung chung cho ca vong doi app.
# Client giu san connection pool nen khong phai bat tay TCP moi request.
http_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=10.0)
    yield
    await http_client.aclose()


app = FastAPI(lifespan=lifespan)

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


@app.middleware("http")
async def track_metrics(request: Request, call_next):
    path = request.url.path

    if path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    status_code = "500"

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    except Exception:
        # Exception khong di qua duong tra ve binh thuong,
        # nhung van phai duoc dem la mot request that bai.
        raise
    finally:
        duration = time.perf_counter() - start

        REQUEST_COUNT.labels(
            service=SERVICE_NAME,
            method=request.method,
            path=path,
            status=status_code,
        ).inc()

        REQUEST_DURATION.labels(
            service=SERVICE_NAME,
            method=request.method,
            path=path,
        ).observe(duration)


@app.get("/api/data")
async def get_data():
    backend_response = await http_client.get(BACKEND_URL)
    return {"frontend": "ok", "backend": backend_response.json()}


@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
