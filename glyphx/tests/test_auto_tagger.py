"""Tests for auto-tagger service."""

from __future__ import annotations

import pytest

from glyphx.app.services.auto_tagger import AutoTagger


@pytest.fixture
def tagger():
    """Create an AutoTagger instance."""
    return AutoTagger()


def test_tagger_initialization():
    """Test that tagger initializes with default values."""
    tagger = AutoTagger()
    assert tagger.model == "gemma:300m"
    assert "localhost" in tagger.client.base_url


def test_tagger_custom_config():
    """Test tagger with custom configuration."""
    tagger = AutoTagger(
        base_url="http://example.com/v1",
        model="custom-model"
    )
    assert tagger.model == "custom-model"
    assert tagger.client.base_url == "http://example.com/v1"


@pytest.mark.skip(reason="Requires running Ollama with gemma:300m")
def test_suggest_tags_from_command(tagger):
    """Test tag suggestion from command."""
    tags = tagger.suggest_tags("docker build -t myapp .", max_tags=3)
    assert isinstance(tags, list)
    assert len(tags) <= 3
    # Expected tags might include: docker, build, container, deployment, etc.
    assert all(isinstance(tag, str) for tag in tags)


@pytest.mark.skip(reason="Requires running Ollama with gemma:300m")
def test_suggest_tags_from_name_and_command(tagger):
    """Test tag suggestion from both name and command."""
    tags = tagger.suggest_from_name_and_command(
        "Deploy to Production",
        "kubectl apply -f deployment.yaml",
        max_tags=3
    )
    assert isinstance(tags, list)
    assert len(tags) <= 3


def test_suggest_tags_returns_empty_on_error(tagger):
    """Test that tagger returns empty list when service is unavailable."""
    bad_tagger = AutoTagger(base_url="http://localhost:99999/v1")
    tags = bad_tagger.suggest_tags("test command", timeout=1.0)
    assert tags == []


@pytest.mark.skip(reason="Requires running Ollama with gemma:300m")
def test_suggest_tags_respects_max_tags(tagger):
    """Test that max_tags parameter is respected."""
    tags = tagger.suggest_tags("git push origin main", max_tags=2)
    assert len(tags) <= 2
