"""
Comprehensive tests for core.metrics, covering both happy-path and
unhappy-path (exception handling) scenarios.

Refinements:
- Parametrized happy-path tests to reduce repetition.
- Robust mocking of the metric objects to be resilient to kw-only usage.
- Verifies both log text and CORRECT LEVEL for unhappy-path cases.
- Uses record.getMessage() for maximum logging compatibility.
- Adds explicit isolation (caplog.clear) and a smoke test for exception propagation.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from core import metrics


# --- Fixtures ---

@pytest.fixture(autouse=True)
def capture_metrics_logs(caplog):
    """
    Capture WARNING+ logs from the 'core.metrics' logger only.
    Set level to WARNING to correctly capture both logger.error and logger.warning calls.
    """
    caplog.set_level(logging.WARNING, logger="core.metrics")
    return caplog


# --- Helpers ---

def assert_logged_once(caplog, level, expected_substring):
    """
    Asserts a log entry exists with at least the required level
    and containing the expected substring, using record.getMessage().
    """
    assert any(
        rec.levelno >= level and expected_substring in rec.getMessage()
        for rec in caplog.records
    ), f"Expected log with level>={level} containing: {expected_substring!r}\nGot: {[rec.getMessage() for rec in caplog.records]}"


# --- Happy Path (Parametrized) ---

@pytest.mark.parametrize(
    "attr, call, expected_labels_kwargs, terminal_method, terminal_args",
    [
        # record_call (default status)
        (
            "API_CALLS",
            lambda: metrics.record_call("Test", "gpt", "success"),
            {"provider": "Test", "model": "gpt", "status": "success"},
            "inc",
            (),
        ),
        # record_call (custom status)
        (
            "API_CALLS",
            lambda: metrics.record_call("Test", "gpt", "rate_limit"),
            {"provider": "Test", "model": "gpt", "status": "rate_limit"},
            "inc",
            (),
        ),
        # record_latency
        (
            "RESPONSE_LATENCY",
            lambda: metrics.record_latency("Test", "gpt", 0.42),
            {"provider": "Test", "model": "gpt"},
            "observe",
            (0.42,),
        ),
    ],
    ids=["call_success", "call_rate_limit", "latency_observe"],
)
def test_happy_path_label_chain(capture_metrics_logs, attr, call, expected_labels_kwargs, terminal_method, terminal_args):
    metric_mock = MagicMock()
    with patch(f"core.metrics.{attr}", metric_mock):
        call()

    metric_mock.labels.assert_called_once_with(**expected_labels_kwargs)
    getattr(metric_mock.labels.return_value, terminal_method).assert_called_once_with(*terminal_args)
    # No warnings/errors should be logged
    assert not capture_metrics_logs.records


def test_record_tokens_happy(capture_metrics_logs):
    """Mocks TOKEN_USAGE and routes different .labels() returns by 'type'."""
    metric_mock = MagicMock()
    metric_input = MagicMock()
    metric_output = MagicMock()

    # CRITICAL: Assert that the mocks are distinct objects, guarding against refactoring bugs.
    assert metric_input is not metric_output

    def labels_side_effect(**kwargs):
        return metric_input if kwargs.get("type") == "input" else metric_output

    metric_mock.labels.side_effect = labels_side_effect

    with patch("core.metrics.TOKEN_USAGE", metric_mock):
        metrics.record_tokens("Test", "gpt", 11, 22)

    # Assert exactly two calls were made to labels (input and output)
    assert metric_mock.labels.call_count == 2
    metric_mock.labels.assert_any_call(provider="Test", model="gpt", type="input")
    metric_mock.labels.assert_any_call(provider="Test", model="gpt", type="output")
    metric_input.inc.assert_called_once_with(11)
    metric_output.inc.assert_called_once_with(22)
    assert not capture_metrics_logs.records


def test_record_error_happy(capture_metrics_logs):
    metric_mock = MagicMock()
    with patch("core.metrics.ERRORS", metric_mock):
        metrics.record_error("Test", "api_error")

    metric_mock.labels.assert_called_once_with(provider="Test", error_type="api_error")
    metric_mock.labels.return_value.inc.assert_called_once()
    assert not capture_metrics_logs.records


def test_increment_conversations_happy(capture_metrics_logs):
    metric_mock = MagicMock()
    with patch("core.metrics.ACTIVE_CONVERSATIONS", metric_mock):
        metrics.increment_conversations()
    metric_mock.inc.assert_called_once()
    assert not capture_metrics_logs.records


def test_decrement_conversations_happy(capture_metrics_logs):
    metric_mock = MagicMock()
    with patch("core.metrics.ACTIVE_CONVERSATIONS", metric_mock):
        metrics.decrement_conversations()
    metric_mock.dec.assert_called_once()
    assert not capture_metrics_logs.records


def test_start_metrics_server_happy(capture_metrics_logs):
    with patch("core.metrics.start_http_server") as start_http_server:
        metrics.start_metrics_server(9999)
    start_http_server.assert_called_once_with(9999)
    assert not capture_metrics_logs.records


# --- Smoke Test: No Propagation ---

@pytest.mark.parametrize(
    "patch_target, metric_func, args",
    [
        ("API_CALLS.labels", metrics.record_call, ("Test", "model", "success")),
        ("RESPONSE_LATENCY.labels", metrics.record_latency, ("Test", "model", 1.0)),
        ("TOKEN_USAGE.labels", metrics.record_tokens, ("Test", "model", 1, 1)),
        ("ERRORS.labels", metrics.record_error, ("Test", "api_error")),
        ("ACTIVE_CONVERSATIONS.inc", metrics.increment_conversations, ()),
        ("ACTIVE_CONVERSATIONS.dec", metrics.decrement_conversations, ()),
    ],
    ids=["call", "latency", "tokens", "error", "inc", "dec"],
)
def test_metric_functions_do_not_propagate_exceptions(patch_target, metric_func, args):
    """
    Smoke test: Ensures that metric functions never re-raise exceptions
    (i.e., they run without raising anything, protecting the main application loop).
    """
    # Patch the actual metric object method to fail
    with patch(f"core.metrics.{patch_target}", side_effect=Exception("FAIL")):
        # We assert that the function runs without raising any exception
        try:
            metric_func(*args)
        except Exception as e:
            pytest.fail(f"Metric function {metric_func.__name__} raised an unhandled exception: {e}")


# --- Unhappy Path (Exceptions) ---

def test_record_call_exception_from_labels(capture_metrics_logs):
    """Tests the logger.error case where .labels() fails."""
    capture_metrics_logs.clear()
    err = Exception("Test Error")
    with patch("core.metrics.API_CALLS.labels", side_effect=err):
        metrics.record_call("Test", "model", "success")
    assert_logged_once(capture_metrics_logs, logging.ERROR, f"Failed to record call metric: {err}")


def test_record_call_exception_after_labels_inc(capture_metrics_logs):
    """Tests the logger.error case where .inc() fails."""
    capture_metrics_logs.clear()
    metric_mock = MagicMock()
    metric_mock.labels.return_value.inc.side_effect = RuntimeError("boom")
    with patch("core.metrics.API_CALLS", metric_mock):
        metrics.record_call("Test", "model", "success")
    assert_logged_once(capture_metrics_logs, logging.ERROR, "Failed to record call metric: RuntimeError('boom')")


def test_record_latency_exception_from_labels(capture_metrics_logs):
    """Tests the logger.error case where .labels() fails."""
    capture_metrics_logs.clear()
    err = Exception("Test Error")
    with patch("core.metrics.RESPONSE_LATENCY.labels", side_effect=err):
        metrics.record_latency("Test", "model", 1.23)
    assert_logged_once(capture_metrics_logs, logging.ERROR, f"Failed to record latency metric: {err}")


def test_record_latency_exception_after_labels_observe(capture_metrics_logs):
    """Tests the logger.error case where .observe() fails."""
    capture_metrics_logs.clear()
    metric_mock = MagicMock()
    metric_mock.labels.return_value.observe.side_effect = ValueError("nope")
    with patch("core.metrics.RESPONSE_LATENCY", metric_mock):
        metrics.record_latency("Test", "model", 1.23)
    assert_logged_once(capture_metrics_logs, logging.ERROR, "Failed to record latency metric: ValueError('nope')")


def test_record_tokens_exception_from_labels(capture_metrics_logs):
    """Tests the logger.error case where .labels() fails."""
    capture_metrics_logs.clear()
    err = Exception("Test Error")
    with patch("core.metrics.TOKEN_USAGE.labels", side_effect=err):
        metrics.record_tokens("Test", "model", 10, 20)
    assert_logged_once(capture_metrics_logs, logging.ERROR, f"Failed to record token metric: {err}")


def test_record_tokens_exception_after_input_inc(capture_metrics_logs):
    """Tests failure on the first metric update (input tokens)."""
    capture_metrics_logs.clear()
    metric_mock = MagicMock()
    # input path raises
    input_counter = MagicMock()
    input_counter.inc.side_effect = RuntimeError("input failed")

    output_counter = MagicMock()

    def labels_side_effect(**kwargs):
        return input_counter if kwargs.get("type") == "input" else output_counter

    metric_mock.labels.side_effect = labels_side_effect

    with patch("core.metrics.TOKEN_USAGE", metric_mock):
        metrics.record_tokens("Test", "model", 10, 20)

    assert_logged_once(capture_metrics_logs, logging.ERROR, "Failed to record token metric: RuntimeError('input failed')")


def test_record_tokens_exception_after_output_inc(capture_metrics_logs):
    """Tests failure on the second metric update (output tokens)."""
    capture_metrics_logs.clear()
    metric_mock = MagicMock()
    # output path raises
    input_counter = MagicMock()
    output_counter = MagicMock()
    output_counter.inc.side_effect = RuntimeError("output failed")

    def labels_side_effect(**kwargs):
        return input_counter if kwargs.get("type") == "input" else output_counter

    metric_mock.labels.side_effect = labels_side_effect

    with patch("core.metrics.TOKEN_USAGE", metric_mock):
        metrics.record_tokens("Test", "model", 10, 20)

    assert_logged_once(capture_metrics_logs, logging.ERROR, "Failed to record token metric: RuntimeError('output failed')")


def test_record_error_exception_from_labels(capture_metrics_logs):
    """Tests the logger.error case where .labels() fails."""
    capture_metrics_logs.clear()
    err = Exception("Test Error")
    with patch("core.metrics.ERRORS.labels", side_effect=err):
        metrics.record_error("Test", "api_error")
    assert_logged_once(capture_metrics_logs, logging.ERROR, f"Failed to record error metric: {err}")


def test_record_error_exception_after_inc(capture_metrics_logs):
    """Tests the logger.error case where .inc() fails."""
    capture_metrics_logs.clear()
    metric_mock = MagicMock()
    metric_mock.labels.return_value.inc.side_effect = RuntimeError("err bump")
    with patch("core.metrics.ERRORS", metric_mock):
        metrics.record_error("Test", "api_error")
    assert_logged_once(capture_metrics_logs, logging.ERROR, "Failed to record error metric: RuntimeError('err bump')")


def test_increment_conversations_exception(capture_metrics_logs):
    """Tests the logger.error case where .inc() fails."""
    capture_metrics_logs.clear()
    err = Exception("Test Error")
    with patch("core.metrics.ACTIVE_CONVERSATIONS.inc", side_effect=err):
        metrics.increment_conversations()
    assert_logged_once(capture_metrics_logs, logging.ERROR, f"Failed to increment conversations: {err}")


def test_decrement_conversations_exception(capture_metrics_logs):
    """Tests the logger.error case where .dec() fails."""
    capture_metrics_logs.clear()
    err = Exception("Test Error")
    with patch("core.metrics.ACTIVE_CONVERSATIONS.dec", side_effect=err):
        metrics.decrement_conversations()
    assert_logged_once(capture_metrics_logs, logging.ERROR, f"Failed to decrement conversations: {err}")


def test_start_metrics_server_os_error(capture_metrics_logs):
    """Tests the logger.warning case in start_metrics_server"""
    capture_metrics_logs.clear()
    err = OSError("Port in use")
    with patch("core.metrics.start_http_server", side_effect=err):
        metrics.start_metrics_server(9999)
    # This is the ONLY case that logs a WARNING
    assert_logged_once(capture_metrics_logs, logging.WARNING, f"Could not start metrics server on port 9999: {err}")


def test_start_metrics_server_generic_exception(capture_metrics_logs):
    """Tests the logger.error case in start_metrics_server"""
    capture_metrics_logs.clear()
    err = Exception("Generic Error")
    with patch("core.metrics.start_http_server", side_effect=err):
        metrics.start_metrics_server(9999)
    # This logs an ERROR
    assert_logged_once(capture_metrics_logs, logging.ERROR, f"Failed to start metrics server: {err}")
