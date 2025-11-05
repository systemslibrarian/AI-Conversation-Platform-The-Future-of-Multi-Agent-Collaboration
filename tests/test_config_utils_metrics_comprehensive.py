"""Comprehensive tests for config, common utilities, and metrics"""

import logging
import os
import sys
import tempfile
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.common import (
    add_jitter,
    hash_message,
    log_event,
    mask_api_key,
    sanitize_content,
    setup_logging,
    simple_similarity,
)
from core.config import Config, ConfigValidation
from core.metrics import (
    decrement_conversations,
    increment_conversations,
    record_call,
    record_error,
    record_latency,
    record_tokens,
    start_metrics_server,
)


# -------------------------
# Global test hygiene
# -------------------------
@pytest.fixture(autouse=True)
def _isolate_env_and_modules(monkeypatch):
    """
    Ensure environment mutations and module reloads don't leak across tests.
    - Snapshot env keys we mutate; restore after test.
    - Drop 'core.config' from sys.modules so re-import paths are fresh when requested.
    """
    touched_keys = ["PROMETHEUS_PORT", "TEST_API_KEY", "MISSING_KEY"]
    original_vals = {k: os.environ.get(k) for k in touched_keys}

    # Make sure any previous injected module is not reused in tests that re-import
    sys.modules.pop("core.config", None)

    yield

    # Restore env
    for k, v in original_vals.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)

    # Drop again to avoid surprising reuse in later tests
    sys.modules.pop("core.config", None)


class TestConfigValidation:
    """Test configuration validation"""

    def test_valid_config(self):
        config = ConfigValidation(
            TEMPERATURE=0.7,
            MAX_TOKENS=1024,
            SIMILARITY_THRESHOLD=0.85,
            MAX_CONSECUTIVE_SIMILAR=2,
            DEFAULT_MAX_TURNS=50,
            DEFAULT_TIMEOUT_MINUTES=30,
            MAX_CONTEXT_MSGS=10,
            PROMETHEUS_PORT=8000,
        )
        assert config.TEMPERATURE == 0.7
        assert config.MAX_TOKENS == 1024

    def test_temperature_validation(self):
        with pytest.raises(Exception):
            ConfigValidation(
                TEMPERATURE=3.0,  # Invalid
                MAX_TOKENS=1024,
                SIMILARITY_THRESHOLD=0.85,
                MAX_CONSECUTIVE_SIMILAR=2,
                DEFAULT_MAX_TURNS=50,
                DEFAULT_TIMEOUT_MINUTES=30,
                MAX_CONTEXT_MSGS=10,
                PROMETHEUS_PORT=8000,
            )

    def test_max_tokens_validation(self):
        with pytest.raises(Exception):
            ConfigValidation(
                TEMPERATURE=0.7,
                MAX_TOKENS=0,  # Invalid
                SIMILARITY_THRESHOLD=0.85,
                MAX_CONSECUTIVE_SIMILAR=2,
                DEFAULT_MAX_TURNS=50,
                DEFAULT_TIMEOUT_MINUTES=30,
                MAX_CONTEXT_MSGS=10,
                PROMETHEUS_PORT=8000,
            )

    def test_similarity_threshold_range(self):
        with pytest.raises(Exception):
            ConfigValidation(
                TEMPERATURE=0.7,
                MAX_TOKENS=1024,
                SIMILARITY_THRESHOLD=1.5,  # Invalid
                MAX_CONSECUTIVE_SIMILAR=2,
                DEFAULT_MAX_TURNS=50,
                DEFAULT_TIMEOUT_MINUTES=30,
                MAX_CONTEXT_MSGS=10,
                PROMETHEUS_PORT=8000,
            )

    def test_prometheus_port_range(self):
        with pytest.raises(Exception):
            ConfigValidation(
                TEMPERATURE=0.7,
                MAX_TOKENS=1024,
                SIMILARITY_THRESHOLD=0.85,
                MAX_CONSECUTIVE_SIMILAR=2,
                DEFAULT_MAX_TURNS=50,
                DEFAULT_TIMEOUT_MINUTES=30,
                MAX_CONTEXT_MSGS=10,
                PROMETHEUS_PORT=100,  # Too low
            )


class TestConfigClass:
    """Test Config class methods"""

    def test_get_api_key_success(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "test-value")
        key = Config.get_api_key("TEST_API_KEY")
        assert key == "test-value"

    def test_get_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("MISSING_KEY", raising=False)
        with pytest.raises(ValueError, match="not set in environment"):
            Config.get_api_key("MISSING_KEY")

    def test_validate_success(self):
        # Should not raise
        Config.validate()

    def test_config_import_warning(self, monkeypatch):
        """
        Force Config.validate() to fail during module import so we hit the
        try/except + warnings.warn(...) branch executed at import time.
        """
        monkeypatch.setenv("PROMETHEUS_PORT", "80")
        sys.modules.pop("core.config", None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import core.config  # noqa: F401  # re-import to trigger module-level validate

        assert any("Configuration validation" in str(rec.message) for rec in w)

    def test_validate_updates_attributes_successfully(self):
        """Test that validate() successfully validates and updates attributes."""
        # Save originals
        original_temp = Config.TEMPERATURE
        original_tokens = Config.MAX_TOKENS
        original_port = Config.PROMETHEUS_PORT
        original_context = Config.MAX_CONTEXT_MSGS
        
        try:
            # Set valid but different values
            Config.TEMPERATURE = 1.5
            Config.MAX_TOKENS = 2048
            Config.PROMETHEUS_PORT = 9090
            Config.MAX_CONTEXT_MSGS = 20
            
            # Validate should succeed and keep these valid values
            Config.validate()
            
            # Verify values are still within valid ranges
            assert 0.0 <= Config.TEMPERATURE <= 2.0
            assert 1 <= Config.MAX_TOKENS <= 32000
            assert 1024 <= Config.PROMETHEUS_PORT <= 65535
            assert 1 <= Config.MAX_CONTEXT_MSGS <= 100
            
        finally:
            # Restore original values
            Config.TEMPERATURE = original_temp
            Config.MAX_TOKENS = original_tokens
            Config.PROMETHEUS_PORT = original_port
            Config.MAX_CONTEXT_MSGS = original_context
            Config.validate()

    # ------------------------------------------------------------
    # ------------------------------------------------------------
    # NEW TEST – ensures invalid config raises error
    # ------------------------------------------------------------
    def test_validate_raises_on_invalid_config(self):
        """Config.validate() must raise ValueError when any field is out of range."""
        original_temp = Config.TEMPERATURE
        original_port = Config.PROMETHEUS_PORT

        try:
            Config.TEMPERATURE = 99.0  # > 2.0
            Config.PROMETHEUS_PORT = 80  # < 1024

            with pytest.raises(ValueError, match="Invalid configuration"):
                Config.validate()
        finally:
            Config.TEMPERATURE = original_temp
            Config.PROMETHEUS_PORT = original_port
            Config.validate()  # restore defaults

    def test_validate_invalid_temperature(self):
        original_temp = Config.TEMPERATURE
        try:
            Config.TEMPERATURE = 5.0  # Invalid
            with pytest.raises(ValueError, match="Invalid configuration"):
                Config.validate()
        finally:
            Config.TEMPERATURE = original_temp


class TestSetupLogging:
    """Test logging setup"""

    def test_setup_logging_creates_logger(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging("test_agent", tmpdir)
            try:
                assert logger.name == "test_agent"
                assert logger.level == logging.INFO
            finally:
                for h in list(logger.handlers):
                    logger.removeHandler(h)
                    h.close()

    def test_setup_logging_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "new_logs"
            logger = setup_logging("test_agent", str(log_dir))
            try:
                assert log_dir.exists()
            finally:
                for h in list(logger.handlers):
                    logger.removeHandler(h)
                    h.close()

    def test_setup_logging_file_handler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging("test_agent", tmpdir)
            try:
                file_handlers = [h for h in logger.handlers if hasattr(h, "baseFilename")]
                assert len(file_handlers) > 0
            finally:
                for h in list(logger.handlers):
                    logger.removeHandler(h)
                    h.close()

    def test_setup_logging_removes_existing_handlers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger1 = setup_logging("test_agent", tmpdir)
            try:
                handler_count1 = len(logger1.handlers)
            finally:
                for h in list(logger1.handlers):
                    logger1.removeHandler(h)
                    h.close()

        with tempfile.TemporaryDirectory() as tmpdir2:
            logger2 = setup_logging("test_agent", tmpdir2)
            try:
                handler_count2 = len(logger2.handlers)
            finally:
                for h in list(logger2.handlers):
                    logger2.removeHandler(h)
                    h.close()

        assert handler_count1 == handler_count2


class TestLogEvent:
    """Test event logging"""

    def test_log_event_format(self):
        logger = logging.getLogger("test")
        handler = MagicMock()
        handler.level = logging.DEBUG
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        try:
            log_event(logger, "test_event", {"key": "value", "number": 42})
            assert handler.handle.called
        finally:
            logger.removeHandler(handler)

    def test_log_event_includes_timestamp(self):
        import json

        logger = logging.getLogger("test_json")
        logger.setLevel(logging.INFO)

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False) as f:
            handler = logging.FileHandler(f.name)
            logger.addHandler(handler)

            try:
                log_event(logger, "test_event", {"data": "test"})
            finally:
                handler.close()
                logger.removeHandler(handler)

            with open(f.name, "r", encoding="utf-8") as log_file:
                log_line = log_file.read()
                log_data = json.loads(log_line)

        Path(f.name).unlink(missing_ok=True)
        assert "timestamp" in log_data
        assert log_data["event"] == "test_event"
        assert log_data["data"] == "test"


class TestSimpleSimilarity:
    """Test similarity calculation"""

    def test_identical_strings(self):
        assert simple_similarity("hello world", "hello world") == 1.0

    def test_completely_different(self):
        assert simple_similarity("hello world", "goodbye universe") < 0.5

    def test_partial_overlap(self):
        sim = simple_similarity("hello world", "hello there")
        assert 0.0 <= sim <= 1.0
        assert sim != 1.0

    def test_case_insensitive(self):
        sim1 = simple_similarity("Hello World", "hello world")
        sim2 = simple_similarity("hello world", "hello world")
        assert sim1 == sim2

    def test_empty_strings(self):
        assert simple_similarity("", "") == 1.0

    def test_one_empty_string(self):
        assert simple_similarity("hello", "") == 0.0

    def test_short_strings(self):
        assert simple_similarity("hi", "hi") == 1.0


class TestHashMessage:
    """Test message hashing"""

    def test_hash_message_consistent(self):
        h1 = hash_message("test content")
        h2 = hash_message("test content")
        assert h1 == h2

    def test_hash_message_different(self):
        assert hash_message("content 1") != hash_message("content 2")

    def test_hash_message_length(self):
        assert len(hash_message("test")) == 8


class TestAddJitter:
    """Test jitter function"""

    def test_add_jitter_range(self):
        for _ in range(100):
            jittered = add_jitter(10.0, jitter_range=0.2)
            assert 8.0 <= jittered <= 12.0

    def test_add_jitter_minimum(self):
        jittered = add_jitter(0.01, jitter_range=0.5)
        assert jittered >= 0.1

    def test_add_jitter_custom_range(self):
        for _ in range(50):
            jittered = add_jitter(10.0, jitter_range=0.5)
            assert 5.0 <= jittered <= 15.0

    def test_add_jitter_zero_range(self):
        assert add_jitter(10.0, jitter_range=0.0) == 10.0


class TestMaskApiKey:
    """Test API key masking"""

    def test_mask_anthropic_key(self):
        text = "My key is sk-ant-1234567890123456789012345"
        masked = mask_api_key(text)
        assert "[ANTHROPIC_KEY]" in masked
        assert "sk-ant-" not in masked

    def test_mask_openai_key(self):
        text = "My key is sk-123456789012345678901234567890"
        masked = mask_api_key(text)
        assert "[OPENAI_KEY]" in masked or "[API_KEY]" in masked
        assert "sk-123456789012345678901234567890" not in masked

    def test_mask_perplexity_key(self):
        text = "My key is pplx-123456789012345678901234567890"
        masked = mask_api_key(text)
        assert "[PERPLEXITY_KEY]" in masked
        assert "pplx-" not in masked

    def test_mask_generic_key(self):
        text = "My key is abcdefghijklmnopqrstuvwxyz1234567890"
        masked = mask_api_key(text)
        assert "[API_KEY]" in masked

    def test_mask_multiple_keys(self):
        text = "Key1: sk-ant-12345678901234567890 Key2: sk-9876543210987654321098765"
        masked = mask_api_key(text)
        assert masked.count("[") >= 2

    def test_mask_no_keys(self):
        text = "This is normal text without keys"
        masked = mask_api_key(text)
        assert masked == text


class TestSanitizeContent:
    """Test content sanitization"""

    def test_sanitize_script_tags(self):
        content = "<div><script>alert('xss')</script>Safe content</div>"
        sanitized = sanitize_content(content)
        assert "[FILTERED]" in sanitized
        assert "alert" not in sanitized

    def test_sanitize_javascript(self):
        content = '<a href="javascript:alert()">Click</a>'
        sanitized = sanitize_content(content)
        assert "[FILTERED]" in sanitized

    def test_sanitize_event_handlers(self):
        content = '<div onclick="doEvil()">Click me</div>'
        sanitized = sanitize_content(content)
        assert "[FILTERED]" in sanitized

    def test_sanitize_sql_injection(self):
        content = "SELECT * FROM users; DROP TABLE users;"
        sanitized = sanitize_content(content)
        assert "[FILTERED]" in sanitized

    def test_sanitize_safe_content(self):
        content = "This is safe content with no dangerous patterns"
        sanitized = sanitize_content(content)
        assert sanitized == content

    def test_sanitize_case_insensitive(self):
        content = "<SCRIPT>alert()</SCRIPT>"
        sanitized = sanitize_content(content)
        assert "[FILTERED]" in sanitized


class TestMetricsRecording:
    """Test metrics recording functions"""

    def test_record_call_success(self):
        record_call("TestProvider", "test-model", "success")

    def test_record_call_error(self):
        record_call("TestProvider", "test-model", "error")

    def test_record_latency(self):
        record_latency("TestProvider", "test-model", 1.5)

    def test_record_tokens(self):
        record_tokens("TestProvider", "test-model", 100, 50)

    def test_record_error(self):
        record_error("TestProvider", "timeout")
        record_error("TestProvider", "api_error")

    def test_increment_conversations(self):
        increment_conversations()

    def test_decrement_conversations(self):
        decrement_conversations()

    def test_metrics_with_special_characters(self):
        record_call("Test-Provider", "model/v1", "success")
        record_error("Test Provider", "rate_limit")


class TestMetricsServer:
    """Test metrics server startup"""

    def test_start_metrics_server_default_port(self):
        with patch("core.metrics.start_http_server") as mock_start:
            start_metrics_server()
            mock_start.assert_called_once()

    def test_start_metrics_server_custom_port(self):
        with patch("core.metrics.start_http_server") as mock_start:
            start_metrics_server(9999)
            mock_start.assert_called_once_with(9999)

    def test_start_metrics_server_error_handling(self):
        with patch("core.metrics.start_http_server", side_effect=OSError("Port in use")):
            start_metrics_server(8000)

    def test_start_metrics_server_from_env(self, monkeypatch):
        monkeypatch.setenv("PROMETHEUS_PORT", "9090")
        with patch("core.metrics.start_http_server") as mock_start:
            start_metrics_server(None)
            mock_start.assert_called_once_with(9090)


class TestMetricsErrorHandling:
    """Test metrics error handling"""

    def test_record_call_with_exception(self):
        with patch("core.metrics.API_CALLS.labels", side_effect=Exception("Metric error")):
            record_call("Test", "model", "success")

    def test_record_latency_with_exception(self):
        with patch("core.metrics.RESPONSE_LATENCY.labels", side_effect=Exception("Metric error")):
            record_latency("Test", "model", 1.0)

    def test_record_tokens_with_exception(self):
        with patch("core.metrics.TOKEN_USAGE.labels", side_effect=Exception("Metric error")):
            record_tokens("Test", "model", 10, 20)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
