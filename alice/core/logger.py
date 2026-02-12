"""Structured logging system with JSON output and file rotation."""

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from alice.core.config import Config


class Logger:
    """Structured logging system with JSON output to console and file."""

    LOG_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    def __init__(self, config: Config, log_dir: str = "logs") -> None:
        """Initialize Logger with file rotation.

        Args:
            config: Configuration object
            log_dir: Directory to store log files
        """
        self.config = config
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create logger
        self.logger = logging.getLogger("alice")
        self.logger.setLevel(self.LOG_LEVELS[config.log_level])

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler (JSON format)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.LOG_LEVELS[config.log_level])
        console_handler.setFormatter(self._get_json_formatter())
        self.logger.addHandler(console_handler)

        # File handler with rotation (JSON format)
        log_file = self.log_dir / "alice.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=config.log_file_max_size_mb * 1024 * 1024,
            backupCount=config.log_file_backup_count,
        )
        file_handler.setLevel(self.LOG_LEVELS[config.log_level])
        file_handler.setFormatter(self._get_json_formatter())
        self.logger.addHandler(file_handler)

        # Store logs in memory for filtering
        self._log_buffer: List[Dict[str, Any]] = []

    def _get_json_formatter(self) -> logging.Formatter:
        """Get JSON formatter for logging.

        Returns:
            Formatter that outputs JSON
        """
        return logging.Formatter(
            fmt='%(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )

    def _format_log_entry(
        self,
        level: str,
        component: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format log entry as JSON.

        Args:
            level: Log level
            component: Component name
            message: Log message
            context: Additional context

        Returns:
            JSON formatted log entry
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "component": component,
            "message": message,
        }

        if context:
            entry["context"] = context

        return json.dumps(entry)

    def log(
        self,
        level: str,
        component: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log structured message to console and file.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            component: Component name
            message: Log message
            context: Additional context
        """
        # Format log entry
        log_entry = self._format_log_entry(level, component, message, context)

        # Store in buffer for filtering
        entry_dict = json.loads(log_entry)
        self._log_buffer.append(entry_dict)

        # Log using standard logger
        log_level = self.LOG_LEVELS.get(level, logging.INFO)
        self.logger.log(log_level, log_entry)

    def debug(
        self,
        component: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log debug message.

        Args:
            component: Component name
            message: Log message
            context: Additional context
        """
        self.log("DEBUG", component, message, context)

    def info(
        self,
        component: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log info message.

        Args:
            component: Component name
            message: Log message
            context: Additional context
        """
        self.log("INFO", component, message, context)

    def warning(
        self,
        component: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log warning message.

        Args:
            component: Component name
            message: Log message
            context: Additional context
        """
        self.log("WARNING", component, message, context)

    def error(
        self,
        component: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log error message.

        Args:
            component: Component name
            message: Log message
            context: Additional context
        """
        self.log("ERROR", component, message, context)

    def critical(
        self,
        component: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log critical message.

        Args:
            component: Component name
            message: Log message
            context: Additional context
        """
        self.log("CRITICAL", component, message, context)

    def filter_logs(
        self,
        component: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Filter logs by component, level, or timestamp.

        Args:
            component: Filter by component name
            level: Filter by log level
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp

        Returns:
            List of filtered log entries
        """
        results = []

        for entry in self._log_buffer:
            # Filter by component
            if component and entry.get("component") != component:
                continue

            # Filter by level
            if level and entry.get("level") != level:
                continue

            # Filter by timestamp
            if start_time or end_time:
                entry_time = datetime.fromisoformat(
                    entry.get("timestamp", "").replace("Z", "+00:00")
                )

                if start_time and entry_time < start_time:
                    continue

                if end_time and entry_time > end_time:
                    continue

            results.append(entry)

        return results

    def close(self) -> None:
        """Close all handlers and cleanup resources."""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
