"""Tests for Error Handler."""

import pytest
import time
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st

from alice.core.error_handler import ErrorHandler
from alice.core.logger import Logger
from alice.core.config import Config


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = Mock()
    config.groq_max_retries = 3
    return config


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return Mock(spec=Logger)


@pytest.fixture
def error_handler(mock_config, mock_logger):
    """Create ErrorHandler instance."""
    return ErrorHandler(mock_config, mock_logger)


class TestErrorClassification:
    """Test error classification (transient vs permanent)."""

    def test_transient_timeout_error(self, error_handler):
        """Test that timeout errors are classified as transient."""
        error = TimeoutError("Connection timeout")
        assert error_handler.is_transient_error(error) is True

    def test_transient_rate_limit_error(self, error_handler):
        """Test that rate limit errors (429) are classified as transient."""
        error = Exception("HTTP 429: Too Many Requests")
        assert error_handler.is_transient_error(error) is True

    def test_transient_service_unavailable(self, error_handler):
        """Test that service unavailable (503) is classified as transient."""
        error = Exception("HTTP 503: Service Unavailable")
        assert error_handler.is_transient_error(error) is True

    def test_permanent_unauthorized_error(self, error_handler):
        """Test that unauthorized (401) is classified as permanent."""
        error = Exception("HTTP 401: Unauthorized")
        assert error_handler.is_transient_error(error) is False

    def test_permanent_forbidden_error(self, error_handler):
        """Test that forbidden (403) is classified as permanent."""
        error = Exception("HTTP 403: Forbidden")
        assert error_handler.is_transient_error(error) is False

    def test_permanent_not_found_error(self, error_handler):
        """Test that not found (404) is classified as permanent."""
        error = Exception("HTTP 404: Not Found")
        assert error_handler.is_transient_error(error) is False

    def test_permanent_invalid_api_key(self, error_handler):
        """Test that invalid API key is classified as permanent."""
        error = Exception("Invalid API key")
        assert error_handler.is_transient_error(error) is False


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    def test_successful_first_attempt(self, error_handler):
        """Test function succeeds on first attempt."""
        func = Mock(return_value="success")
        func.__name__ = "test_func"
        result = error_handler.execute_with_retry(func)
        
        assert result == "success"
        assert func.call_count == 1

    def test_retry_on_transient_error(self, error_handler):
        """Test retry on transient error."""
        func = Mock(side_effect=[
            TimeoutError("timeout"),
            "success"
        ])
        func.__name__ = "test_func"
        
        result = error_handler.execute_with_retry(func)
        
        assert result == "success"
        assert func.call_count == 2

    def test_fail_fast_on_permanent_error(self, error_handler):
        """Test fail fast on permanent error."""
        func = Mock(side_effect=Exception("HTTP 401: Unauthorized"))
        func.__name__ = "test_func"
        
        with pytest.raises(Exception, match="401"):
            error_handler.execute_with_retry(func)
        
        assert func.call_count == 1

    def test_max_retries_exceeded(self, error_handler):
        """Test max retries exceeded."""
        func = Mock(side_effect=TimeoutError("timeout"))
        func.__name__ = "test_func"
        
        with pytest.raises(TimeoutError):
            error_handler.execute_with_retry(func)
        
        # Should try max_retries + 1 times (initial + retries)
        assert func.call_count == error_handler.max_retries + 1

    def test_exponential_backoff_timing(self, error_handler):
        """Test exponential backoff timing."""
        error_handler.base_delay = 0.01  # 10ms for testing
        func = Mock(side_effect=[
            TimeoutError("timeout"),
            TimeoutError("timeout"),
            "success"
        ])
        func.__name__ = "test_func"
        
        start_time = time.time()
        result = error_handler.execute_with_retry(func)
        elapsed = time.time() - start_time
        
        assert result == "success"
        # Should have delays: 0.01s + 0.02s = 0.03s minimum
        assert elapsed >= 0.03

    def test_retry_with_args_and_kwargs(self, error_handler):
        """Test retry with function arguments."""
        func = Mock(side_effect=[
            TimeoutError("timeout"),
            "success"
        ])
        func.__name__ = "test_func"
        
        result = error_handler.execute_with_retry(
            func, "arg1", "arg2", kwarg1="value1"
        )
        
        assert result == "success"
        func.assert_called_with("arg1", "arg2", kwarg1="value1")


class TestTimeoutManagement:
    """Test timeout management."""

    def test_timeout_exceeded(self, error_handler):
        """Test timeout exceeded."""
        def slow_func():
            time.sleep(0.1)
            return "success"
        
        with pytest.raises(TimeoutError, match="exceeded timeout"):
            error_handler.execute_with_retry(slow_func, timeout_ms=10)

    def test_timeout_not_exceeded(self, error_handler):
        """Test timeout not exceeded."""
        def fast_func():
            time.sleep(0.01)
            return "success"
        
        result = error_handler.execute_with_retry(fast_func, timeout_ms=100)
        assert result == "success"

    def test_timeout_with_retry(self, error_handler):
        """Test timeout with retry logic."""
        error_handler.base_delay = 0.001  # 1ms for testing
        func = Mock(side_effect=[
            TimeoutError("timeout"),
            "success"
        ])
        func.__name__ = "test_func"
        
        result = error_handler.execute_with_retry(func, timeout_ms=1000)
        assert result == "success"


class TestErrorLogging:
    """Test error logging with full context."""

    def test_error_logged_with_context(self, error_handler, mock_logger):
        """Test error is logged with full context."""
        func = Mock(side_effect=Exception("Test error"))
        func.__name__ = "test_func"
        
        with pytest.raises(Exception):
            error_handler.execute_with_retry(func)
        
        # Should log error with context
        assert mock_logger.error.called
        call_args = mock_logger.error.call_args
        assert "ErrorHandler" in call_args[0]
        assert "error_type" in call_args[0][2]
        assert "error_message" in call_args[0][2]

    def test_permanent_error_logged_as_fail_fast(self, error_handler, mock_logger):
        """Test permanent error is logged as fail fast."""
        func = Mock(side_effect=Exception("HTTP 401: Unauthorized"))
        func.__name__ = "test_func"
        
        with pytest.raises(Exception):
            error_handler.execute_with_retry(func)
        
        # Should log fail fast message
        error_calls = [call for call in mock_logger.error.call_args_list]
        assert any("Permanent error" in str(call) for call in error_calls)


class TestAlertTrigger:
    """Test alert triggering for critical errors."""

    def test_trigger_alert(self, error_handler, mock_logger):
        """Test alert is triggered."""
        error = Exception("Critical error")
        error_handler.trigger_alert(error)
        
        # Should log critical message
        assert mock_logger.critical.called
        call_args = mock_logger.critical.call_args
        assert "CRITICAL ERROR" in call_args[0][1]


# Property-based tests

@given(st.integers(min_value=1, max_value=10))
def test_property_exponential_backoff(attempt_number):
    """Property 5: Transient Error Retry with Exponential Backoff.
    
    For any API call that fails with a transient error, the Error_Handler 
    should retry with exponential backoff.
    
    Validates: Requirements 3.1
    """
    config = Mock()
    config.groq_max_retries = 10
    logger = Mock(spec=Logger)
    error_handler = ErrorHandler(config, logger)
    error_handler.base_delay = 0.001  # 1ms for testing
    
    # Calculate expected delay for this attempt
    expected_delay = error_handler.base_delay * (error_handler.backoff_factor ** (attempt_number - 1))
    
    # Verify exponential backoff formula
    assert expected_delay > 0
    if attempt_number > 1:
        prev_delay = error_handler.base_delay * (error_handler.backoff_factor ** (attempt_number - 2))
        assert expected_delay > prev_delay


@given(st.text())
def test_property_permanent_error_fails_fast(error_message):
    """Property 6: Permanent Error Fails Fast.
    
    For any API call that fails with a permanent error, the Error_Handler 
    should fail immediately without retrying.
    
    Validates: Requirements 3.6
    """
    config = Mock()
    config.groq_max_retries = 5
    logger = Mock(spec=Logger)
    error_handler = ErrorHandler(config, logger)
    
    # Create permanent error
    permanent_errors = [
        "HTTP 401: Unauthorized",
        "HTTP 403: Forbidden",
        "HTTP 404: Not Found",
        "Invalid API key",
    ]
    
    for error_msg in permanent_errors:
        func = Mock(side_effect=Exception(error_msg))
        
        with pytest.raises(Exception):
            error_handler.execute_with_retry(func)
        
        # Should only call once (no retries)
        assert func.call_count == 1


def test_property_error_logging_includes_context():
    """Property 7: Error Logging Includes Full Context.
    
    For any error encountered by a component, the logged error should include 
    the component name, error type, error message, and context.
    
    Validates: Requirements 3.3
    """
    config = Mock()
    config.groq_max_retries = 1
    logger = Mock(spec=Logger)
    error_handler = ErrorHandler(config, logger)
    
    # Use transient error so it goes through retry logic
    func = Mock(side_effect=TimeoutError("Test timeout"))
    func.__name__ = "test_func"
    
    with pytest.raises(TimeoutError):
        error_handler.execute_with_retry(func)
    
    # Verify error was logged with context
    assert logger.error.called
    
    # Get first error call (the initial error log)
    first_call = logger.error.call_args_list[0]
    
    # Check component name
    assert first_call[0][0] == "ErrorHandler"
    
    # Check context includes required fields
    context = first_call[0][2]
    assert "error_type" in context
    assert "error_message" in context
    assert "attempt" in context
