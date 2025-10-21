"""Tests for terminal panel functionality."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from glyphx.app.gui import TerminalPanel
from glyphx.app.infra.history import CommandHistory
from glyphx.app.infra.logger import Logger
from glyphx.app.infra.worker import Worker
from glyphx.app.services.tools import ToolsBridge


@pytest.fixture
def mock_tools() -> Mock:
    """Create a mock ToolsBridge."""
    tools = Mock(spec=ToolsBridge)
    tools.run_shell.return_value = {
        "label": "shell",
        "returncode": "0",
        "stdout": "test output\n",
        "stderr": "",
    }
    return tools


@pytest.fixture
def mock_worker() -> Mock:
    """Create a mock Worker."""
    worker = Mock(spec=Worker)
    # Make submit immediately call the callback with the job result
    def submit_side_effect(job, description=None, callback=None):
        if callback:
            result = job()
            callback(result)
    worker.submit.side_effect = submit_side_effect
    return worker


@pytest.fixture
def mock_logger() -> Mock:
    """Create a mock Logger."""
    return Mock(spec=Logger)


@pytest.fixture
def mock_history(tmp_path: Path) -> CommandHistory:
    """Create a real CommandHistory with temporary storage."""
    return CommandHistory(tmp_path / "history.jsonl")


@pytest.fixture
def terminal_panel(
    mock_tools: Mock,
    mock_worker: Mock,
    mock_logger: Mock,
    mock_history: CommandHistory,
) -> TerminalPanel:
    """Create a TerminalPanel for testing."""
    root = tk.Tk()
    try:
        panel = TerminalPanel(
            root,
            mock_tools,
            mock_worker,
            mock_logger,
            mock_history,
        )
        yield panel
    finally:
        root.destroy()


def test_terminal_panel_initialization(terminal_panel: TerminalPanel) -> None:
    """Test that terminal panel initializes correctly."""
    assert terminal_panel._cwd_var.get() != ""
    assert not terminal_panel._is_running
    assert terminal_panel._history_index == -1


def test_terminal_clear_output(terminal_panel: TerminalPanel) -> None:
    """Test clearing terminal output."""
    # Add some text first
    terminal_panel._append_text("test content\n")
    
    # Clear it
    terminal_panel._clear_output()
    
    # Output should be empty except for prompt
    content = terminal_panel._output.get("1.0", "end")
    assert "test content" not in content


def test_terminal_execute_command(
    terminal_panel: TerminalPanel,
    mock_tools: Mock,
    mock_worker: Mock,
    mock_history: CommandHistory,
) -> None:
    """Test executing a command."""
    # Set up command
    terminal_panel._input.insert(0, "echo test")
    
    # Execute
    terminal_panel._on_execute()
    
    # Verify command was executed via tools
    mock_tools.run_shell.assert_called_once()
    call_args = mock_tools.run_shell.call_args
    assert call_args[0][0] == "echo test"
    
    # Verify worker was used
    assert mock_worker.submit.called
    
    # Verify history was updated
    records = mock_history.tail()
    assert len(records) >= 1
    assert records[-1].command == "echo test"
    assert records[-1].source == "terminal"


def test_terminal_cd_command(terminal_panel: TerminalPanel, tmp_path: Path) -> None:
    """Test built-in cd command."""
    # Set up cd command to existing directory
    terminal_panel._input.insert(0, f"cd {tmp_path}")
    
    # Execute
    terminal_panel._on_execute()
    
    # Verify working directory changed
    assert terminal_panel._cwd_var.get() == str(tmp_path)


def test_terminal_clear_command(terminal_panel: TerminalPanel) -> None:
    """Test built-in clear command."""
    # Add some content
    terminal_panel._append_text("test content\n")
    
    # Execute clear
    terminal_panel._input.insert(0, "clear")
    terminal_panel._on_execute()
    
    # Output should be cleared
    content = terminal_panel._output.get("1.0", "end")
    assert "test content" not in content


def test_terminal_empty_command(
    terminal_panel: TerminalPanel,
    mock_tools: Mock,
) -> None:
    """Test that empty commands are ignored."""
    # Execute without entering a command
    terminal_panel._on_execute()
    
    # Verify nothing was executed
    mock_tools.run_shell.assert_not_called()


def test_terminal_command_history_navigation(
    mock_tools: Mock,
    mock_worker: Mock,
    mock_logger: Mock,
    mock_history: CommandHistory,
) -> None:
    """Test navigating command history with arrow keys."""
    # Add some commands to history
    mock_history.append("terminal", "command1")
    mock_history.append("terminal", "command2")
    mock_history.append("terminal", "command3")
    
    # Create terminal panel after adding history
    root = tk.Tk()
    try:
        terminal_panel = TerminalPanel(
            root,
            mock_tools,
            mock_worker,
            mock_logger,
            mock_history,
        )
        
        # Navigate up (most recent)
        terminal_panel._history_prev()
        assert terminal_panel._input.get() == "command3"
        
        # Navigate up again
        terminal_panel._history_prev()
        assert terminal_panel._input.get() == "command2"
        
        # Navigate down
        terminal_panel._history_next()
        assert terminal_panel._input.get() == "command3"
        
        # Navigate down to clear
        terminal_panel._history_next()
        assert terminal_panel._input.get() == ""
    finally:
        root.destroy()


def test_terminal_command_error(
    terminal_panel: TerminalPanel,
    mock_tools: Mock,
    mock_worker: Mock,
) -> None:
    """Test handling command errors."""
    # Make tools return an error
    mock_tools.run_shell.return_value = {
        "label": "error",
        "returncode": "1",
        "stdout": "",
        "stderr": "command not found\n",
    }
    
    # Mock worker to execute synchronously
    def submit_error(job, description=None, callback=None):
        if callback:
            result = job()
            callback(result)
    mock_worker.submit.side_effect = submit_error
    
    # Execute command
    terminal_panel._input.insert(0, "invalid_command")
    terminal_panel._on_execute()
    
    # Force UI update
    terminal_panel.update_idletasks()
    
    # Verify error is displayed
    content = terminal_panel._output.get("1.0", "end")
    assert "command not found" in content or "returncode" in content.lower()


def test_terminal_set_running_state(terminal_panel: TerminalPanel) -> None:
    """Test that running state disables input."""
    # Set running
    terminal_panel._set_running(True)
    assert terminal_panel._is_running
    assert str(terminal_panel._input.cget("state")) == "disabled"
    assert str(terminal_panel._run_button.cget("state")) == "disabled"
    
    # Set not running
    terminal_panel._set_running(False)
    assert not terminal_panel._is_running
    assert str(terminal_panel._input.cget("state")) == "normal"
    assert str(terminal_panel._run_button.cget("state")) == "normal"


def test_terminal_append_text_with_tags(terminal_panel: TerminalPanel) -> None:
    """Test appending text with different tags."""
    terminal_panel._append_text("stdout text", "stdout")
    terminal_panel._append_text("stderr text", "stderr")
    terminal_panel._append_text("error text", "error")
    
    content = terminal_panel._output.get("1.0", "end")
    assert "stdout text" in content
    assert "stderr text" in content
    assert "error text" in content


def test_terminal_working_directory_validation(terminal_panel: TerminalPanel) -> None:
    """Test that working directory is validated."""
    # Try to cd to non-existent directory
    terminal_panel._input.insert(0, "cd /nonexistent/path/that/does/not/exist")
    terminal_panel._on_execute()
    
    # Verify error message appears
    content = terminal_panel._output.get("1.0", "end")
    assert "cd:" in content.lower() or "not a directory" in content.lower()


@pytest.mark.parametrize(
    "command,expected_in_output",
    [
        ("echo hello", "hello"),
        ("python --version", "Python"),
        ("dir", "."),
    ],
)
def test_terminal_various_commands(
    terminal_panel: TerminalPanel,
    mock_tools: Mock,
    mock_worker: Mock,
    command: str,
    expected_in_output: str,
) -> None:
    """Test various command types execute correctly."""
    mock_tools.run_shell.return_value = {
        "label": "shell",
        "returncode": "0",
        "stdout": expected_in_output + "\n",
        "stderr": "",
    }
    
    # Mock worker to execute synchronously
    def submit_sync(job, description=None, callback=None):
        if callback:
            result = job()
            callback(result)
    mock_worker.submit.side_effect = submit_sync
    
    terminal_panel._input.insert(0, command)
    terminal_panel._on_execute()
    
    # Force UI update
    terminal_panel.update_idletasks()
    
    content = terminal_panel._output.get("1.0", "end")
    assert expected_in_output in content
