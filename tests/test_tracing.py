
from core import tracing
import os

def test_get_tracer():
    assert tracing.get_tracer() is not None

def test_setup_tracing_without_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    tracing.setup_tracing()
    assert True
