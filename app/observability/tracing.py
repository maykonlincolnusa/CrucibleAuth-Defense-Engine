try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except Exception:  # pragma: no cover - optional dependency
    trace = None
    OTLPSpanExporter = None
    FastAPIInstrumentor = None
    SQLAlchemyInstrumentor = None
    SERVICE_NAME = None
    Resource = None
    TracerProvider = None
    BatchSpanProcessor = None

from app.core.config import get_settings


def setup_tracing(app, engine) -> None:
    settings = get_settings()
    if (
        not settings.otel_enabled
        or trace is None
        or FastAPIInstrumentor is None
        or SQLAlchemyInstrumentor is None
        or TracerProvider is None
        or Resource is None
    ):
        return

    resource = Resource(attributes={SERVICE_NAME: "security-defense-api"})
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
