from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


def setup_tracing():
    """
    Configure OpenTelemetry + OTLP exporter (Grafana Tempo).
    """

    # ✅ This gives your service a visible name in Grafana
    resource = Resource.create({
        "service.name": "partselect-backend"
    })

    provider = TracerProvider(resource=resource)

    processor = BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint="http://localhost:4317",
            insecure=True
        )
    )

    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)
