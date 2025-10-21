"""Tests for session summarizer service."""

from __future__ import annotations

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from glyphx.app.services.session_summarizer import SessionSummarizer
from glyphx.app.infra.history import CommandHistory, CommandRecord


@pytest.fixture
def summarizer():
    """Create a SessionSummarizer instance."""
    return SessionSummarizer()


@pytest.fixture
def command_history():
    """Create a temporary command history."""
    with TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "history.jsonl"
        history = CommandHistory(history_path)
        
        # Add some sample commands
        history.append(CommandRecord(
            command="git status",
            cwd="/home/user/project",
            source="terminal",
            exit_code=0
        ))
        history.append(CommandRecord(
            command="git add .",
            cwd="/home/user/project",
            source="terminal",
            exit_code=0
        ))
        history.append(CommandRecord(
            command="git commit -m 'Update docs'",
            cwd="/home/user/project",
            source="terminal",
            exit_code=0
        ))
        
        yield history


def test_summarizer_initialization():
    """Test that summarizer initializes with default values."""
    summarizer = SessionSummarizer()
    assert summarizer.model == "gemma:300m"
    assert "localhost" in summarizer.client.base_url


def test_summarizer_custom_config():
    """Test summarizer with custom configuration."""
    summarizer = SessionSummarizer(
        base_url="http://example.com/v1",
        model="custom-model"
    )
    assert summarizer.model == "custom-model"
    assert summarizer.client.base_url == "http://example.com/v1"


@pytest.mark.skip(reason="Requires running Ollama with gemma:300m")
def test_summarize_recent(summarizer, command_history):
    """Test summarizing recent commands."""
    summary = summarizer.summarize_recent(command_history, limit=10)
    assert isinstance(summary, str)
    assert len(summary) > 0
    # Summary should mention git operations
    assert any(word in summary.lower() for word in ["git", "commit", "update"])


def test_summarize_recent_empty_history(summarizer):
    """Test summarizing empty history."""
    with TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "empty_history.jsonl"
        empty_history = CommandHistory(history_path)
        
        summary = summarizer.summarize_recent(empty_history)
        assert summary == "No commands executed yet."


@pytest.mark.skip(reason="Requires running Ollama with gemma:300m")
def test_summarize_specific_commands(summarizer):
    """Test summarizing a specific list of commands."""
    commands = [
        "npm install",
        "npm run build",
        "npm test"
    ]
    summary = summarizer.summarize_specific_commands(commands)
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_summarize_specific_commands_empty_list(summarizer):
    """Test summarizing empty command list."""
    summary = summarizer.summarize_specific_commands([])
    assert summary == "No commands to summarize."


def test_summarize_returns_error_message_on_failure(summarizer):
    """Test that summarizer returns error message when service is unavailable."""
    bad_summarizer = SessionSummarizer(base_url="http://localhost:99999/v1")
    
    with TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "history.jsonl"
        history = CommandHistory(history_path)
        history.append(CommandRecord(
            command="test",
            cwd="/tmp",
            source="terminal",
            exit_code=0
        ))
        
        summary = bad_summarizer.summarize_recent(history, timeout=1.0)
        assert summary == "No summary available"


@pytest.mark.skip(reason="Requires running Ollama with gemma:300m")
def test_generate_session_title(summarizer, command_history):
    """Test generating a short session title."""
    title = summarizer.generate_session_title(command_history, limit=5)
    assert isinstance(title, str)
    assert len(title.split()) <= 7  # Should be 3-5 words, but allow some flexibility
