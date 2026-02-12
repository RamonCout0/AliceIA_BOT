"""Shared test fixtures and configuration."""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_env_file(temp_dir):
    """Create a temporary .env file for testing."""
    env_file = temp_dir / ".env"
    env_file.write_text(
        "GROQ_API_KEY=test_key\n"
        "GEMINI_API_KEY=test_key\n"
        "DISCORD_TOKEN=test_token\n"
    )
    return env_file


@pytest.fixture
def mock_logger(mocker):
    """Create a mock logger for testing."""
    return mocker.MagicMock()


@pytest.fixture
def mock_config(mocker):
    """Create a mock config for testing."""
    config = mocker.MagicMock()
    config.groq_api_key = "test_key"
    config.gemini_api_key = "test_key"
    config.discord_token = "test_token"
    config.groq_timeout_ms = 30000
    config.gemini_timeout_ms = 30000
    config.groq_max_retries = 5
    config.gemini_max_retries = 5
    return config
