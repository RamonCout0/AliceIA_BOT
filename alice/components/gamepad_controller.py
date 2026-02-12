"""Gamepad Controller with thread safety."""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from queue import Queue

from alice.core.logger import Logger


@dataclass
class GamepadCommand:
    """Represents a gamepad command."""
    
    button: str  # Button name (e.g., "W", "A", "S", "D", "Space")
    action: str  # "press", "release", "hold"
    duration_ms: int = 0  # For hold actions
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Macro:
    """Represents a macro (sequence of commands)."""
    
    name: str
    description: str
    commands: List[GamepadCommand]
    parameters: List[str] = field(default_factory=list)
    timeout_ms: int = 5000


@dataclass
class MacroResult:
    """Result of macro execution."""
    
    success: bool
    macro_name: str
    execution_time_ms: float
    error: Optional[str] = None
    commands_executed: int = 0


class GamepadController:
    """Thread-safe virtual gamepad interface."""

    def __init__(self, config: Any, logger: Logger, error_handler: Any):
        """Initialize GamepadController.
        
        Args:
            config: Configuration object
            logger: Logger instance
            error_handler: ErrorHandler instance
        """
        self.config = config
        self.logger = logger
        self.error_handler = error_handler
        
        # Thread safety
        self.command_queue: Queue = Queue()
        self.lock = threading.Lock()
        self.held_keys: set = set()
        
        # Macro execution
        self.current_macro: Optional[Macro] = None
        self.macro_interrupted = False
        
        self.logger.info(
            "GamepadController",
            "Gamepad controller initialized",
            {}
        )

    def send_command(self, command: GamepadCommand) -> None:
        """Send command to gamepad (thread-safe, queued).
        
        Args:
            command: GamepadCommand to send
        """
        # Validate command
        if not self._validate_command(command):
            self.logger.error(
                "GamepadController",
                f"Invalid command: {command.button} {command.action}",
                {
                    "button": command.button,
                    "action": command.action,
                }
            )
            return
        
        # Queue command
        self.command_queue.put(command)
        self.logger.debug(
            "GamepadController",
            f"Command queued: {command.button} {command.action}",
            {
                "button": command.button,
                "action": command.action,
                "queue_size": self.command_queue.qsize(),
            }
        )

    def execute_macro(self, macro: Macro) -> MacroResult:
        """Execute macro atomically.
        
        Args:
            macro: Macro to execute
            
        Returns:
            MacroResult with execution details
        """
        start_time = time.time()
        self.current_macro = macro
        self.macro_interrupted = False
        
        # Validate macro
        if not self._validate_macro(macro):
            elapsed = (time.time() - start_time) * 1000
            self.release_all_keys()
            return MacroResult(
                success=False,
                macro_name=macro.name,
                execution_time_ms=elapsed,
                error="Macro validation failed",
                commands_executed=0
            )
        
        try:
            commands_executed = 0
            
            # Execute commands
            for command in macro.commands:
                if self.macro_interrupted:
                    break
                
                self.send_command(command)
                commands_executed += 1
                
                # Wait for command duration if hold action
                if command.action == "hold":
                    time.sleep(command.duration_ms / 1000.0)
            
            elapsed = (time.time() - start_time) * 1000
            
            self.logger.info(
                "GamepadController",
                f"Macro executed: {macro.name}",
                {
                    "macro_name": macro.name,
                    "commands_executed": commands_executed,
                    "execution_time_ms": elapsed,
                }
            )
            
            return MacroResult(
                success=True,
                macro_name=macro.name,
                execution_time_ms=elapsed,
                commands_executed=commands_executed
            )
            
        except Exception as error:
            elapsed = (time.time() - start_time) * 1000
            self.logger.error(
                "GamepadController",
                f"Macro execution failed: {macro.name}",
                {
                    "macro_name": macro.name,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "execution_time_ms": elapsed,
                }
            )
            
            # Release all keys on error
            self.release_all_keys()
            
            return MacroResult(
                success=False,
                macro_name=macro.name,
                execution_time_ms=elapsed,
                error=str(error),
                commands_executed=0
            )
        
        finally:
            self.current_macro = None

    def release_all_keys(self) -> None:
        """Release all held keys (safe state)."""
        with self.lock:
            keys_count = len(self.held_keys)
            self.held_keys.clear()
            
            self.logger.info(
                "GamepadController",
                "All keys released",
                {"keys_released": keys_count}
            )

    def interrupt_macro(self) -> None:
        """Interrupt current macro execution."""
        self.macro_interrupted = True
        self.release_all_keys()
        
        if self.current_macro:
            self.logger.info(
                "GamepadController",
                "Macro interrupted",
                {"macro_name": self.current_macro.name}
            )

    def get_status(self) -> Dict[str, Any]:
        """Get current status.
        
        Returns:
            Dictionary with status information
        """
        with self.lock:
            return {
                "queue_size": self.command_queue.qsize(),
                "held_keys": list(self.held_keys),
                "current_macro": self.current_macro.name if self.current_macro else None,
                "macro_interrupted": self.macro_interrupted,
            }

    def _validate_command(self, command: GamepadCommand) -> bool:
        """Validate gamepad command.
        
        Args:
            command: Command to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Valid buttons
        valid_buttons = {
            "W", "A", "S", "D",  # Movement
            "Space", "Shift", "Ctrl", "Alt",  # Modifiers
            "E", "R", "T", "Y", "U", "I", "O", "P",  # Hotkeys
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",  # Number keys
            "LMB", "RMB", "MMB",  # Mouse buttons
        }
        
        # Valid actions
        valid_actions = {"press", "release", "hold"}
        
        if command.button not in valid_buttons:
            return False
        
        if command.action not in valid_actions:
            return False
        
        if command.action == "hold" and command.duration_ms <= 0:
            return False
        
        return True

    def _validate_macro(self, macro: Macro) -> bool:
        """Validate macro before execution.
        
        Args:
            macro: Macro to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not macro.commands:
            self.logger.error(
                "GamepadController",
                f"Macro has no commands: {macro.name}",
                {"macro_name": macro.name}
            )
            return False
        
        # Validate all commands
        for command in macro.commands:
            if not self._validate_command(command):
                self.logger.error(
                    "GamepadController",
                    f"Invalid command in macro {macro.name}",
                    {
                        "macro_name": macro.name,
                        "button": command.button,
                        "action": command.action,
                    }
                )
                return False
        
        return True
