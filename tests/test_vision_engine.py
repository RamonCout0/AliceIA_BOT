"""Tests for Vision Engine."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from alice.components.vision_engine import VisionEngine, GameplayDecision
from alice.core.logger import Logger
from alice.core.error_handler import ErrorHandler
from alice.core.schema_validator import SchemaValidator


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = Mock()
    config.groq_api_key = "test_key"
    config.groq_timeout_ms = 30000
    return config


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return Mock(spec=Logger)


@pytest.fixture
def mock_error_handler():
    """Create mock error handler."""
    return Mock(spec=ErrorHandler)


@pytest.fixture
def mock_schema_validator():
    """Create mock schema validator."""
    return Mock(spec=SchemaValidator)


@pytest.fixture
def vision_engine(mock_config, mock_logger, mock_error_handler, mock_schema_validator):
    """Create VisionEngine instance."""
    return VisionEngine(
        mock_config,
        mock_logger,
        mock_error_handler,
        mock_schema_validator
    )


class TestGameplayDecision:
    """Test GameplayDecision dataclass."""

    def test_create_decision(self):
        """Test creating a gameplay decision."""
        decision = GameplayDecision(
            action="move_left",
            parameters={"distance": 10},
            confidence=0.9,
            reasoning="Player is moving left",
            timestamp=datetime.now()
        )
        
        assert decision.action == "move_left"
        assert decision.confidence == 0.9


class TestScreenshotAnalysis:
    """Test screenshot analysis."""

    def test_analyze_screenshot_success(self, vision_engine, mock_error_handler, mock_schema_validator):
        """Test successful screenshot analysis."""
        # Mock the error handler to return a valid response
        mock_response = {
            "choices": [{"message": {"content": "move_left"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model": "llama-2-vision"
        }
        mock_error_handler.execute_with_retry.return_value = mock_response
        
        # Mock schema validator to accept the response
        mock_schema_validator.validate_groq_response.return_value = True
        
        screenshot = b"fake_screenshot_data"
        decision = vision_engine.analyze_screenshot(screenshot)
        
        assert decision is not None
        assert decision.action == "move_left"

    def test_analyze_screenshot_invalid_response(self, vision_engine, mock_error_handler, mock_schema_validator):
        """Test analysis with invalid response."""
        # Mock the error handler to return a response
        mock_response = {
            "invalid": "response"
        }
        mock_error_handler.execute_with_retry.return_value = mock_response
        
        # Mock schema validator to reject the response
        mock_schema_validator.validate_groq_response.return_value = False
        mock_schema_validator.get_validation_errors.return_value = ["Missing choices field"]
        
        screenshot = b"fake_screenshot_data"
        decision = vision_engine.analyze_screenshot(screenshot)
        
        assert decision is None

    def test_analyze_screenshot_api_error(self, vision_engine, mock_error_handler):
        """Test analysis with API error."""
        # Mock the error handler to raise an exception
        mock_error_handler.execute_with_retry.side_effect = Exception("API error")
        
        screenshot = b"fake_screenshot_data"
        decision = vision_engine.analyze_screenshot(screenshot)
        
        assert decision is None
        assert vision_engine.get_status() == "error"


class TestStatus:
    """Test status reporting."""

    def test_initial_status(self, vision_engine):
        """Test initial status."""
        assert vision_engine.get_status() == "idle"

    def test_status_during_analysis(self, vision_engine, mock_error_handler, mock_schema_validator):
        """Test status during analysis."""
        mock_response = {
            "choices": [{"message": {"content": "move_left"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model": "llama-2-vision"
        }
        mock_error_handler.execute_with_retry.return_value = mock_response
        mock_schema_validator.validate_groq_response.return_value = True
        
        screenshot = b"fake_screenshot_data"
        vision_engine.analyze_screenshot(screenshot)
        
        # After analysis, should be back to idle
        assert vision_engine.get_status() == "idle"

    def test_status_on_error(self, vision_engine, mock_error_handler):
        """Test status on error."""
        mock_error_handler.execute_with_retry.side_effect = Exception("API error")
        
        screenshot = b"fake_screenshot_data"
        vision_engine.analyze_screenshot(screenshot)
        
        assert vision_engine.get_status() == "error"


class TestResponseParsing:
    """Test response parsing."""

    def test_parse_valid_response(self, vision_engine):
        """Test parsing valid response."""
        response = {
            "choices": [{"message": {"content": "move_left"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model": "llama-2-vision"
        }
        
        decision = vision_engine._parse_response(response)
        
        assert decision.action == "move_left"
        assert decision.confidence == 0.8

    def test_parse_response_with_parameters(self, vision_engine):
        """Test parsing response with parameters."""
        response = {
            "choices": [{"message": {"content": "move_left distance=10"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model": "llama-2-vision"
        }
        
        decision = vision_engine._parse_response(response)
        
        assert decision.action == "move_left"


class TestErrorHandling:
    """Test error handling."""

    def test_error_handler_called_with_timeout(self, vision_engine, mock_error_handler, mock_schema_validator):
        """Test that error handler is called with timeout."""
        mock_response = {
            "choices": [{"message": {"content": "move_left"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model": "llama-2-vision"
        }
        mock_error_handler.execute_with_retry.return_value = mock_response
        mock_schema_validator.validate_groq_response.return_value = True
        
        screenshot = b"fake_screenshot_data"
        vision_engine.analyze_screenshot(screenshot)
        
        # Verify error handler was called with timeout
        mock_error_handler.execute_with_retry.assert_called_once()
        call_kwargs = mock_error_handler.execute_with_retry.call_args[1]
        assert call_kwargs["timeout_ms"] == 30000

    def test_schema_validator_called(self, vision_engine, mock_error_handler, mock_schema_validator):
        """Test that schema validator is called."""
        mock_response = {
            "choices": [{"message": {"content": "move_left"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model": "llama-2-vision"
        }
        mock_error_handler.execute_with_retry.return_value = mock_response
        mock_schema_validator.validate_groq_response.return_value = True
        
        screenshot = b"fake_screenshot_data"
        vision_engine.analyze_screenshot(screenshot)
        
        # Verify schema validator was called
        mock_schema_validator.validate_groq_response.assert_called_once_with(mock_response)


class TestLogging:
    """Test logging."""

    def test_logs_successful_analysis(self, vision_engine, mock_logger, mock_error_handler, mock_schema_validator):
        """Test logging of successful analysis."""
        mock_response = {
            "choices": [{"message": {"content": "move_left"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model": "llama-2-vision"
        }
        mock_error_handler.execute_with_retry.return_value = mock_response
        mock_schema_validator.validate_groq_response.return_value = True
        
        screenshot = b"fake_screenshot_data"
        vision_engine.analyze_screenshot(screenshot)
        
        # Verify logging
        assert mock_logger.info.called

    def test_logs_analysis_failure(self, vision_engine, mock_logger, mock_error_handler):
        """Test logging of analysis failure."""
        mock_error_handler.execute_with_retry.side_effect = Exception("API error")
        
        screenshot = b"fake_screenshot_data"
        vision_engine.analyze_screenshot(screenshot)
        
        # Verify error logging
        assert mock_logger.error.called
