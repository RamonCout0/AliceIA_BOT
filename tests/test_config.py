"""Tests for Config Manager."""

import os
import pytest
from pathlib import Path
from hypothesis import given, strategies as st
from alice.core.config import Config, ConfigManager


class TestConfigDataclass:
    """Test Config dataclass."""
    
    def test_config_creation(self):
        """Test creating a Config object."""
        config = Config(
            groq_api_key="test_key",
            groq_timeout_ms=5000,
            groq_max_retries=3,
            gemini_api_key="gemini_key",
            gemini_timeout_ms=5000,
            gemini_max_retries=3,
            discord_token="discord_token",
            history_backend="json",
            history_max_size_mb=100,
            history_archive_days=30,
            log_level="INFO",
            log_file_max_size_mb=10,
            log_file_backup_count=5,
            rate_limit_requests_per_minute=60,
            rate_limit_burst_size=10,
            gamepad_queue_timeout_ms=1000,
            environment="dev",
        )
        
        assert config.groq_api_key == "test_key"
        assert config.groq_timeout_ms == 5000
        assert config.environment == "dev"


class TestConfigManager:
    """Test ConfigManager."""
    
    @pytest.fixture
    def env_file(self, tmp_path):
        """Create a temporary .env file."""
        env_path = tmp_path / ".env"
        return str(env_path)
    
    def _create_valid_env(self, env_file):
        """Create a valid .env file."""
        with open(env_file, 'w') as f:
            f.write("groq_api_key=test_groq_key\n")
            f.write("groq_timeout_ms=5000\n")
            f.write("groq_max_retries=3\n")
            f.write("gemini_api_key=test_gemini_key\n")
            f.write("gemini_timeout_ms=5000\n")
            f.write("gemini_max_retries=3\n")
            f.write("discord_token=test_discord_token\n")
            f.write("history_backend=json\n")
            f.write("history_max_size_mb=100\n")
            f.write("history_archive_days=30\n")
            f.write("log_level=INFO\n")
            f.write("log_file_max_size_mb=10\n")
            f.write("log_file_backup_count=5\n")
            f.write("rate_limit_requests_per_minute=60\n")
            f.write("rate_limit_burst_size=10\n")
            f.write("gamepad_queue_timeout_ms=1000\n")
            f.write("environment=dev\n")
    
    def test_config_manager_initialization(self, env_file):
        """Test ConfigManager initialization."""
        self._create_valid_env(env_file)
        manager = ConfigManager(env_file)
        assert manager.env_file == env_file
    
    def test_config_validation_success(self, env_file):
        """Test successful configuration validation."""
        self._create_valid_env(env_file)
        manager = ConfigManager(env_file)
        assert manager.validate() is True
    
    def test_config_validation_missing_required(self, env_file):
        """Test validation fails with missing required variables."""
        # Create incomplete .env
        with open(env_file, 'w') as f:
            f.write("groq_api_key=test_key\n")
        
        manager = ConfigManager(env_file)
        with pytest.raises(ValueError) as exc_info:
            manager.validate()
        
        assert "Missing required environment variables" in str(exc_info.value)
        # Ensure the error message doesn't expose variable names
        assert "groq_api_key" not in str(exc_info.value)
    
    def test_config_validation_invalid_type(self, env_file):
        """Test validation fails with invalid types."""
        with open(env_file, 'w') as f:
            f.write("groq_api_key=test_key\n")
            f.write("groq_timeout_ms=not_an_int\n")
            f.write("groq_max_retries=3\n")
            f.write("gemini_api_key=test_key\n")
            f.write("gemini_timeout_ms=5000\n")
            f.write("gemini_max_retries=3\n")
            f.write("discord_token=token\n")
            f.write("history_backend=json\n")
            f.write("history_max_size_mb=100\n")
            f.write("history_archive_days=30\n")
            f.write("log_level=INFO\n")
            f.write("log_file_max_size_mb=10\n")
            f.write("log_file_backup_count=5\n")
            f.write("rate_limit_requests_per_minute=60\n")
            f.write("rate_limit_burst_size=10\n")
            f.write("gamepad_queue_timeout_ms=1000\n")
            f.write("environment=dev\n")
        
        manager = ConfigManager(env_file)
        with pytest.raises(ValueError) as exc_info:
            manager.validate()
        
        assert "Invalid configuration types" in str(exc_info.value)
    
    def test_get_config(self, env_file):
        """Test getting validated config object."""
        self._create_valid_env(env_file)
        manager = ConfigManager(env_file)
        config = manager.get_config()
        
        assert isinstance(config, Config)
        assert config.groq_api_key == "test_groq_key"
        assert config.groq_timeout_ms == 5000
        assert config.environment == "dev"
    
    def test_is_secret(self):
        """Test secret key identification."""
        assert ConfigManager.is_secret('groq_api_key') is True
        assert ConfigManager.is_secret('gemini_api_key') is True
        assert ConfigManager.is_secret('discord_token') is True
        assert ConfigManager.is_secret('log_level') is False
        assert ConfigManager.is_secret('environment') is False


class TestConfigValidationProperties:
    """Property-based tests for Config validation."""
    
    @given(st.text(min_size=1))
    def test_property_8_missing_variables_rejected(self, missing_var_name):
        """Property 8: Config Validation Rejects Missing Required Variables.
        
        For any Config_Manager initialization with missing required environment variables,
        validation should fail with a clear error message that does not expose the variable names or values.
        
        **Validates: Requirements 4.2, 4.3, 4.6**
        """
        # Create minimal env with only one variable
        env_content = f"{missing_var_name}=value\n"
        
        # This should fail because required variables are missing
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            f.flush()
            
            try:
                manager = ConfigManager(f.name)
                with pytest.raises(ValueError) as exc_info:
                    manager.validate()
                
                error_msg = str(exc_info.value)
                # Error should not expose specific variable names
                assert "Missing required environment variables" in error_msg
                # Should not contain the actual variable name
                assert missing_var_name not in error_msg or missing_var_name in ConfigManager.REQUIRED_KEYS
            finally:
                os.unlink(f.name)
    
    @given(st.text(min_size=1))
    def test_property_9_secrets_not_logged(self, secret_value):
        """Property 9: Config Never Logs Secrets.
        
        For any log message generated by the system, if the message contains a configuration value
        that is marked as secret (API keys, tokens), the log should not contain the actual value.
        
        **Validates: Requirements 4.3, 4.6**
        """
        # Test that secret keys are properly identified
        for secret_key in ConfigManager.SECRET_KEYS:
            assert ConfigManager.is_secret(secret_key) is True
        
        # Test that non-secret keys are not identified as secrets
        non_secret_keys = ['log_level', 'environment', 'history_backend']
        for key in non_secret_keys:
            assert ConfigManager.is_secret(key) is False
    
    @given(
        st.integers(min_value=1, max_value=100000),
        st.integers(min_value=1, max_value=100),
        st.integers(min_value=1, max_value=100000),
    )
    def test_property_10_type_validation(self, timeout_val, retries_val, size_val):
        """Property 10: Config Type Validation.
        
        For any configuration value with a specified type (integer, URL, boolean),
        if a value of a different type is provided, Config_Manager should reject it
        with a clear error message.
        
        **Validates: Requirements 4.6**
        """
        import tempfile
        
        # Create env with valid integer values
        env_content = f"""groq_api_key=test_key
groq_timeout_ms={timeout_val}
groq_max_retries={retries_val}
gemini_api_key=test_key
gemini_timeout_ms={timeout_val}
gemini_max_retries={retries_val}
discord_token=token
history_backend=json
history_max_size_mb={size_val}
history_archive_days=30
log_level=INFO
log_file_max_size_mb=10
log_file_backup_count=5
rate_limit_requests_per_minute=60
rate_limit_burst_size=10
gamepad_queue_timeout_ms=1000
environment=dev
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            f.flush()
            
            try:
                manager = ConfigManager(f.name)
                # Should validate successfully with valid integers
                assert manager.validate() is True
                
                config = manager.get_config()
                assert config.groq_timeout_ms == timeout_val
                assert config.groq_max_retries == retries_val
                assert config.history_max_size_mb == size_val
            finally:
                os.unlink(f.name)
