"""Core Orchestrator - Main Alice System."""

import signal
import sys
from typing import Optional

from alice.core.config import Config, ConfigManager
from alice.core.logger import Logger
from alice.core.error_handler import ErrorHandler
from alice.core.schema_validator import SchemaValidator
from alice.core.history_manager import HistoryManager
from alice.core.rate_limiter import RateLimiter
from alice.components.gamepad_controller import GamepadController
from alice.components.macro_system import MacroSystem
from alice.components.vision_engine import VisionEngine
from alice.components.discord_bot import DiscordBot


class AliceSystem:
    """Main Alice System - Orchestrates all components."""

    def __init__(self, config_file: str = ".env"):
        """Initialize AliceSystem.
        
        Args:
            config_file: Path to configuration file
        """
        self.running = False
        self.config: Optional[Config] = None
        self.logger: Optional[Logger] = None
        self.error_handler: Optional[ErrorHandler] = None
        self.schema_validator: Optional[SchemaValidator] = None
        self.history_manager: Optional[HistoryManager] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.gamepad_controller: Optional[GamepadController] = None
        self.macro_system: Optional[MacroSystem] = None
        self.vision_engine: Optional[VisionEngine] = None
        self.discord_bot: Optional[DiscordBot] = None
        
        # Load configuration
        try:
            config_manager = ConfigManager(config_file)
            self.config = config_manager.get_config()
        except Exception as error:
            print(f"Failed to load configuration: {error}")
            sys.exit(1)

    def start(self) -> None:
        """Start all components in correct order."""
        try:
            print("Starting Alice System...")
            
            # 1. Initialize Logger
            self.logger = Logger(self.config)
            self.logger.info("AliceSystem", "Initializing Alice System", {})
            
            # 2. Initialize Error Handler
            self.error_handler = ErrorHandler(self.config, self.logger)
            self.logger.info("AliceSystem", "Error Handler initialized", {})
            
            # 3. Initialize Schema Validator
            self.schema_validator = SchemaValidator(self.logger)
            self.logger.info("AliceSystem", "Schema Validator initialized", {})
            
            # 4. Initialize History Manager
            self.history_manager = HistoryManager(self.config, self.logger, self.error_handler)
            self.logger.info("AliceSystem", "History Manager initialized", {})
            
            # 5. Initialize Rate Limiter
            self.rate_limiter = RateLimiter(self.config, self.logger)
            self.logger.info("AliceSystem", "Rate Limiter initialized", {})
            
            # 6. Initialize Gamepad Controller
            self.gamepad_controller = GamepadController(self.config, self.logger, self.error_handler)
            self.logger.info("AliceSystem", "Gamepad Controller initialized", {})
            
            # 7. Initialize Macro System
            self.macro_system = MacroSystem(self.gamepad_controller, self.logger, self.error_handler)
            self.logger.info("AliceSystem", "Macro System initialized", {})
            
            # 8. Initialize Vision Engine
            self.vision_engine = VisionEngine(
                self.config,
                self.logger,
                self.error_handler,
                self.schema_validator
            )
            self.logger.info("AliceSystem", "Vision Engine initialized", {})
            
            # 9. Initialize Discord Bot
            self.discord_bot = DiscordBot(
                self.config,
                self.logger,
                self.error_handler,
                self.schema_validator,
                self.history_manager
            )
            self.logger.info("AliceSystem", "Discord Bot initialized", {})
            
            self.running = True
            self.logger.info("AliceSystem", "Alice System started successfully", {})
            print("Alice System started successfully!")
            
        except Exception as error:
            self.logger.error(
                "AliceSystem",
                "Failed to start Alice System",
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )
            raise

    def stop(self) -> None:
        """Stop all components gracefully."""
        try:
            self.logger.info("AliceSystem", "Stopping Alice System", {})
            
            # Release all gamepad keys
            if self.gamepad_controller:
                self.gamepad_controller.release_all_keys()
            
            # Archive old history entries
            if self.history_manager:
                self.history_manager.archive_old_entries()
            
            self.running = False
            self.logger.info("AliceSystem", "Alice System stopped", {})
            print("Alice System stopped.")
            
        except Exception as error:
            self.logger.error(
                "AliceSystem",
                "Error during shutdown",
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )

    def is_running(self) -> bool:
        """Check if system is running.
        
        Returns:
            True if running, False otherwise
        """
        return self.running

    def get_status(self) -> dict:
        """Get system status.
        
        Returns:
            Dictionary with component statuses
        """
        return {
            "running": self.running,
            "vision_engine": self.vision_engine.get_status() if self.vision_engine else "not initialized",
            "discord_bot": self.discord_bot.get_status() if self.discord_bot else "not initialized",
            "gamepad_controller": self.gamepad_controller.get_status() if self.gamepad_controller else "not initialized",
            "rate_limiter": self.rate_limiter.get_status() if self.rate_limiter else "not initialized",
        }


def main():
    """Main entry point."""
    system = AliceSystem()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down...")
        system.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start system
    system.start()
    
    # Keep system running
    try:
        while system.is_running():
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        system.stop()


if __name__ == "__main__":
    main()
