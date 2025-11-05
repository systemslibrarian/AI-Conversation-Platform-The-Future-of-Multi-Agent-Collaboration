"""Comprehensive tests for config, common utilities, and metrics"""

import pytest
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import os
from pydantic import BaseModel  # Import BaseModel for mocking Pydantic
import warnings 
import sys 
import json
import shutil # For safely removing log directories


from core.config import Config, ConfigValidation
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
    
    # 1. Snapshot Environment
    original_environ = os.environ.copy()
    
    # 2. Yield to run the test
    yield

    # 3. Restore Environment
    os.environ.clear()
    os.environ.update(original_environ)

    # 4. Clean up module cache for core.config
    sys.modules.pop("core.config", None)
    
    # 5. Clean up any temporary log directories created by setup_logging tests
    # Note: Using Path and shutil.rmtree for robust cleanup
    if Path('temp_logs').exists():
        shutil.rmtree('temp_logs')


# --- TESTS START ---

class TestConfigValidation:
    """Test configuration validation"""

    def test_valid_config(self):
        """Test valid configuration"""
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
        """Test temperature must be between 0 and 2"""
        with pytest.raises(Exception):  # Pydantic ValidationError
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
        """Test MAX_TOKENS must be positive"""
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
        """Test similarity threshold must be 0-1"""
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
        """Test Prometheus port must be valid"""
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
        """Test getting API key from environment"""
        monkeypatch.setenv("TEST_API_KEY", "test-value")
        key = Config.get_api_key("TEST_API_KEY")
        assert key == "test-value"

    def test_get_api_key_missing(self, monkeypatch):
        """Test error when API key missing"""
        monkeypatch.delenv("MISSING_KEY", raising=False)
        with pytest.raises(ValueError, match="not set in environment"):
            Config.get_api_key("MISSING_KEY")

    def test_validate_success(self):
        """Test successful validation"""
        # Should not raise
        Config.validate()

    # --- covers import-time warning path in core.config ---
    def test_config_import_warning(self, monkeypatch):
        """
        Force Config.validate() to fail during module import so we hit the
        try/except + warnings.warn(...) branch executed at import time.
        """
        
        # Make validation fail by supplying an invalid env var (e.g., low port)
        monkeypatch.setenv("PROMETHEUS_PORT", "80")

        # Ensure a fresh import triggers module-level validation
        sys.modules.pop("core.config", None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import core.config  # noqa: F401  # re-import to trigger module-level validate

        assert any("Configuration validation warning" in str(rec.message) for rec in w)
    # --- END NEW TEST ---

    # --- ensure validate() overwrites attributes ---
    def test_validate_updates_attributes(self):
        """Test successful validation overwrites live class attributes."""

        # Store original values for cleanup
        original_temp = Config.TEMPERATURE
        original_max = Config.MAX_TOKENS
        original_port = Config.PROMETHEUS_PORT
        original_max_context = Config.MAX_CONTEXT_MSGS
        
        # 0. Set initial values different from mock target (these are invalid but won't cause the test to fail now)
        Config.TEMPERATURE = 99.0
        Config.MAX_TOKENS = 1
        Config.PROMETHEUS_PORT = 1000
        Config.MAX_CONTEXT_MSGS = 1

        # The data we want to assert were set successfully
        MOCK_DUMP = {
            "TEMPERATURE": 0.5,
            "MAX_TOKENS": 2000,
            "SIMILARITY_THRESHOLD": 0.80,
            "MAX_CONSECUTIVE_SIMILAR": 3,
            "DEFAULT_MAX_TURNS": 60,
            "DEFAULT_TIMEOUT_MINUTES": 40,
            "MAX_CONTEXT_MSGS": 15,
            "PROMETHEUS_PORT": 9000
        }

        try:
            # 1. Patch the symbol 'ConfigValidation' directly within the 'core.config' module
            with patch('core.config.ConfigValidation') as MockPydanticClass:
                
                # Configure the mock instance to return our desired data when .model_dump() is called
                # This bypasses the validation constructor failure while allowing the rest of the validate() method to run
                MockPydanticClass.return_value.model_dump.return_value = MOCK_DUMP
                
                # 2. Run validation (the call to ConfigValidation(...) now returns the mock instance)
                Config.validate()

            # 3. Assert that the setter loop (for key, value in ...) successfully ran
            assert Config.TEMPERATURE == 0.5
            assert Config.MAX_TOKENS == 2000
            assert Config.PROMETHEUS_PORT == 9000
            assert Config.MAX_CONTEXT_MSGS == 15

        finally:
            # 4. Clean up: Restore original values
            Config.TEMPERATURE = original_temp
            Config.MAX_TOKENS = original_max
            Config.PROMETHEUS_PORT = original_port
            Config.MAX_CONTEXT_MSGS = original_max_context
            Config.validate() # Re-validate to ensure clean state
    # --- END NEW TEST ---

    def test_validate_invalid_temperature(self):
        """Test validation catches invalid temperature"""
        original_temp = Config.TEMPERATURE

        try:
            Config.TEMPERATURE = 5.0  # Invalid
            with pytest.raises(ValueError, match="Invalid configuration"):
                Config.validate()
        finally:
            Config.TEMPERATURE = original_temp

    def test_config_attributes(self):
        """Test config has expected attributes"""
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
        """Test logger creation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging("test_agent", tmpdir)

            assert logger.name == "test_agent"
            assert logger.level == logging.INFO
            
            # Ensure handlers are removed for clean state
            for h in list(logger.handlers):
                logger.removeHandler(h)
                h.close()

    def test_setup_logging_creates_directory(self):
        """Test log directory creation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "new_logs"
            logger = setup_logging("test_agent", str(log_dir))

            assert log_dir.exists()
            
            # Ensure handlers are removed for clean state
            for h in list(logger.handlers):
                logger.removeHandler(h)
                h.close()

    def test_setup_logging_file_handler(self):
        """Test file handler creation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging("test_agent", tmpdir)
            try:
                # Should have at least one file handler
                file_handlers = [h for h in logger.handlers if hasattr(h, "baseFilename")]
                assert len(file_handlers) > 0
            finally:
                 # Ensure handlers are removed for clean state
                for h in list(logger.handlers):
                    logger.removeHandler(h)
                    h.close()

    def test_setup_logging_removes_existing_handlers(self):
        """Test that existing handlers are removed"""
        
        # We must create and remove handlers from the same logger instance for the test to work
        # We use a shared unique logger name
        logger_name = "test_handler_removal"
        logger = logging.getLogger(logger_name)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Setup once (adds 2 handlers: File, Console)
            setup_logging(logger_name, tmpdir)
            handler_count1 = len(logger.handlers)
            
            # 2. Setup again (removes old 2, adds 2 new)
            setup_logging(logger_name, tmpdir)
            handler_count2 = len(logger.handlers)

        # Should have the same number (old ones removed before new ones added)
        assert handler_count1 == handler_count2
        
        # Final cleanup for the test logger
        for h in list(logger.handlers):
            logger.removeHandler(h)
            h.close()


class TestLogEvent:
    """Test event logging"""

    def test_log_event_format(self):
        """Test log event creates proper JSON"""
        logger = logging.getLogger("test")
        handler = MagicMock()
        handler.level = logging.DEBUG  # Mock handlers need a numeric level attribute
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        try:
            log_event(logger, "test_event", {"key": "value", "number": 42})
            # Should have been called
            assert handler.handle.called
        finally:
            logger.removeHandler(handler) # Ensure cleanup

    def test_log_event_includes_timestamp(self):
        """Test log event includes timestamp"""
        logger = logging.getLogger("test_json")
        logger.setLevel(logging.INFO)

        # Capture log output
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False) as f:
            handler = logging.FileHandler(f.name)
            logger.addHandler(handler)

            try:
                log_event(logger, "test_event", {"data": "test"})
            finally:
                handler.close()
                logger.removeHandler(handler)

            # Read log
            with open(f.name, "r") as log_file:
                log_line = log_file.read()
                log_data = json.loads(log_line)

            assert "timestamp" in log_data
            assert log_data["event"] == "test_event"
            assert log_data["data"] == "test"

            # Cleanup
            Path(f.name).unlink()


class TestSimpleSimilarity:
    """Test similarity calculation"""

    def test_identical_strings(self):
        """Test identical strings have high similarity"""
        sim = simple_similarity("hello world", "hello world")
        assert sim == 1.0

    def test_completely_different(self):
        """Test completely different strings have low similarity"""
        sim = simple_similarity("hello world", "goodbye universe")
        # FIX: Make check less brittle
        assert sim < 0.5 

    def test_partial_overlap(self):
        """Test partial overlap"""
        # Test with strings that have clear word overlap
        sim = simple_similarity("hello world", "hello there")
        # Should have some similarity (both have "hello")
        assert 0.0 <= sim <= 1.0
        # Should not be identical
        assert sim != 1.0

    def test_case_insensitive(self):
        """Test case insensitivity"""
        sim1 = simple_similarity("Hello World", "hello world")
        sim2 = simple_similarity("hello world", "hello world")
        assert sim1 == sim2

    def test_empty_strings(self):
        """Test empty strings"""
        sim = simple_similarity("", "")
        # Two empty strings are identical, so similarity should be 1.0
        assert sim == 1.0

    def test_one_empty_string(self):
        """Test one empty string"""
        sim = simple_similarity("hello", "")
        assert sim == 0.0

    def test_short_strings(self):
        """Test strings shorter than shingle size"""
        sim = simple_similarity("hi", "hi")
        assert sim == 1.0


class TestHashMessage:
    """Test message hashing"""

    def test_hash_message_consistent(self):
        """Test same content produces same hash"""
        hash1 = hash_message("test content")
        hash2 = hash_message("test content")
        assert hash1 == hash2

    def test_hash_message_different(self):
        """Test different content produces different hash"""
        hash1 = hash_message("content 1")
        hash2 = hash_message("content 2")
        assert hash1 != hash2

    def test_hash_message_length(self):
        """Test hash length"""
        hash_val = hash_message("test")
        assert len(hash_val) == 8  # First 8 chars of MD5


class TestAddJitter:
    """Test jitter function"""

    def test_add_jitter_range(self):
        """Test jitter stays within range"""
        for _ in range(100):
            jittered = add_jitter(10.0, jitter_range=0.2)
            assert 8.0 <= jittered <= 12.0

    def test_add_jitter_minimum(self):
        """Test jitter has minimum value"""
        jittered = add_jitter(0.01, jitter_range=0.5)
        assert jittered >= 0.1

    def test_add_jitter_custom_range(self):
        """Test custom jitter range"""
        for _ in range(50):
            jittered = add_jitter(10.0, jitter_range=0.5)
            assert 5.0 <= jittered <= 15.0
    
    # --- NEW TEST: zero jitter branch (no randomness path) ---
    def test_add_jitter_zero_range(self):
        """With zero jitter, value should be returned unchanged (no clamp needed)."""
        assert add_jitter(10.0, jitter_range=0.0) == 10.0
    # --- END NEW TEST ---


class TestMaskApiKey:
    """Test API key masking"""

    def test_mask_anthropic_key(self):
        """Test masking Anthropic keys"""
        text = "My key is sk-ant-1234567890123456789012345"
        masked = mask_api_key(text)
        assert "[ANTHROPIC_KEY]" in masked
        assert "sk-ant-" not in masked

    def test_mask_openai_key(self):
        """Test masking OpenAI keys"""
        text = "My key is sk-123456789012345678901234567890"
        masked = mask_api_key(text)
        assert "[OPENAI_KEY]" in masked or "[API_KEY]" in masked
        assert "sk-123456789012345678901234567890" not in masked

    def test_mask_perplexity_key(self):
        """Test masking Perplexity keys"""
        text = "My key is pplx-123456789012345678901234567890"
        masked = mask_api_key(text)
        assert "[PERPLEXITY_KEY]" in masked
        assert "pplx-" not in masked

    def test_mask_generic_key(self):
        """Test masking generic long keys"""
        text = "My key is abcdefghijklmnopqrstuvwxyz1234567890"
        masked = mask_api_key(text)
        assert "[API_KEY]" in masked

    def test_mask_multiple_keys(self):
        """Test masking multiple keys"""
        text = "Key1: sk-ant-12345678901234567890 Key2: sk-9876543210987654321098765"
        masked = mask_api_key(text)
        assert masked.count("[") >= 2  # At least 2 masked sections

    def test_mask_no_keys(self):
        """Test text without keys"""
        text = "This is normal text without keys"
        masked = mask_api_key(text)
        assert masked == text


class TestSanitizeContent:
    """Test content sanitization"""

    def test_sanitize_script_tags(self):
        """Test removing script tags"""
        content = "<div><script>alert('xss')</script>Safe content</div>"
        sanitized = sanitize_content(content)
        assert "[FILTERED]" in sanitized
        assert "alert" not in sanitized

    def test_sanitize_javascript(self):
        """Test removing javascript:"""
        content = '<a href="javascript:alert()">Click</a>'
        sanitized = sanitize_content(content)
        assert "[FILTERED]" in sanitized

    def test_sanitize_event_handlers(self):
        """Test removing event handlers"""
        content = '<div onclick="doEvil()">Click me</div>'
        sanitized = sanitize_content(content)
        assert "[FILTERED]" in sanitized

    def test_sanitize_sql_injection(self):
        """Test removing SQL patterns"""
        content = "SELECT * FROM users; DROP TABLE users;"
        sanitized = sanitize_content(content)
        assert "[FILTERED]" in sanitized

    def test_sanitize_safe_content(self):
        """Test safe content unchanged"""
        content = "This is safe content with no dangerous patterns"
        sanitized = sanitize_content(content)
        assert sanitized == content

    def test_sanitize_case_insensitive(self):
        """Test case-insensitive matching"""
        content = "<SCRIPT>alert()</SCRIPT>"
        sanitized = sanitize_content(content)
        assert "[FILTERED]" in sanitized


class TestMetricsRecording:
    """Test metrics recording functions"""

    def test_record_call_success(self):
        """Test recording successful API call"""
        # Should not raise
        record_call("TestProvider", "test-model", "success")

    def test_record_call_error(self):
        """Test recording failed API call"""
        # Should not raise
        record_call("TestProvider", "test-model", "error")

    def test_record_latency(self):
        """Test recording latency"""
        # Should not raise
        record_latency("TestProvider", "test-model", 1.5)

    def test_record_tokens(self):
        """Test recording token usage"""
        # Should not raise
        record_tokens("TestProvider", "test-model", 100, 50)

    def test_record_error(self):
        """Test recording errors"""
        # Should not raise
        record_error("TestProvider", "timeout")
        record_error("TestProvider", "api_error")

    def test_increment_conversations(self):
        """Test incrementing conversation counter"""
        # Should not raise
        increment_conversations()

    def test_decrement_conversations(self):
        """Test decrementing conversation counter"""
        # Should not raise
        decrement_conversations()

    def test_metrics_with_special_characters(self):
        """Test metrics with special characters in labels"""
        # Should handle gracefully
        record_call("Test-Provider", "model/v1", "success")
        record_error("Test Provider", "rate_limit")


class TestMetricsServer:
    """Test metrics server startup"""

    def test_start_metrics_server_default_port(self):
        """Test starting server with default port"""
        with patch("core.metrics.start_http_server") as mock_start:
            start_metrics_server()
            mock_start.assert_called_once()

    def test_start_metrics_server_custom_port(self):
        """Test starting server with custom port"""
        with patch("core.metrics.start_http_server") as mock_start:
            start_metrics_server(9999)
            mock_start.assert_called_once_with(9999)

    def test_start_metrics_server_error_handling(self):
        """Test server handles errors gracefully"""
        with patch("core.metrics.start_http_server", side_effect=OSError("Port in use")):
            # Should not raise
            start_metrics_server(8000)

    def test_start_metrics_server_from_env(self):
        """Test reading port from environment"""
        with patch.dict(os.environ, {"PROMETHEUS_PORT": "9090"}):
            with patch("core.metrics.start_http_server") as mock_start:
                start_metrics_server(None)
                mock_start.assert_called_once_with(9090)


class TestMetricsErrorHandling:
    """Test metrics error handling"""

    def test_record_call_with_exception(self):
        """Test record_call handles exceptions"""
        with patch("core.metrics.API_CALLS.labels", side_effect=Exception("Metric error")):
            # Should not raise
            record_call("Test", "model", "success")

    def test_record_latency_with_exception(self):
        """Test record_latency handles exceptions"""
        with patch("core.metrics.RESPONSE_LATENCY.labels", side_effect=Exception("Metric error")):
            # Should not raise
            record_latency("Test", "model", 1.0)

    def test_record_tokens_with_exception(self):
        """Test record_tokens handles exceptions"""
        with patch("core.metrics.TOKEN_USAGE.labels", side_effect=Exception("Metric error")):
            # Should not raise
            record_tokens("Test", "model", 10, 20)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
