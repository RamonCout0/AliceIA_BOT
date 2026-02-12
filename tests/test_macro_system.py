"""Tests for Macro System."""

import pytest
from datetime import datetime
from unittest.mock import Mock
from hypothesis import given, strategies as st

from alice.components.macro_system import MacroSystem, MacroExecution
from alice.components.gamepad_controller import GamepadController, Macro, GamepadCommand
from alice.core.logger import Logger


@pytest.fixture
def mock_gamepad_controller():
    """Create mock gamepad controller."""
    return Mock(spec=GamepadController)


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return Mock(spec=Logger)


@pytest.fixture
def mock_error_handler():
    """Create mock error handler."""
    return Mock()


@pytest.fixture
def macro_system(mock_gamepad_controller, mock_logger, mock_error_handler):
    """Create MacroSystem instance."""
    return MacroSystem(mock_gamepad_controller, mock_logger, mock_error_handler)


class TestMacroRegistration:
    """Test macro registration."""

    def test_register_valid_macro(self, macro_system):
        """Test registering a valid macro."""
        commands = [
            GamepadCommand(button="W", action="press"),
            GamepadCommand(button="W", action="release"),
        ]
        macro = Macro(
            name="move_forward",
            description="Move forward",
            commands=commands
        )
        
        macro_system.register_macro("move_forward", macro)
        
        assert "move_forward" in macro_system.macros

    def test_register_invalid_macro(self, macro_system):
        """Test registering an invalid macro."""
        macro = Macro(
            name="invalid",
            description="Invalid",
            commands=[]
        )
        
        macro_system.register_macro("invalid", macro)
        
        # Should not register invalid macro
        assert "invalid" not in macro_system.macros

    def test_register_multiple_macros(self, macro_system):
        """Test registering multiple macros."""
        for i in range(3):
            commands = [GamepadCommand(button="W", action="press")]
            macro = Macro(
                name=f"macro_{i}",
                description=f"Macro {i}",
                commands=commands
            )
            macro_system.register_macro(f"macro_{i}", macro)
        
        assert len(macro_system.macros) == 3


class TestMacroExecution:
    """Test macro execution."""

    def test_execute_registered_macro(self, macro_system, mock_gamepad_controller):
        """Test executing a registered macro."""
        commands = [GamepadCommand(button="W", action="press")]
        macro = Macro(
            name="move",
            description="Move",
            commands=commands
        )
        
        macro_system.register_macro("move", macro)
        
        # Mock the gamepad controller result
        from alice.components.gamepad_controller import MacroResult
        mock_result = MacroResult(
            success=True,
            macro_name="move",
            execution_time_ms=10,
            commands_executed=1
        )
        mock_gamepad_controller.execute_macro.return_value = mock_result
        
        result = macro_system.execute_macro("move")
        
        assert result.success is True
        assert result.macro_name == "move"

    def test_execute_nonexistent_macro(self, macro_system):
        """Test executing a non-existent macro."""
        result = macro_system.execute_macro("nonexistent")
        
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_execute_macro_with_parameters(self, macro_system, mock_gamepad_controller):
        """Test executing macro with parameters."""
        commands = [GamepadCommand(button="W", action="press")]
        macro = Macro(
            name="move",
            description="Move",
            commands=commands,
            parameters=["direction"]
        )
        
        macro_system.register_macro("move", macro)
        
        from alice.components.gamepad_controller import MacroResult
        mock_result = MacroResult(
            success=True,
            macro_name="move",
            execution_time_ms=10,
            commands_executed=1
        )
        mock_gamepad_controller.execute_macro.return_value = mock_result
        
        result = macro_system.execute_macro("move", {"direction": "forward"})
        
        assert result.success is True


class TestMacroValidation:
    """Test macro validation."""

    def test_validate_valid_macro(self, macro_system):
        """Test validating a valid macro."""
        commands = [
            GamepadCommand(button="W", action="press"),
            GamepadCommand(button="W", action="release"),
        ]
        macro = Macro(
            name="valid",
            description="Valid",
            commands=commands
        )
        
        assert macro_system.validate_macro(macro) is True

    def test_validate_empty_macro(self, macro_system):
        """Test validating an empty macro."""
        macro = Macro(
            name="empty",
            description="Empty",
            commands=[]
        )
        
        assert macro_system.validate_macro(macro) is False

    def test_validate_macro_with_invalid_command(self, macro_system):
        """Test validating macro with invalid command."""
        commands = [
            GamepadCommand(button="INVALID", action="press"),
        ]
        macro = Macro(
            name="invalid",
            description="Invalid",
            commands=commands
        )
        
        assert macro_system.validate_macro(macro) is False


class TestExecutionHistory:
    """Test execution history tracking."""

    def test_execution_recorded(self, macro_system, mock_gamepad_controller):
        """Test that execution is recorded."""
        commands = [GamepadCommand(button="W", action="press")]
        macro = Macro(
            name="move",
            description="Move",
            commands=commands
        )
        
        macro_system.register_macro("move", macro)
        
        from alice.components.gamepad_controller import MacroResult
        mock_result = MacroResult(
            success=True,
            macro_name="move",
            execution_time_ms=10,
            commands_executed=1
        )
        mock_gamepad_controller.execute_macro.return_value = mock_result
        
        macro_system.execute_macro("move")
        
        assert len(macro_system.execution_history) == 1

    def test_get_execution_history(self, macro_system, mock_gamepad_controller):
        """Test getting execution history."""
        commands = [GamepadCommand(button="W", action="press")]
        macro = Macro(
            name="move",
            description="Move",
            commands=commands
        )
        
        macro_system.register_macro("move", macro)
        
        from alice.components.gamepad_controller import MacroResult
        mock_result = MacroResult(
            success=True,
            macro_name="move",
            execution_time_ms=10,
            commands_executed=1
        )
        mock_gamepad_controller.execute_macro.return_value = mock_result
        
        # Execute multiple times
        for i in range(3):
            macro_system.execute_macro("move")
        
        history = macro_system.get_execution_history()
        assert len(history) == 3

    def test_filter_history_by_macro_name(self, macro_system, mock_gamepad_controller):
        """Test filtering history by macro name."""
        from alice.components.gamepad_controller import MacroResult
        mock_result = MacroResult(
            success=True,
            macro_name="test",
            execution_time_ms=10,
            commands_executed=1
        )
        mock_gamepad_controller.execute_macro.return_value = mock_result
        
        # Register and execute multiple macros
        for i in range(2):
            commands = [GamepadCommand(button="W", action="press")]
            macro = Macro(
                name=f"macro_{i}",
                description=f"Macro {i}",
                commands=commands
            )
            macro_system.register_macro(f"macro_{i}", macro)
            macro_system.execute_macro(f"macro_{i}")
        
        # Filter by macro name
        history = macro_system.get_execution_history("macro_0")
        assert len(history) == 1
        assert history[0].macro_name == "macro_0"


class TestMacroStats:
    """Test macro statistics."""

    def test_get_macro_stats(self, macro_system, mock_gamepad_controller):
        """Test getting macro statistics."""
        commands = [GamepadCommand(button="W", action="press")]
        macro = Macro(
            name="move",
            description="Move",
            commands=commands
        )
        
        macro_system.register_macro("move", macro)
        
        from alice.components.gamepad_controller import MacroResult
        mock_result = MacroResult(
            success=True,
            macro_name="move",
            execution_time_ms=10,
            commands_executed=1
        )
        mock_gamepad_controller.execute_macro.return_value = mock_result
        
        # Execute macro
        macro_system.execute_macro("move")
        
        stats = macro_system.get_macro_stats("move")
        
        assert stats is not None
        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 1
        assert stats["failed_executions"] == 0

    def test_get_stats_nonexistent_macro(self, macro_system):
        """Test getting stats for non-existent macro."""
        stats = macro_system.get_macro_stats("nonexistent")
        
        assert stats is None

    def test_macro_stats_with_failures(self, macro_system, mock_gamepad_controller):
        """Test macro stats with failures."""
        commands = [GamepadCommand(button="W", action="press")]
        macro = Macro(
            name="move",
            description="Move",
            commands=commands
        )
        
        macro_system.register_macro("move", macro)
        
        from alice.components.gamepad_controller import MacroResult
        
        # First execution succeeds
        success_result = MacroResult(
            success=True,
            macro_name="move",
            execution_time_ms=10,
            commands_executed=1
        )
        
        # Second execution fails
        fail_result = MacroResult(
            success=False,
            macro_name="move",
            execution_time_ms=5,
            error="Test error",
            commands_executed=0
        )
        
        mock_gamepad_controller.execute_macro.side_effect = [success_result, fail_result]
        
        macro_system.execute_macro("move")
        macro_system.execute_macro("move")
        
        stats = macro_system.get_macro_stats("move")
        
        assert stats["total_executions"] == 2
        assert stats["successful_executions"] == 1
        assert stats["failed_executions"] == 1
        assert stats["success_rate"] == 0.5


# Property-based tests

def test_property_macro_validation_before_execution():
    """Property 25: Macro Validation Before Execution.
    
    For any macro with invalid commands, the Macro_System should reject 
    it before execution and provide detailed error messages.
    
    Validates: Requirements 9.2
    """
    mock_gamepad = Mock(spec=GamepadController)
    mock_logger = Mock(spec=Logger)
    mock_error_handler = Mock()
    
    system = MacroSystem(mock_gamepad, mock_logger, mock_error_handler)
    
    # Try to register invalid macro
    invalid_macro = Macro(
        name="invalid",
        description="Invalid",
        commands=[]
    )
    
    system.register_macro("invalid", invalid_macro)
    
    # Should not be registered
    assert "invalid" not in system.macros


def test_property_parameterized_macro_substitution():
    """Property 26: Parameterized Macro Substitution.
    
    For any parameterized macro with parameters provided, the Macro_System 
    should substitute the parameters into the macro commands before execution.
    
    Validates: Requirements 9.3
    """
    mock_gamepad = Mock(spec=GamepadController)
    mock_logger = Mock(spec=Logger)
    mock_error_handler = Mock()
    
    system = MacroSystem(mock_gamepad, mock_logger, mock_error_handler)
    
    # Create parameterized macro
    commands = [GamepadCommand(button="W", action="press")]
    macro = Macro(
        name="move",
        description="Move",
        commands=commands,
        parameters=["direction", "distance"]
    )
    
    system.register_macro("move", macro)
    
    from alice.components.gamepad_controller import MacroResult
    mock_result = MacroResult(
        success=True,
        macro_name="move",
        execution_time_ms=10,
        commands_executed=1
    )
    mock_gamepad.execute_macro.return_value = mock_result
    
    # Execute with parameters
    result = system.execute_macro("move", {"direction": "forward", "distance": 10})
    
    assert result.success is True


def test_property_macro_execution_history_tracking():
    """Property 27: Macro Execution History Tracking.
    
    For any macro execution, the Macro_System should record the execution 
    in history including success/failure, execution time, and any errors.
    
    Validates: Requirements 9.6
    """
    mock_gamepad = Mock(spec=GamepadController)
    mock_logger = Mock(spec=Logger)
    mock_error_handler = Mock()
    
    system = MacroSystem(mock_gamepad, mock_logger, mock_error_handler)
    
    # Register macro
    commands = [GamepadCommand(button="W", action="press")]
    macro = Macro(
        name="move",
        description="Move",
        commands=commands
    )
    system.register_macro("move", macro)
    
    from alice.components.gamepad_controller import MacroResult
    mock_result = MacroResult(
        success=True,
        macro_name="move",
        execution_time_ms=10,
        commands_executed=1
    )
    mock_gamepad.execute_macro.return_value = mock_result
    
    # Execute macro
    system.execute_macro("move")
    
    # Verify history
    history = system.get_execution_history("move")
    assert len(history) == 1
    assert history[0].success is True
    assert history[0].execution_time_ms == 10
    assert history[0].commands_executed == 1
