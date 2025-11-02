"""OpenTelemetry distributed tracing v5.0"""

import os
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

logger = logging.getLogger(__name__)

# Initialize tracer
tracer = trace.get_tracer(__name__)


def setup_tracing():
    """Setup OpenTelemetry tracing if endpoint is configured"""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    
    if not endpoint:
        logger.info("OpenTelemetry endpoint not configured, skipping tracing setup")
        return
    
    try:
        # Create tracer provider
        provider = TracerProvider()
        
        # Create OTLP exporter
        exporter = OTLPSpanExporter(endpoint=endpoint)
        
        # Add span processor
        provider.add_span_processor(BatchSpanProcessor(exporter))
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        logger.info(f"OpenTelemetry tracing configured with endpoint: {endpoint}")
        
        # Try to instrument OpenAI (optional)
        try:
            from opentelemetry.instrumentation.openai import OpenAIInstrumentor
            OpenAIInstrumentor().instrument()
            logger.info("OpenAI instrumentation enabled")
        except ImportError:
            logger.debug("OpenAI instrumentation not available")
        
    except Exception as e:
        logger.error(f"Failed to setup OpenTelemetry tracing: {e}")


def get_tracer():
    """Get the global tracer"""
    return tracer
