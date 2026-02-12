"""Macro System with validation and history."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from alice.components.gamepad_controller import GamepadController, Macro, MacroResult, GamepadCommand
from alice.core.logger import Logger


@dataclass
class MacroExecution:
    """Record of a macro execution."""
    
    macro_name: str
    timestamp: datetime
    success: bool
    execution_time_ms: float
    error: Optional[str] = None
    commands_executed: int = 0


class MacroSystem:
    """Manages macro definition, validation, and execution."""

    def __init__(self, gamepad_controller: GamepadController, logger: Logger, error_handler: any):
        """Initialize MacroSystem.
        
        Args:
            gamepad_controller: GamepadController instance
            logger: Logger instance
            error_handler: ErrorHandler instance
        """
        self.gamepad_controller = gamepad_controller
        self.logger = logger
        self.error_handler = error_handler
        
        # Macro registry
        self.macros: Dict[str, Macro] = {}
        
        # Execution history
        self.execution_history: List[MacroExecution] = []
        
        self.logger.info(
            "MacroSystem",
            "Macro system initialized",
            {}
        )

    def register_macro(self, name: str, macro: Macro) -> None:
        """Register a macro.
        
        Args:
            name: Macro name
            macro: Macro object
        """
        if not self.validate_macro(macro):
            self.logger.error(
                "MacroSystem",
                f"Cannot register invalid macro: {name}",
                {"macro_name": name}
            )
            return
        
        self.macros[name] = macro
        self.logger.info(
            "MacroSystem",
            f"Macro registered: {name}",
            {
                "macro_name": name,
                "command_count": len(macro.commands),
            }
        )

    def execute_macro(self, name: str, params: Optional[Dict[str, any]] = None) -> MacroResult:
        """Execute a macro with optional parameters.
        
        Args:
            name: Macro name
            params: Optional parameters for parameterized macros
            
        Returns:
            MacroResult with execution details
        """
        if name not in self.macros:
            self.logger.error(
                "MacroSystem",
                f"Macro not found: {name}",
                {"macro_name": name}
            )
            return MacroResult(
                success=False,
                macro_name=name,
                execution_time_ms=0,
                error=f"Macro not found: {name}",
                commands_executed=0
            )
        
        macro = self.macros[name]
        
        # Substitute parameters if provided
        if params:
            macro = self._substitute_parameters(macro, params)
        
        # Execute macro
        result = self.gamepad_controller.execute_macro(macro)
        
        # Record execution
        execution = MacroExecution(
            macro_name=name,
            timestamp=datetime.now(),
            success=result.success,
            execution_time_ms=result.execution_time_ms,
            error=result.error,
            commands_executed=result.commands_executed
        )
        self.execution_history.append(execution)
        
        self.logger.info(
            "MacroSystem",
            f"Macro executed: {name}",
            {
                "macro_name": name,
                "success": result.success,
                "execution_time_ms": result.execution_time_ms,
                "commands_executed": result.commands_executed,
            }
        )
        
        return result

    def validate_macro(self, macro: Macro) -> bool:
        """Validate macro before execution.
        
        Args:
            macro: Macro to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not macro.commands:
            self.logger.error(
                "MacroSystem",
                f"Macro has no commands: {macro.name}",
                {"macro_name": macro.name}
            )
            return False
        
        # Validate all commands
        for command in macro.commands:
            if not self._validate_command(command):
                self.logger.error(
                    "MacroSystem",
                    f"Invalid command in macro {macro.name}",
                    {
                        "macro_name": macro.name,
                        "button": command.button,
                        "action": command.action,
                    }
                )
                return False
        
        return True

    def get_execution_history(self, macro_name: Optional[str] = None) -> List[MacroExecution]:
        """Get execution history for debugging.
        
        Args:
            macro_name: Optional filter by macro name
            
        Returns:
            List of MacroExecution records
        """
        if macro_name:
            return [e for e in self.execution_history if e.macro_name == macro_name]
        return self.execution_history.copy()

    def get_macro_stats(self, macro_name: str) -> Optional[Dict[str, any]]:
        """Get statistics for a macro.
        
        Args:
            macro_name: Macro name
            
        Returns:
            Dictionary with statistics or None if macro not found
        """
        if macro_name not in self.macros:
            return None
        
        executions = [e for e in self.execution_history if e.macro_name == macro_name]
        
        if not executions:
            return {
                "macro_name": macro_name,
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "average_execution_time_ms": 0,
            }
        
        successful = sum(1 for e in executions if e.success)
        failed = len(executions) - successful
        avg_time = sum(e.execution_time_ms for e in executions) / len(executions)
        
        return {
            "macro_name": macro_name,
            "total_executions": len(executions),
            "successful_executions": successful,
            "failed_executions": failed,
            "average_execution_time_ms": avg_time,
            "success_rate": successful / len(executions) if executions else 0,
        }

    def _substitute_parameters(self, macro: Macro, params: Dict[str, any]) -> Macro:
        """Substitute parameters into macro commands.
        
        Args:
            macro: Original macro
            params: Parameters to substitute
            
        Returns:
            New macro with substituted parameters
        """
        # For now, just return the original macro
        # In a real implementation, this would substitute parameters into command values
        return macro

    def _validate_command(self, command: GamepadCommand) -> bool:
        """Validate a gamepad command.
        
        Args:
            command: Command to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Valid buttons
        valid_buttons = {
            "W", "A", "S", "D",
            "Space", "Shift", "Ctrl", "Alt",
            "E", "R", "T", "Y", "U", "I", "O", "P",
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
            "LMB", "RMB", "MMB",
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
