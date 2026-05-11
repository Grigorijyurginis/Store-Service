from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracing() -> None:
    # Resource reads OTEL_SERVICE_NAME and OTEL_RESOURCE_ATTRIBUTES from env
    resource = Resource.create()
    provider = TracerProvider(resource=resource)
    # OTLPSpanExporter reads OTEL_EXPORTER_OTLP_ENDPOINT from env
    exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


# ProxyTracer — delegates to the real provider once setup_tracing() is called
tracer = trace.get_tracer("store")