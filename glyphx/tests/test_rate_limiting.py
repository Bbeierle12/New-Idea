"""Tests for LLM rate limiting."""

import time
from unittest.mock import Mock

import pytest
import requests

from glyphx.app.infra.logger import Logger
from glyphx.app.services.llm import ChatMessage, LLMClient
from glyphx.app.services.settings import Settings, SettingsService


def test_rate_limiting_enforced(tmp_path):
    """Test that rate limiting delays requests correctly."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text('{"llm_rate_limit_per_minute": 2}')
    
    logger = Logger(tmp_path / "test.log")
    settings_service = SettingsService(settings_path, logger)
    
    # Update settings to set rate limit and API key
    settings_service.update(api_key="test-key", llm_rate_limit_per_minute="2")
    
    # Create mock session
    mock_session = Mock(spec=requests.Session)
    mock_response = Mock()
    mock_response.json.return_value = {
        "id": "test",
        "choices": [{"message": {"role": "assistant", "content": "test"}}],
        "usage": {"total_tokens": 10},
    }
    mock_response.raise_for_status = Mock()
    mock_session.post.return_value = mock_response
    
    client = LLMClient(settings_service, logger, session=mock_session, timeout=5.0)
    
    messages = [ChatMessage(role="user", content="test")]
    
    # First two calls should succeed quickly
    start = time.time()
    client.chat(messages)
    client.chat(messages)
    elapsed_fast = time.time() - start
    
    # Third call should be delayed due to rate limit
    start = time.time()
    client.chat(messages)
    elapsed_slow = time.time() - start
    
    # The third call should take significantly longer (waiting for window to clear)
    assert elapsed_slow > 1.0, "Rate limiting should have caused a delay"
    assert elapsed_fast < 1.0, "First two calls should be fast"


def test_rate_limiting_disabled(tmp_path):
    """Test that rate limiting is disabled when limit is None."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text('{}')
    
    logger = Logger(tmp_path / "test.log")
    settings_service = SettingsService(settings_path, logger)
    settings_service.update(api_key="test-key")
    
    # Create mock session
    mock_session = Mock(spec=requests.Session)
    mock_response = Mock()
    mock_response.json.return_value = {
        "id": "test",
        "choices": [{"message": {"role": "assistant", "content": "test"}}],
        "usage": {"total_tokens": 10},
    }
    mock_response.raise_for_status = Mock()
    mock_session.post.return_value = mock_response
    
    client = LLMClient(settings_service, logger, session=mock_session, timeout=5.0)
    
    messages = [ChatMessage(role="user", content="test")]
    
    # Multiple calls should succeed quickly without rate limiting
    start = time.time()
    for _ in range(5):
        client.chat(messages)
    elapsed = time.time() - start
    
    # Should complete quickly since rate limiting is disabled
    assert elapsed < 1.0, "Calls should be fast without rate limiting"
