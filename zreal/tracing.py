"""
OpenTelemetry Tracing Configuration for ZReal.

This module sets up distributed tracing across:
- Django web requests
- Celery tasks
- Database queries (PostgreSQL)
- External HTTP calls
- Zcash RPC interactions (via custom spans)
"""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

def init_tracing():
    """Initialize OpenTelemetry tracing for the entire application."""
    
    # Create a tracer provider
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    
    # Configure OTLP exporter (can point to Jaeger, Tempo, or managed service)
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        insecure=True,
    )
    
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)
    
    # Auto-instrument frameworks
    DjangoInstrumentor().instrument()
    CeleryInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    RequestsInstrumentor().instrument()
    
    # Get a tracer for custom spans
    tracer = trace.get_tracer(__name__)
    
    return tracer


# Custom tracer for ZReal-specific operations
tracer = trace.get_tracer("zreal.tracer")
