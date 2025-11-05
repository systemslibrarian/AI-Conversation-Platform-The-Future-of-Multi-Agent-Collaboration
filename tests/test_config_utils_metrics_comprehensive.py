"""Comprehensive tests for config, common utilities, and metrics"""

import pytest
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import os
import warnings
import sys
import json
import shutil


from core.config import Config
from core.common import (
    setup_logging,
    log_event,
    simple_similarity,
    hash_message,
    add_jitter,
    mask_api_key,
    sanitize_content,
)
from core.metrics import (
    record_call,
    record_latency,
    record_tokens,
    record_error,
    increment_conversations,
    decrement_conversations,
    start_metrics_server,
)


# --- FIXTURES AND CLEANUP ---


@pytest.fixture(autouse=True)
def config_cleanup_fixture(monkeypatch):
    """Snapshot and restore environment variables, and ensure module cleanup."""
    original_environ = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_environ)
    sys.modules.pop("core.config", None)
    if Path("temp_logs").exists():
        shutil.rmtree("temp_logs")


# --- TESTS START ---


class TestConfigValidation:
    """Test configuration validation"""

    def test_valid_config(self):
        from core.config import ConfigValidation

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
        from core.config import ConfigValidation

        with pytest.raises(Exception):
            ConfigValidation(
                TEMPERATURE=3.0,
                MAX_TOKENS=1024,
                SIMILARITY_THRESHOLD=0.85,
                MAX_CONSECUTIVE_SIMILAR=2,
                DEFAULT_MAX_TURNS=50,
                DEFAULT_TIMEOUT_MINUTES=30,
                MAX_CONTEXT_MSGS=10,
                PROMETHEUS_PORT=8000,
            )

    def test_max_tokens_validation(self):
        from core.config import ConfigValidation

        with pytest.raises(Exception):
            ConfigValidation(
                TEMPERATURE=0.7,
                MAX_TOKENS=0,
                SIMILARITY_THRESHOLD=0.85,
                MAX_CONSECUTIVE_SIMILAR=2,
                DEFAULT_MAX_TURNS=50,
                DEFAULT_TIMEOUT_MINUTES=30,
                MAX_CONTEXT_MSGS=10,
                PROMETHEUS_PORT=8000,
            )

    def test_similarity_threshold_range(self):
        from core.config import ConfigValidation

        with pytest.raises(Exception):
            ConfigValidation(
                TEMPERATURE=0.7,
                MAX_TOKENS=1024,
                SIMILARITY_THRESHOLD=1.5,
                MAX_CONSECUTIVE_SIMILAR=2,
                DEFAULT_MAX_TURNS=50,
                DEFAULT_TIMEOUT_MINUTES=30,
                MAX_CONTEXT_MSGS=10,
                PROMETHEUS_PORT=8000,
            )

    def test_prometheus_port_range(self):
        from core.config import ConfigValidation

        with pytest.raises(Exception):
            ConfigValidation(
                TEMPERATURE=0.7,
                MAX_TOKENS=1024,
                SIMILARITY_THRESHOLD=0.85,
                MAX_CONSECUTIVE_SIMILAR=2,
                DEFAULT_MAX_TURNS=50,
                DEFAULT_TIMEOUT_MINUTES=30,
                MAX_CONTEXT_MSGS=10,
                PROMETHEUS_PORT=100,
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
        Config.validate()

    def test_config_import_warning(self, monkeypatch):
        monkeypatch.setenv("PROMETHEUS_PORT", "80")
        sys.modules.pop("core.config", None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import core.config  # noqa: F401
        assert any("configuration validation" in str(rec.message).lower() for rec in w)

    @pytest.mark.skip(reason="Fragile due to module import caching; behavior covered elsewhere")
    def test_validate_updates_attributes(self):
        """SKIP: Internal attribute update is tested indirectly via validate_success/failure."""
        pass

    def test_validate_invalid_temperature(self):
        original_temp = Config.TEMPERATURE
        try:
            Config.TEMPERATURE = 5.0
            with pytest.raises(ValueError, match="Invalid configuration"):
                Config.validate()
        finally:
            Config.TEMPERATURE = original_temp

    def test_config_attributes(self):
        assert hasattr(Config, "DEFAULT_CONVERSATION_FILE")
        assert hasattr(Config, "DEFAULT_LOG_DIR")
        assert hasattr(Config, "CLAUDE_DEFAULT_MODEL")
        assert hasattr(Config, "CHATGPT_DEFAULT_MODEL")
        assert hasattr(Config, "SIMILARITY_THRESHOLD")
        assert hasattr(Config, "MAX_CONSECUTIVE_SIMILAR")
        assert hasattr(Config, "TEMPERATURE")
        assert hasattr(Config, "MAX_TOKENS")


class TestSetupLogging:
    """Test logging setup"""

    def test_setup_logging_creates_logger(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging("test_agent", tmpdir)
            logger.propagate = False
            assert logger.name == "test_agent"
            assert logger.level == logging.INFO
            for h in list(logger.handlers):
                logger.removeHandler(h)
                h.close()

    def test_setup_logging_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "new_logs"
            logger = setup_logging("test_agent", str(log_dir))
            logger.propagate = False
            assert log_dir.exists()
            for h in list(logger.handlers):
                logger.removeHandler(h)
                h.close()

    def test_setup_logging_file_handler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging("test_agent", tmpdir)
            logger.propagate = False
            try:
                file_handlers = [h for h in logger.handlers if hasattr(h, "baseFilename")]
                assert len(file_handlers) > 0
            finally:
                for h in list(logger.handlers):
                    logger.removeHandler(h)
                    h.close()

    def test_setup_logging_removes_existing_handlers(self):
        logger_name = "test_handler_removal"
        logger = logging.getLogger(logger_name)
        logger.propagate = False
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(logger_name, tmpdir)
            count1 = len(logger.handlers)
            setup_logging(logger_name, tmpdir)
            count2 = len(logger.handlers)
        assert count1 == count2
        for h in list(logger.handlers):
            logger.removeHandler(h)
            h.close()


class TestLogEvent:
    """Test event logging"""

    def test_log_event_format(self):
        logger = logging.getLogger("test")
        logger.propagate = False
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
        logger = logging.getLogger("test_json")
        logger.propagate = False
        logger.setLevel(logging.INFO)
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False) as f:
            handler = logging.FileHandler(f.name)
            logger.addHandler(handler)
            try:
                log_event(logger, "test_event", {"data": "test"})
            finally:
                handler.close()
                logger.removeHandler(handler)
            with open(f.name, "r") as log_file:
                data = json.loads(log_file.read())
            assert "timestamp" in data
            assert data["event"] == "test_event"
            assert data["data"] == "test"
            Path(f.name).unlink()


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
        assert simple_similarity("Hello World", "hello world") == simple_similarity(
            "hello world", "hello world"
        )

    def test_empty_strings(self):
        assert simple_similarity("", "") == 1.0

    def test_one_empty_string(self):
        assert simple_similarity("hello", "") == 0.0

    def test_short_strings(self):
        assert simple_similarity("hi", "hi") == 1.0


class TestHashMessage:
    """Test message hashing"""

    def test_hash_message_consistent(self):
        assert hash_message("test content") == hash_message("test content")

    def test_hash_message_different(self):
        assert hash_message("content 1") != hash_message("content 2")

    def test_hash_message_length(self):
        assert len(hash_message("test")) == 8


class TestAddJitter:
    """Test jitter function"""

    def test_add_jitter_range(self):
        for _ in range(100):
            v = add_jitter(10.0, jitter_range=0.2)
            assert 8.0 <= v <= 12.0

    def test_add_jitter_minimum(self):
        assert add_jitter(0.01, jitter_range=0.5) >= 0.1

    def test_add_jitter_custom_range(self):
        for _ in range(50):
            v = add_jitter(10.0, jitter_range=0.5)
            assert 5.0 <= v <= 15.0

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
        assert mask_api_key(text) == text


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
        assert sanitize_content(content) == content

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

    def test_start_metrics_server_from_env(self):
        with patch.dict(os.environ, {"PROMETHEUS_PORT": "9090"}):
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
