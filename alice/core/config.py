"""Configuration management with secure environment variable handling."""

import os
from dataclasses import dataclass
from typing import Any, Optional
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration dataclass with all configuration fields."""

    # Groq API settings
    groq_api_key: str
    groq_timeout_ms: int
    groq_max_retries: int

    # Gemini API settings
    gemini_api_key: str
    gemini_timeout_ms: int
    gemini_max_retries: int

    # Discord settings
    discord_token: str

    # History settings
    history_backend: str  # "json" or "sqlite"
    history_max_size_mb: int
    history_archive_days: int

    # Logging settings
    log_level: str  # "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    log_file_max_size_mb: int
    log_file_backup_count: int

    # Rate limiting settings
    rate_limit_requests_per_minute: int
    rate_limit_burst_size: int

    # Gamepad settings
    gamepad_queue_timeout_ms: int

    # Environment settings
    environment: str  # "dev", "staging", "production"


class ConfigManager:
    """Manages environment variables and configuration with validation."""

    # Secret keys that should never be logged
    SECRET_KEYS = {"groq_api_key", "gemini_api_key", "discord_token"}

    # Required environment variables
    REQUIRED_VARS = {
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "DISCORD_TOKEN",
    }

    # Type mappings for validation
    TYPE_MAPPINGS = {
        "GROQ_TIMEOUT_MS": int,
        "GROQ_MAX_RETRIES": int,
        "GEMINI_TIMEOUT_MS": int,
        "GEMINI_MAX_RETRIES": int,
        "HISTORY_MAX_SIZE_MB": int,
        "HISTORY_ARCHIVE_DAYS": int,
        "LOG_FILE_MAX_SIZE_MB": int,
        "LOG_FILE_BACKUP_COUNT": int,
        "RATE_LIMIT_REQUESTS_PER_MINUTE": int,
        "RATE_LIMIT_BURST_SIZE": int,
        "GAMEPAD_QUEUE_TIMEOUT_MS": int,
    }

    # Default values for optional variables
    DEFAULTS = {
        "GROQ_TIMEOUT_MS": 30000,
        "GROQ_MAX_RETRIES": 3,
        "GEMINI_TIMEOUT_MS": 30000,
        "GEMINI_MAX_RETRIES": 3,
        "HISTORY_BACKEND": "json",
        "HISTORY_MAX_SIZE_MB": 100,
        "HISTORY_ARCHIVE_DAYS": 30,
        "LOG_LEVEL": "INFO",
        "LOG_FILE_MAX_SIZE_MB": 10,
        "LOG_FILE_BACKUP_COUNT": 5,
        "RATE_LIMIT_REQUESTS_PER_MINUTE": 60,
        "RATE_LIMIT_BURST_SIZE": 10,
        "GAMEPAD_QUEUE_TIMEOUT_MS": 5000,
        "ENVIRONMENT": "dev",
    }

    def __init__(self, env_file: str = ".env") -> None:
        """Initialize ConfigManager and load environment variables.

        Args:
            env_file: Path to .env file to load

        Raises:
            ValueError: If required variables are missing or invalid
        """
        # Load .env file if it exists
        if Path(env_file).exists():
            load_dotenv(env_file)

        # Validate and load configuration
        self._config = self._load_and_validate()

    def _load_and_validate(self) -> Config:
        """Load and validate all configuration variables.

        Returns:
            Config object with validated values

        Raises:
            ValueError: If required variables are missing or invalid
        """
        # Check required variables
        missing_vars = []
        for var in self.REQUIRED_VARS:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {len(missing_vars)} variable(s) not set"
            )

        # Load and validate all variables
        config_dict = {}

        # Load required variables (strings)
        config_dict["groq_api_key"] = os.getenv("GROQ_API_KEY", "")
        config_dict["gemini_api_key"] = os.getenv("GEMINI_API_KEY", "")
        config_dict["discord_token"] = os.getenv("DISCORD_TOKEN", "")

        # Load optional variables with type validation
        for env_var, expected_type in self.TYPE_MAPPINGS.items():
            config_key = env_var.lower()
            value = os.getenv(env_var)

            if value is None:
                # Use default value
                config_dict[config_key] = self.DEFAULTS.get(env_var)
            else:
                # Validate type
                try:
                    if expected_type == int:
                        config_dict[config_key] = int(value)
                    else:
                        config_dict[config_key] = value
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Invalid type for {env_var}: expected {expected_type.__name__}"
                    )

        # Load string variables with defaults
        config_dict["history_backend"] = os.getenv(
            "HISTORY_BACKEND", self.DEFAULTS["HISTORY_BACKEND"]
        )
        config_dict["log_level"] = os.getenv(
            "LOG_LEVEL", self.DEFAULTS["LOG_LEVEL"]
        )
        config_dict["environment"] = os.getenv(
            "ENVIRONMENT", self.DEFAULTS["ENVIRONMENT"]
        )

        # Validate log level
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if config_dict["log_level"] not in valid_levels:
            raise ValueError(
                f"Invalid LOG_LEVEL: must be one of {valid_levels}"
            )

        # Validate history backend
        valid_backends = {"json", "sqlite"}
        if config_dict["history_backend"] not in valid_backends:
            raise ValueError(
                f"Invalid HISTORY_BACKEND: must be one of {valid_backends}"
            )

        # Validate environment
        valid_envs = {"dev", "staging", "production"}
        if config_dict["environment"] not in valid_envs:
            raise ValueError(
                f"Invalid ENVIRONMENT: must be one of {valid_envs}"
            )

        return Config(**config_dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with type validation.

        Args:
            key: Configuration key (lowercase, underscore-separated)
            default: Default value if key not found

        Returns:
            Configuration value or default

        Raises:
            AttributeError: If key doesn't exist and no default provided
        """
        if hasattr(self._config, key):
            return getattr(self._config, key)
        elif default is not None:
            return default
        else:
            raise AttributeError(f"Configuration key '{key}' not found")

    def validate(self) -> bool:
        """Validate all configuration values are present and valid.

        Returns:
            True if all configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Check all required fields are set
        required_fields = {
            "groq_api_key",
            "gemini_api_key",
            "discord_token",
        }

        for field in required_fields:
            value = getattr(self._config, field, None)
            if not value:
                raise ValueError(f"Required field '{field}' is not set")

        # Check all integer fields are positive
        int_fields = {
            "groq_timeout_ms",
            "groq_max_retries",
            "gemini_timeout_ms",
            "gemini_max_retries",
            "history_max_size_mb",
            "history_archive_days",
            "log_file_max_size_mb",
            "log_file_backup_count",
            "rate_limit_requests_per_minute",
            "rate_limit_burst_size",
            "gamepad_queue_timeout_ms",
        }

        for field in int_fields:
            value = getattr(self._config, field, None)
            if value is not None and value <= 0:
                raise ValueError(f"Field '{field}' must be positive, got {value}")

        return True

    def to_dict(self) -> dict:
        """Convert config to dictionary, excluding secrets.

        Returns:
            Dictionary representation of config without secret values
        """
        result = {}
        for key, value in self._config.__dict__.items():
            if key not in self.SECRET_KEYS:
                result[key] = value
        return result
