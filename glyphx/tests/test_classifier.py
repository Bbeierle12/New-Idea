"""Tests for command classifier service."""

from __future__ import annotations

import pytest

from glyphx.app.services.classifier import CommandClassifier


@pytest.fixture
def classifier():
    """Create a CommandClassifier instance."""
    return CommandClassifier()


def test_classifier_initialization():
    """Test that classifier initializes with default values."""
    classifier = CommandClassifier()
    assert classifier.model == "gemma:300m"
    assert "localhost" in classifier.client.base_url


def test_classifier_custom_config():
    """Test classifier with custom configuration."""
    classifier = CommandClassifier(
        base_url="http://example.com/v1",
        model="custom-model"
    )
    assert classifier.model == "custom-model"
    assert classifier.client.base_url == "http://example.com/v1"


@pytest.mark.skip(reason="Requires running Ollama with gemma:300m")
def test_classify_shell_command(classifier):
    """Test classification of shell commands."""
    result = classifier.classify("ls -la")
    assert result == "shell"


@pytest.mark.skip(reason="Requires running Ollama with gemma:300m")
def test_classify_glyph_command(classifier):
    """Test classification of glyph-related commands."""
    result = classifier.classify("run my deployment script")
    assert result in ("glyph", "unclear")


@pytest.mark.skip(reason="Requires running Ollama with gemma:300m")
def test_classify_file_operation(classifier):
    """Test classification of file operations."""
    result = classifier.classify("read config.json")
    assert result == "file_operation"


@pytest.mark.skip(reason="Requires running Ollama with gemma:300m")
def test_classify_chat(classifier):
    """Test classification of conversational queries."""
    result = classifier.classify("what is the weather like?")
    assert result == "chat"


def test_classify_returns_unclear_on_error(classifier):
    """Test that classifier returns 'unclear' when service is unavailable."""
    # Using a bad URL to force an error
    bad_classifier = CommandClassifier(base_url="http://localhost:99999/v1")
    result = bad_classifier.classify("test command", timeout=1.0)
    assert result == "unclear"


@pytest.mark.skip(reason="Requires running Ollama with gemma:300m")
def test_is_available(classifier):
    """Test availability check."""
    # This will only pass if Ollama is running with gemma:300m
    result = classifier.is_available()
    assert isinstance(result, bool)
