"""Tests for Alice System."""

import pytest
from unittest.mock import Mock, patch

from alice.alice_system import AliceSystem


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a mock .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text("""
GROQ_API_KEY=test_groq_key
GEMINI_API_KEY=test_gemini_key
DISCORD_TOKEN=test_discord_token
GROQ_TIMEOUT_MS=30000
GROQ_MAX_RETRIES=3
GEMINI_TIMEOUT_MS=30000
GEMINI_MAX_RETRIES=3
HISTORY_BACKEND=json
HISTORY_MAX_SIZE_MB=100
HISTORY_ARCHIVE_DAYS=30
LOG_LEVEL=INFO
LOG_FILE_MAX_SIZE_MB=10
LOG_FILE_BACKUP_COUNT=5
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST_SIZE=10
GAMEPAD_QUEUE_TIMEOUT_MS=5000
ENVIRONMENT=dev
""")
    return str(env_file)


class TestAliceSystemInitialization:
    """Test Alice System initialization."""

    def test_initialize_with_config(self, mock_config_file):
        """Test initializing Alice System with config."""
        system = AliceSystem(mock_config_file)
        
        assert system.config is not None
        assert system.running is False


class TestAliceSystemStartup:
    """Test Alice System startup."""

    def test_start_system(self, mock_config_file):
        """Test starting Alice System."""
        system = AliceSystem(mock_config_file)
        system.start()
        
        assert system.running is True
        assert system.logger is not None
        assert system.error_handler is not None
        assert system.schema_validator is not None
        assert system.history_manager is not None
        assert system.rate_limiter is not None
        assert system.gamepad_controller is not None
        assert system.macro_system is not None
        assert system.vision_engine is not None
        assert system.discord_bot is not None
        
        system.stop()

    def test_component_initialization_order(self, mock_config_file):
        """Test that components are initialized in correct order."""
        system = AliceSystem(mock_config_file)
        system.start()
        
        # Verify all components are initialized
        assert system.logger is not None
        assert system.error_handler is not None
        assert system.schema_validator is not None
        assert system.history_manager is not None
        assert system.rate_limiter is not None
        assert system.gamepad_controller is not None
        assert system.macro_system is not None
        assert system.vision_engine is not None
        assert system.discord_bot is not None
        
        system.stop()


class TestAliceSystemShutdown:
    """Test Alice System shutdown."""

    def test_stop_system(self, mock_config_file):
        """Test stopping Alice System."""
        system = AliceSystem(mock_config_file)
        system.start()
        
        assert system.running is True
        
        system.stop()
        
        assert system.running is False

    def test_graceful_shutdown(self, mock_config_file):
        """Test graceful shutdown."""
        system = AliceSystem(mock_config_file)
        system.start()
        
        # Should not raise any exceptions
        system.stop()


class TestAliceSystemStatus:
    """Test Alice System status."""

    def test_is_running(self, mock_config_file):
        """Test is_running method."""
        system = AliceSystem(mock_config_file)
        
        assert system.is_running() is False
        
        system.start()
        assert system.is_running() is True
        
        system.stop()
        assert system.is_running() is False

    def test_get_status(self, mock_config_file):
        """Test get_status method."""
        system = AliceSystem(mock_config_file)
        system.start()
        
        status = system.get_status()
        
        assert "running" in status
        assert "vision_engine" in status
        assert "discord_bot" in status
        assert "gamepad_controller" in status
        assert "rate_limiter" in status
        
        system.stop()


class TestAliceSystemDependencyInjection:
    """Test dependency injection."""

    def test_components_receive_dependencies(self, mock_config_file):
        """Test that components receive their dependencies."""
        system = AliceSystem(mock_config_file)
        system.start()
        
        # Verify Vision Engine has dependencies
        assert system.vision_engine.config is not None
        assert system.vision_engine.logger is not None
        assert system.vision_engine.error_handler is not None
        assert system.vision_engine.schema_validator is not None
        
        # Verify Discord Bot has dependencies
        assert system.discord_bot.config is not None
        assert system.discord_bot.logger is not None
        assert system.discord_bot.error_handler is not None
        assert system.discord_bot.schema_validator is not None
        assert system.discord_bot.history_manager is not None
        
        system.stop()


class TestAliceSystemNoDependencies:
    """Test system without external dependencies."""

    def test_system_works_without_external_apis(self, mock_config_file):
        """Test that system can start without external API access."""
        system = AliceSystem(mock_config_file)
        
        # Should not require external API calls to start
        system.start()
        
        assert system.running is True
        
        system.stop()
