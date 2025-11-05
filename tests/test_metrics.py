"""
Comprehensive tests for core.metrics, covering both happy-path
and unhappy-path (exception handling) scenarios.

Refinements:
- Happy path: Mocks the entire metric object (e.g., API_CALLS)
  to be robust against positional vs. keyword args.
- Unhappy path: Asserts the specific error message is logged.
- Fully aligned with actual core.metrics implementation.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock

# Import the functions we need to test
from core import metrics

# --- Fixtures ---

@pytest.fixture(autouse=True)
def capture_logs(caplog):
    """
    Fixture to capture logs at the ERROR level, but only from
    the 'core.metrics' logger.
    """
    caplog.set_level(logging.ERROR, logger="core.metrics")
    return caplog


# --- Happy Path Tests ---

def test_record_call_happy(capture_logs):
    """Mocks the whole API_CALLS object to test labels().inc() chain"""
    metric_mock = MagicMock()
    with patch("core.metrics.API_CALLS", metric_mock):
        metrics.record_call("Test", "gpt", "success")
    
    metric_mock.labels.assert_called_once_with(provider="Test", model="gpt", status="success")
    metric_mock.labels.return_value.inc.assert_called_once()
    assert not capture_logs.records


def test_record_latency_happy(capture_logs):
    """Mocks the whole RESPONSE_LATENCY object to test labels().observe() chain"""
    metric_mock = MagicMock()
    with patch("core.metrics.RESPONSE_LATENCY", metric_mock):
        metrics.record_latency("Test", "gpt", 0.42)
    
    metric_mock.labels.assert_called_once_with(provider="Test", model="gpt")
    metric_mock.labels.return_value.observe.assert_called_once_with(0.42)
    assert not capture_logs.records


def test_record_tokens_happy(capture_logs):
    """Mocks the whole TOKEN_USAGE object to test multiple .labels() calls"""
    metric_mock = MagicMock()
    metric_input = MagicMock()
    metric_output = MagicMock()

    def labels_side_effect(**kwargs):
        if kwargs.get("type") == "input":
            return metric_input
        return metric_output

    metric_mock.labels.side_effect = labels_side_effect

    with patch("core.metrics.TOKEN_USAGE", metric_mock):
        metrics.record_tokens("Test", "gpt", 11, 22)

    metric_mock.labels.assert_any_call(provider="Test", model="gpt", type="input")
    metric_mock.labels.assert_any_call(provider="Test", model="gpt", type="output")
    metric_input.inc.assert_called_once_with(11)
    metric_output.inc.assert_called_once_with(22)
    assert not capture_logs.records


def test_record_error_happy(capture_logs):
    """Mocks the whole ERRORS object to test labels().inc() chain"""
    metric_mock = MagicMock()
    with patch("core.metrics.ERRORS", metric_mock):
        metrics.record_error("Test", "api_error")
    
    metric_mock.labels.assert_called_once_with(provider="Test", error_type="api_error")
    metric_mock.labels.return_value.inc.assert_called_once()
    assert not capture_logs.records


def test_increment_conversations_happy(capture_logs):
    """Mocks the whole ACTIVE_CONVERSATIONS object to test .inc()"""
    metric_mock = MagicMock()
    with patch("core.metrics.ACTIVE_CONVERSATIONS", metric_mock):
        metrics.increment_conversations()
    
    metric_mock.inc.assert_called_once()
    assert not capture_logs.records


def test_decrement_conversations_happy(capture_logs):
    """Mocks the whole ACTIVE_CONVERSATIONS object to test .dec()"""
    metric_mock = MagicMock()
    with patch("core.metrics.ACTIVE_CONVERSATIONS", metric_mock):
        metrics.decrement_conversations()
    
    metric_mock.dec.assert_called_once()
    assert not capture_logs.records


def test_start_metrics_server_happy(capture_logs):
    """Tests the happy path for start_http_server (external function)"""
    with patch("core.metrics.start_http_server") as start_http_server:
        metrics.start_metrics_server(9999)
    start_http_server.assert_called_once_with(9999)
    assert not capture_logs.records


# --- Unhappy Path (Exception) Tests ---

def test_record_call_exception(capture_logs):
    """Tests that record_call logs the specific error."""
    test_exception = Exception("Test Error")
    with patch("core.metrics.API_CALLS.labels", side_effect=test_exception):
        metrics.record_call("Test", "model", "success")
    assert f"Failed to record call metric: {test_exception}" in capture_logs.text


def test_record_latency_exception(capture_logs):
    """Tests that record_latency logs the specific error."""
    test_exception = Exception("Test Error")
    with patch("core.metrics.RESPONSE_LATENCY.labels", side_effect=test_exception):
        metrics.record_latency("Test", "model", 1.23)
    assert f"Failed to record latency metric: {test_exception}" in capture_logs.text


def test_record_tokens_exception(capture_logs):
    """Tests that record_tokens logs the specific error."""
    test_exception = Exception("Test Error")
    with patch("core.metrics.TOKEN_USAGE.labels", side_effect=test_exception):
        metrics.record_tokens("Test", "model", 10, 20)
    assert f"Failed to record token metric: {test_exception}" in capture_logs.text


def test_record_error_exception(capture_logs):
    """Tests that record_error logs the specific error."""
    test_exception = Exception("Test Error")
    with patch("core.metrics.ERRORS.labels", side_effect=test_exception):
        metrics.record_error("Test", "api_error")
    assert f"Failed to record error metric: {test_exception}" in capture_logs.text


def test_increment_conversations_exception(capture_logs):
    """Tests that increment_conversations logs the specific error."""
    test_exception = Exception("Test Error")
    with patch("core.metrics.ACTIVE_CONVERSATIONS.inc", side_effect=test_exception):
        metrics.increment_conversations()
    assert f"Failed to increment conversations: {test_exception}" in capture_logs.text


def test_decrement_conversations_exception(capture_logs):
    """Tests that decrement_conversations logs the specific error."""
    test_exception = Exception("Test Error")
    with patch("core.metrics.ACTIVE_CONVERSATIONS.dec", side_effect=test_exception):
        metrics.decrement_conversations()
    assert f"Failed to decrement conversations: {test_exception}" in capture_logs.text


def test_start_metrics_server_os_error(capture_logs):
    """Tests that start_metrics_server logs the specific OSError."""
    test_exception = OSError("Port in use")
    with patch("core.metrics.start_http_server", side_effect=test_exception):
        metrics.start_metrics_server(9999)
    # Matches logger.warning text in metrics.py
    assert f"Could not start metrics server on port 9999: {test_exception}" in capture_logs.text


def test_start_metrics_server_generic_exception(capture_logs):
    """Tests that start_metrics_server logs other exceptions."""
    test_exception = Exception("Generic Error")
    with patch("core.metrics.start_http_server", side_effect=test_exception):
        metrics.start_metrics_server(9999)
    assert f"Failed to start metrics server: {test_exception}" in capture_logs.text
