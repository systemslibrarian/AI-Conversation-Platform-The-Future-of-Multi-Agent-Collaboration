# Minimal tests to increase coverage for core/tracing.py
import os
from unittest.mock import patch
from core import tracing


def test_setup_tracing_runs():
    # setup_tracing() takes no arguments
    tracing.setup_tracing()


def test_setup_tracing_with_endpoint():
    # Test with OTEL endpoint set
    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318"}):
        with patch("core.tracing.TracerProvider"):
            with patch("core.tracing.OTLPSpanExporter"):
                with patch("core.tracing.BatchSpanProcessor"):
                    tracing.setup_tracing()


def test_get_tracer_returns_tracer():
    tracer = tracing.get_tracer()
    assert tracer is not None


def test_setup_tracing_with_openai_instrumentation():
    # Test OpenAI instrumentation path (lines 43-44)
    from unittest.mock import MagicMock

    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318"}):
        with patch("core.tracing.TracerProvider"):
            with patch("core.tracing.OTLPSpanExporter"):
                with patch("core.tracing.BatchSpanProcessor"):
                    with patch("core.tracing.trace.set_tracer_provider"):
                        # Mock OpenAI instrumentor to test lines 43-44
                        mock_instrumentor = MagicMock()
                        with patch.dict(
                            "sys.modules",
                            {
                                "opentelemetry.instrumentation.openai": MagicMock(
                                    OpenAIInstrumentor=lambda: mock_instrumentor
                                )
                            },
                        ):
                            tracing.setup_tracing()
