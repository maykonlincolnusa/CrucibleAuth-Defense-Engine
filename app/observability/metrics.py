from time import perf_counter

from fastapi import Request, Response
try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
except Exception:  # pragma: no cover - optional dependency
    CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"

    class _NoOpMetric:
        def labels(self, **_):
            return self

        def inc(self, *_):
            return None

        def observe(self, *_):
            return None

        def set(self, *_):
            return None

    def Counter(*_, **__):  # type: ignore
        return _NoOpMetric()

    def Histogram(*_, **__):  # type: ignore
        return _NoOpMetric()

    def Gauge(*_, **__):  # type: ignore
        return _NoOpMetric()

    def generate_latest():  # type: ignore
        return b"# metrics disabled\n"
from starlette.middleware.base import BaseHTTPMiddleware

HTTP_REQUESTS_TOTAL = Counter(
    "security_http_requests_total",
    "Total HTTP requests.",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "security_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)

LOGIN_EVENTS_TOTAL = Counter(
    "security_login_events_total",
    "Login events by outcome.",
    ["result"],
)
NETWORK_ANOMALIES_TOTAL = Counter(
    "security_network_anomalies_total",
    "Detected network anomalies.",
)
PIPELINE_MODEL_READY = Gauge(
    "security_pipeline_model_ready",
    "Model readiness status in pipeline (1 ready, 0 not ready).",
    ["model"],
)
DQN_EPSILON = Gauge(
    "security_dqn_epsilon",
    "Current epsilon value of DQN response agent.",
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = perf_counter()
        response = await call_next(request)
        duration = perf_counter() - start

        path = request.url.path
        if path == "/metrics":
            return response

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            path=path,
            status=str(response.status_code),
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            path=path,
        ).observe(duration)
        return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
