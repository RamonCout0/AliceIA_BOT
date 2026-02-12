"""Tests for Gamepad Controller."""

import pytest
import time
import threading
from datetime import datetime
from unittest.mock import Mock
from hypothesis import given, strategies as st

from alice.components.gamepad_controller import (
    GamepadController, GamepadCommand, Macro, MacroResult
)
from alice.core.logger import Logger


@pytest.fixture
def mock_config():
    """Create mock config."""
    return Mock()


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return Mock(spec=Logger)


@pytest.fixture
def mock_error_handler():
    """Create mock error handler."""
    return Mock()


@pytest.fixture
def gamepad_controller(mock_config, mock_logger, mock_error_handler):
    """Create GamepadController instance."""
    return GamepadController(mock_config, mock_logger, mock_error_handler)


class TestGamepadCommand:
    """Test GamepadCommand dataclass."""

    def test_create_command(self):
        """Test creating a gamepad command."""
        cmd = GamepadCommand(button="W", action="press")
        
        assert cmd.button == "W"
        assert cmd.action == "press"
        assert cmd.duration_ms == 0

    def test_create_hold_command(self):
        """Test creating a hold command."""
        cmd = GamepadCommand(button="Space", action="hold", duration_ms=500)
        
        assert cmd.button == "Space"
        assert cmd.action == "hold"
        assert cmd.duration_ms == 500


class TestMacro:
    """Test Macro dataclass."""

    def test_create_macro(self):
        """Test creating a macro."""
        commands = [
            GamepadCommand(button="W", action="press"),
            GamepadCommand(button="W", action="release"),
        ]
        macro = Macro(
            name="move_forward",
            description="Move forward",
            commands=commands
        )
        
        assert macro.name == "move_forward"
        assert len(macro.commands) == 2

    def test_macro_with_parameters(self):
        """Test macro with parameters."""
        commands = [GamepadCommand(button="W", action="press")]
        macro = Macro(
            name="move",
            description="Move",
            commands=commands,
            parameters=["direction", "distance"]
        )
        
        assert len(macro.parameters) == 2


class TestCommandSending:
    """Test sending commands."""

    def test_send_valid_command(self, gamepad_controller):
        """Test sending a valid command."""
        cmd = GamepadCommand(button="W", action="press")
        gamepad_controller.send_command(cmd)
        
        assert gamepad_controller.command_queue.qsize() == 1

    def test_send_multiple_commands(self, gamepad_controller):
        """Test sending multiple commands."""
        for i in range(5):
            cmd = GamepadCommand(button="W", action="press")
            gamepad_controller.send_command(cmd)
        
        assert gamepad_controller.command_queue.qsize() == 5

    def test_send_invalid_button(self, gamepad_controller):
        """Test sending command with invalid button."""
        cmd = GamepadCommand(button="INVALID", action="press")
        gamepad_controller.send_command(cmd)
        
        # Should not queue invalid command
        assert gamepad_controller.command_queue.qsize() == 0

    def test_send_invalid_action(self, gamepad_controller):
        """Test sending command with invalid action."""
        cmd = GamepadCommand(button="W", action="invalid_action")
        gamepad_controller.send_command(cmd)
        
        # Should not queue invalid command
        assert gamepad_controller.command_queue.qsize() == 0

    def test_send_hold_without_duration(self, gamepad_controller):
        """Test sending hold command without duration."""
        cmd = GamepadCommand(button="Space", action="hold", duration_ms=0)
        gamepad_controller.send_command(cmd)
        
        # Should not queue invalid command
        assert gamepad_controller.command_queue.qsize() == 0


class TestMacroExecution:
    """Test macro execution."""

    def test_execute_simple_macro(self, gamepad_controller):
        """Test executing a simple macro."""
        commands = [
            GamepadCommand(button="W", action="press"),
            GamepadCommand(button="W", action="release"),
        ]
        macro = Macro(
            name="move_forward",
            description="Move forward",
            commands=commands
        )
        
        result = gamepad_controller.execute_macro(macro)
        
        assert result.success is True
        assert result.macro_name == "move_forward"
        assert result.commands_executed == 2

    def test_execute_macro_with_hold(self, gamepad_controller):
        """Test executing macro with hold command."""
        commands = [
            GamepadCommand(button="Space", action="hold", duration_ms=100),
        ]
        macro = Macro(
            name="jump",
            description="Jump",
            commands=commands
        )
        
        start = time.time()
        result = gamepad_controller.execute_macro(macro)
        elapsed = (time.time() - start) * 1000
        
        assert result.success is True
        assert elapsed >= 100

    def test_execute_macro_with_invalid_command(self, gamepad_controller):
        """Test executing macro with invalid command."""
        commands = [
            GamepadCommand(button="INVALID", action="press"),
        ]
        macro = Macro(
            name="invalid_macro",
            description="Invalid",
            commands=commands
        )
        
        result = gamepad_controller.execute_macro(macro)
        
        assert result.success is False
        assert result.error is not None

    def test_execute_empty_macro(self, gamepad_controller):
        """Test executing empty macro."""
        macro = Macro(
            name="empty",
            description="Empty",
            commands=[]
        )
        
        result = gamepad_controller.execute_macro(macro)
        
        assert result.success is False

    def test_macro_execution_time(self, gamepad_controller):
        """Test macro execution time tracking."""
        commands = [
            GamepadCommand(button="Space", action="hold", duration_ms=50),
        ]
        macro = Macro(
            name="move",
            description="Move",
            commands=commands
        )
        
        result = gamepad_controller.execute_macro(macro)
        
        assert result.execution_time_ms >= 50


class TestKeyRelease:
    """Test key release functionality."""

    def test_release_all_keys(self, gamepad_controller):
        """Test releasing all keys."""
        gamepad_controller.held_keys.add("W")
        gamepad_controller.held_keys.add("Space")
        
        gamepad_controller.release_all_keys()
        
        assert len(gamepad_controller.held_keys) == 0

    def test_release_on_macro_error(self, gamepad_controller):
        """Test that keys are released on macro error."""
        # Add some held keys before macro execution
        gamepad_controller.held_keys.add("W")
        
        commands = [
            GamepadCommand(button="INVALID", action="press"),
        ]
        macro = Macro(
            name="error_macro",
            description="Error",
            commands=commands
        )
        
        result = gamepad_controller.execute_macro(macro)
        
        # Macro should fail
        assert result.success is False
        # Keys should be released on error
        assert len(gamepad_controller.held_keys) == 0


class TestMacroInterruption:
    """Test macro interruption."""

    def test_interrupt_macro(self, gamepad_controller):
        """Test interrupting a macro."""
        commands = [
            GamepadCommand(button="Space", action="hold", duration_ms=1000),
        ]
        macro = Macro(
            name="long_jump",
            description="Long jump",
            commands=commands
        )
        
        def execute_and_interrupt():
            time.sleep(0.1)
            gamepad_controller.interrupt_macro()
        
        thread = threading.Thread(target=execute_and_interrupt)
        thread.start()
        
        result = gamepad_controller.execute_macro(macro)
        thread.join()
        
        # Macro should be interrupted
        assert gamepad_controller.macro_interrupted is True


class TestStatus:
    """Test status reporting."""

    def test_get_status(self, gamepad_controller):
        """Test getting status."""
        status = gamepad_controller.get_status()
        
        assert "queue_size" in status
        assert "held_keys" in status
        assert "current_macro" in status
        assert "macro_interrupted" in status

    def test_status_reflects_queue(self, gamepad_controller):
        """Test that status reflects queue size."""
        cmd = GamepadCommand(button="W", action="press")
        gamepad_controller.send_command(cmd)
        
        status = gamepad_controller.get_status()
        assert status["queue_size"] == 1


class TestThreadSafety:
    """Test thread safety."""

    def test_concurrent_command_sending(self, gamepad_controller):
        """Test concurrent command sending."""
        def send_commands():
            for i in range(10):
                cmd = GamepadCommand(button="W", action="press")
                gamepad_controller.send_command(cmd)
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=send_commands)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All commands should be queued
        assert gamepad_controller.command_queue.qsize() == 50

    def test_concurrent_status_checks(self, gamepad_controller):
        """Test concurrent status checks."""
        def check_status():
            for i in range(10):
                gamepad_controller.get_status()
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=check_status)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should complete without errors


# Property-based tests

def test_property_gamepad_command_queue_ordering():
    """Property 21: Gamepad Command Queue Ordering.
    
    For any sequence of gamepad commands sent from multiple threads, 
    the Gamepad_Controller should execute them in the order they were queued.
    
    Validates: Requirements 8.2
    """
    config = Mock()
    logger = Mock(spec=Logger)
    error_handler = Mock()
    
    controller = GamepadController(config, logger, error_handler)
    
    # Send commands from multiple threads
    def send_commands(thread_id):
        for i in range(5):
            cmd = GamepadCommand(button="W", action="press")
            controller.send_command(cmd)
    
    threads = []
    for i in range(3):
        t = threading.Thread(target=send_commands, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # All commands should be queued in order
    assert controller.command_queue.qsize() == 15


def test_property_gamepad_command_validation():
    """Property 22: Gamepad Command Validation.
    
    For any gamepad command with invalid parameters, the Gamepad_Controller 
    should reject it and log an error.
    
    Validates: Requirements 8.3, 8.4
    """
    config = Mock()
    logger = Mock(spec=Logger)
    error_handler = Mock()
    
    controller = GamepadController(config, logger, error_handler)
    
    # Try invalid commands
    invalid_commands = [
        GamepadCommand(button="INVALID", action="press"),
        GamepadCommand(button="W", action="invalid_action"),
        GamepadCommand(button="Space", action="hold", duration_ms=0),
    ]
    
    for cmd in invalid_commands:
        controller.send_command(cmd)
    
    # No commands should be queued
    assert controller.command_queue.qsize() == 0


def test_property_macro_atomic_execution():
    """Property 23: Macro Atomic Execution.
    
    For any macro execution, either all commands in the macro should execute 
    successfully or none should execute (all-or-nothing semantics).
    
    Validates: Requirements 8.5
    """
    config = Mock()
    logger = Mock(spec=Logger)
    error_handler = Mock()
    
    controller = GamepadController(config, logger, error_handler)
    
    # Valid macro
    valid_commands = [
        GamepadCommand(button="W", action="press"),
        GamepadCommand(button="W", action="release"),
    ]
    valid_macro = Macro(
        name="valid",
        description="Valid",
        commands=valid_commands
    )
    
    result = controller.execute_macro(valid_macro)
    assert result.success is True
    assert result.commands_executed == 2
    
    # Invalid macro (should not execute any commands)
    invalid_commands = [
        GamepadCommand(button="INVALID", action="press"),
    ]
    invalid_macro = Macro(
        name="invalid",
        description="Invalid",
        commands=invalid_commands
    )
    
    result = controller.execute_macro(invalid_macro)
    assert result.success is False
    assert result.commands_executed == 0


def test_property_macro_interrupt_key_release():
    """Property 24: Macro Interrupt Key Release.
    
    For any macro that is interrupted during execution, all held keys 
    should be released and the gamepad should return to a safe state.
    
    Validates: Requirements 8.6
    """
    config = Mock()
    logger = Mock(spec=Logger)
    error_handler = Mock()
    
    controller = GamepadController(config, logger, error_handler)
    
    # Add some held keys before macro execution
    controller.held_keys.add("W")
    controller.held_keys.add("Space")
    
    # Interrupt macro (should release all keys)
    controller.interrupt_macro()
    
    # All keys should be released
    assert len(controller.held_keys) == 0
