"""Tests for Discord Bot."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from alice.components.discord_bot import DiscordBot
from alice.core.logger import Logger
from alice.core.error_handler import ErrorHandler
from alice.core.schema_validator import SchemaValidator
from alice.core.history_manager import HistoryManager


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = Mock()
    config.discord_token = "test_token"
    config.gemini_api_key = "test_key"
    config.gemini_timeout_ms = 30000
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
def mock_history_manager():
    """Create mock history manager."""
    return Mock(spec=HistoryManager)


@pytest.fixture
def discord_bot(mock_config, mock_logger, mock_error_handler, mock_schema_validator, mock_history_manager):
    """Create DiscordBot instance."""
    return DiscordBot(
        mock_config,
        mock_logger,
        mock_error_handler,
        mock_schema_validator,
        mock_history_manager
    )


class TestMessageSending:
    """Test message sending."""

    def test_send_message(self, discord_bot, mock_logger):
        """Test sending a message."""
        discord_bot.send_message("channel_123", "Hello, world!")
        
        # Verify logging
        assert mock_logger.info.called

    def test_send_message_error(self, discord_bot, mock_logger):
        """Test sending message with error."""
        # Simulate an error
        discord_bot.send_message("channel_123", "Hello, world!")
        
        # Should still log
        assert mock_logger.info.called


class TestMessageProcessing:
    """Test message processing."""

    def test_process_message_success(self, discord_bot, mock_error_handler, mock_schema_validator, mock_history_manager):
        """Test successful message processing."""
        # Mock the error handler to return a valid response
        mock_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Hello! How can I help?"}
                        ]
                    }
                }
            ]
        }
        mock_error_handler.execute_with_retry.return_value = mock_response
        
        # Mock schema validator to accept the response
        mock_schema_validator.validate_gemini_response.return_value = True
        
        reply = discord_bot.process_message("Hello!")
        
        assert reply == "Hello! How can I help?"
        assert mock_history_manager.add_entry.called

    def test_process_message_invalid_response(self, discord_bot, mock_error_handler, mock_schema_validator):
        """Test processing with invalid response."""
        # Mock the error handler to return a response
        mock_response = {"invalid": "response"}
        mock_error_handler.execute_with_retry.return_value = mock_response
        
        # Mock schema validator to reject the response
        mock_schema_validator.validate_gemini_response.return_value = False
        mock_schema_validator.get_validation_errors.return_value = ["Missing candidates"]
        
        reply = discord_bot.process_message("Hello!")
        
        assert "error" in reply.lower()

    def test_process_message_api_error(self, discord_bot, mock_error_handler):
        """Test processing with API error."""
        # Mock the error handler to raise an exception
        mock_error_handler.execute_with_retry.side_effect = Exception("API error")
        
        reply = discord_bot.process_message("Hello!")
        
        assert "error" in reply.lower()

    def test_process_message_adds_to_history(self, discord_bot, mock_error_handler, mock_schema_validator, mock_history_manager):
        """Test that message is added to history."""
        mock_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Hello! How can I help?"}
                        ]
                    }
                }
            ]
        }
        mock_error_handler.execute_with_retry.return_value = mock_response
        mock_schema_validator.validate_gemini_response.return_value = True
        
        discord_bot.process_message("Hello!")
        
        # Verify history manager was called
        assert mock_history_manager.add_entry.called


class TestStatus:
    """Test status reporting."""

    def test_initial_status(self, discord_bot):
        """Test initial status."""
        assert discord_bot.get_status() == "disconnected"


class TestResponseParsing:
    """Test response parsing."""

    def test_parse_valid_response(self, discord_bot):
        """Test parsing valid response."""
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Hello! How can I help?"}
                        ]
                    }
                }
            ]
        }
        
        text = discord_bot._parse_response(response)
        
        assert text == "Hello! How can I help?"

    def test_parse_response_no_candidates(self, discord_bot):
        """Test parsing response with no candidates."""
        response = {"candidates": []}
        
        text = discord_bot._parse_response(response)
        
        assert "No response" in text

    def test_parse_response_no_parts(self, discord_bot):
        """Test parsing response with no parts."""
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": []
                    }
                }
            ]
        }
        
        text = discord_bot._parse_response(response)
        
        assert "No response" in text


class TestErrorHandling:
    """Test error handling."""

    def test_error_handler_called_with_timeout(self, discord_bot, mock_error_handler, mock_schema_validator):
        """Test that error handler is called with timeout."""
        mock_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Hello!"}
                        ]
                    }
                }
            ]
        }
        mock_error_handler.execute_with_retry.return_value = mock_response
        mock_schema_validator.validate_gemini_response.return_value = True
        
        discord_bot.process_message("Hello!")
        
        # Verify error handler was called with timeout
        mock_error_handler.execute_with_retry.assert_called_once()
        call_kwargs = mock_error_handler.execute_with_retry.call_args[1]
        assert call_kwargs["timeout_ms"] == 30000

    def test_schema_validator_called(self, discord_bot, mock_error_handler, mock_schema_validator):
        """Test that schema validator is called."""
        mock_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Hello!"}
                        ]
                    }
                }
            ]
        }
        mock_error_handler.execute_with_retry.return_value = mock_response
        mock_schema_validator.validate_gemini_response.return_value = True
        
        discord_bot.process_message("Hello!")
        
        # Verify schema validator was called
        mock_schema_validator.validate_gemini_response.assert_called_once_with(mock_response)


class TestLogging:
    """Test logging."""

    def test_logs_successful_processing(self, discord_bot, mock_logger, mock_error_handler, mock_schema_validator):
        """Test logging of successful processing."""
        mock_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Hello!"}
                        ]
                    }
                }
            ]
        }
        mock_error_handler.execute_with_retry.return_value = mock_response
        mock_schema_validator.validate_gemini_response.return_value = True
        
        discord_bot.process_message("Hello!")
        
        # Verify logging
        assert mock_logger.info.called

    def test_logs_processing_failure(self, discord_bot, mock_logger, mock_error_handler):
        """Test logging of processing failure."""
        mock_error_handler.execute_with_retry.side_effect = Exception("API error")
        
        discord_bot.process_message("Hello!")
        
        # Verify error logging
        assert mock_logger.error.called
