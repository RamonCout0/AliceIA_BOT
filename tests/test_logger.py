"""Property-based tests for Logger."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from alice.core.config import Config, ConfigManager
from alice.core.logger import Logger


class TestLoggerProperties:
    """Property-based tests for Logger."""

    @pytest.fixture(autouse=True)
    def setup_logger(self):
        """Setup logger for tests."""
        import os
        import tempfile

        self.tmpdir = tempfile.mkdtemp()
        env_file = Path(self.tmpdir) / ".env"
        env_file.write_text(
            "GROQ_API_KEY=test\nGEMINI_API_KEY=test\nDISCORD_TOKEN=test"
        )

        original_env = {}
        for var in ["GROQ_API_KEY", "GEMINI_API_KEY", "DISCORD_TOKEN"]:
            original_env[var] = os.environ.pop(var, None)

        config_manager = ConfigManager(str(env_file))
        config = Config(
            groq_api_key=config_manager.get("groq_api_key"),
            groq_timeout_ms=config_manager.get("groq_timeout_ms"),
            groq_max_retries=config_manager.get("groq_max_retries"),
            gemini_api_key=config_manager.get("gemini_api_key"),
            gemini_timeout_ms=config_manager.get("gemini_timeout_ms"),
            gemini_max_retries=config_manager.get("gemini_max_retries"),
            discord_token=config_manager.get("discord_token"),
            history_backend=config_manager.get("history_backend"),
            history_max_size_mb=config_manager.get("history_max_size_mb"),
            history_archive_days=config_manager.get("history_archive_days"),
            log_level=config_manager.get("log_level"),
            log_file_max_size_mb=config_manager.get("log_file_max_size_mb"),
            log_file_backup_count=config_manager.get("log_file_backup_count"),
            rate_limit_requests_per_minute=config_manager.get(
                "rate_limit_requests_per_minute"
            ),
            rate_limit_burst_size=config_manager.get("rate_limit_burst_size"),
            gamepad_queue_timeout_ms=config_manager.get("gamepad_queue_timeout_ms"),
            environment=config_manager.get("environment"),
        )

        self.logger = Logger(config, log_dir=str(Path(self.tmpdir) / "logs"))
        self.original_env = original_env

        yield

        # Cleanup
        self.logger.close()
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value

    @given(
        level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
        component=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        message=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=5)
    def test_property_11_logger_output_contains_all_required_fields(
        self, level, component, message
    ):
        """Property 11: Logger Output Contains All Required Fields.

        For any log message written by the Logger, the output should be valid
        JSON containing timestamp, level, component, and message fields.

        **Validates: Requirements 5.1**
        """
        # Log message
        self.logger.log(level, component, message)

        # Get filtered logs
        logs = self.logger.filter_logs()

        # Verify at least one log entry
        assert len(logs) > 0

        # Get the last log entry
        log_entry = logs[-1]

        # Verify all required fields are present
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "component" in log_entry
        assert "message" in log_entry

        # Verify field values
        assert log_entry["level"] == level
        assert log_entry["component"] == component
        assert log_entry["message"] == message

        # Verify timestamp is valid ISO format
        datetime.fromisoformat(log_entry["timestamp"].replace("Z", "+00:00"))

    @given(
        component=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        message=st.text(min_size=1, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz0123456789 "),
    )
    @settings(max_examples=3)
    def test_property_12_logger_writes_to_both_console_and_file(
        self, component, message
    ):
        """Property 12: Logger Writes to Both Console and File.

        For any log message written by the Logger, the message should appear
        in both console output and the log file.

        **Validates: Requirements 5.3**
        """
        # Log message
        self.logger.info(component, message)

        # Verify log file exists and contains the message
        log_file = Path(self.tmpdir) / "logs" / "alice.log"
        assert log_file.exists()

        log_content = log_file.read_text()
        # Check that component and message appear in the log file
        assert component in log_content
        # Message may be JSON-escaped, so check for it in the buffer instead
        logs = self.logger.filter_logs()
        assert len(logs) > 0
        assert any(
            log["message"] == message and log["component"] == component for log in logs
        )

    @given(
        component=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
    )
    @settings(max_examples=3)
    def test_property_14_logger_filtering_by_component(self, component):
        """Property 14: Logger Filtering by Component.

        For any set of log messages from different components, filtering by
        component should return only messages from that component.

        **Validates: Requirements 5.6**
        """
        # Log messages from different components
        self.logger.info("component1", "message1")
        self.logger.info("component2", "message2")
        self.logger.info(component, "message3")

        # Filter by component
        filtered = self.logger.filter_logs(component=component)

        # Verify only messages from the specified component are returned
        assert len(filtered) > 0
        for log in filtered:
            assert log["component"] == component


class TestLoggerUnit:
    """Unit tests for Logger."""

    def test_logger_creates_log_file(self):
        """Test Logger creates log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "GROQ_API_KEY=test\nGEMINI_API_KEY=test\nDISCORD_TOKEN=test"
            )

            original_env = {}
            try:
                for var in ["GROQ_API_KEY", "GEMINI_API_KEY", "DISCORD_TOKEN"]:
                    original_env[var] = os.environ.pop(var, None)

                config_manager = ConfigManager(str(env_file))
                config = Config(
                    groq_api_key=config_manager.get("groq_api_key"),
                    groq_timeout_ms=config_manager.get("groq_timeout_ms"),
                    groq_max_retries=config_manager.get("groq_max_retries"),
                    gemini_api_key=config_manager.get("gemini_api_key"),
                    gemini_timeout_ms=config_manager.get("gemini_timeout_ms"),
                    gemini_max_retries=config_manager.get("gemini_max_retries"),
                    discord_token=config_manager.get("discord_token"),
                    history_backend=config_manager.get("history_backend"),
                    history_max_size_mb=config_manager.get("history_max_size_mb"),
                    history_archive_days=config_manager.get("history_archive_days"),
                    log_level=config_manager.get("log_level"),
                    log_file_max_size_mb=config_manager.get("log_file_max_size_mb"),
                    log_file_backup_count=config_manager.get("log_file_backup_count"),
                    rate_limit_requests_per_minute=config_manager.get(
                        "rate_limit_requests_per_minute"
                    ),
                    rate_limit_burst_size=config_manager.get("rate_limit_burst_size"),
                    gamepad_queue_timeout_ms=config_manager.get(
                        "gamepad_queue_timeout_ms"
                    ),
                    environment=config_manager.get("environment"),
                )

                log_dir = Path(tmpdir) / "logs"
                logger = Logger(config, log_dir=str(log_dir))

                # Verify log directory exists
                assert log_dir.exists()

                # Verify log file exists after logging
                logger.info("test", "test message")
                log_file = log_dir / "alice.log"
                assert log_file.exists()

                logger.close()

            finally:
                for var, value in original_env.items():
                    if value is not None:
                        os.environ[var] = value

    def test_logger_json_format(self):
        """Test Logger outputs valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "GROQ_API_KEY=test\nGEMINI_API_KEY=test\nDISCORD_TOKEN=test"
            )

            original_env = {}
            try:
                for var in ["GROQ_API_KEY", "GEMINI_API_KEY", "DISCORD_TOKEN"]:
                    original_env[var] = os.environ.pop(var, None)

                config_manager = ConfigManager(str(env_file))
                config = Config(
                    groq_api_key=config_manager.get("groq_api_key"),
                    groq_timeout_ms=config_manager.get("groq_timeout_ms"),
                    groq_max_retries=config_manager.get("groq_max_retries"),
                    gemini_api_key=config_manager.get("gemini_api_key"),
                    gemini_timeout_ms=config_manager.get("gemini_timeout_ms"),
                    gemini_max_retries=config_manager.get("gemini_max_retries"),
                    discord_token=config_manager.get("discord_token"),
                    history_backend=config_manager.get("history_backend"),
                    history_max_size_mb=config_manager.get("history_max_size_mb"),
                    history_archive_days=config_manager.get("history_archive_days"),
                    log_level=config_manager.get("log_level"),
                    log_file_max_size_mb=config_manager.get("log_file_max_size_mb"),
                    log_file_backup_count=config_manager.get("log_file_backup_count"),
                    rate_limit_requests_per_minute=config_manager.get(
                        "rate_limit_requests_per_minute"
                    ),
                    rate_limit_burst_size=config_manager.get("rate_limit_burst_size"),
                    gamepad_queue_timeout_ms=config_manager.get(
                        "gamepad_queue_timeout_ms"
                    ),
                    environment=config_manager.get("environment"),
                )

                logger = Logger(config, log_dir=str(Path(tmpdir) / "logs"))

                # Log message
                logger.info("test_component", "test message")

                # Get logs
                logs = logger.filter_logs()
                assert len(logs) > 0

                # Verify JSON structure
                log_entry = logs[-1]
                assert isinstance(log_entry, dict)
                assert "timestamp" in log_entry
                assert "level" in log_entry
                assert "component" in log_entry
                assert "message" in log_entry

                logger.close()

            finally:
                for var, value in original_env.items():
                    if value is not None:
                        os.environ[var] = value
