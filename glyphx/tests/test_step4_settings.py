"""Tests for Step 4: Configurable truncation and safety settings."""

import pytest
import tempfile
from pathlib import Path

from glyphx.app.services.settings import Settings, SettingsService
from glyphx.app.infra.logger import Logger


class TestSafetySettings:
    """Tests for the new safety-related settings."""

    def test_default_safety_settings(self):
        """Test that default safety settings are correct."""
        settings = Settings()
        assert settings.tool_output_max_bytes == 8000
        assert settings.context_truncation_enabled is True
        assert settings.default_mode == "chat"

    def test_safety_settings_persistence(self, tmp_path):
        """Test that safety settings persist correctly."""
        settings_path = tmp_path / "settings.json"
        logger = Logger(tmp_path / "log.jsonl")
        
        service = SettingsService(settings_path, logger)
        
        # Update safety settings
        service.update(
            tool_output_max_bytes=16000,
            context_truncation_enabled=False,
            default_mode="agent"
        )
        
        # Reload from disk
        service2 = SettingsService(settings_path, logger)
        settings = service2.get()
        
        assert settings.tool_output_max_bytes == 16000
        assert settings.context_truncation_enabled is False
        assert settings.default_mode == "agent"

    def test_tool_output_max_bytes_validation(self, tmp_path):
        """Test validation of tool_output_max_bytes setting."""
        settings_path = tmp_path / "settings.json"
        logger = Logger(tmp_path / "log.jsonl")
        service = SettingsService(settings_path, logger)
        
        # Valid value should work
        service.update(tool_output_max_bytes=5000)
        assert service.get().tool_output_max_bytes == 5000
        
        # Too small should fail
        with pytest.raises(ValueError, match="at least 1000"):
            service.update(tool_output_max_bytes=500)
        
        # Too large should fail
        with pytest.raises(ValueError, match="cannot exceed 100000"):
            service.update(tool_output_max_bytes=150000)

    def test_default_mode_validation(self, tmp_path):
        """Test validation of default_mode setting."""
        settings_path = tmp_path / "settings.json"
        logger = Logger(tmp_path / "log.jsonl")
        service = SettingsService(settings_path, logger)
        
        # Valid modes should work
        service.update(default_mode="chat")
        assert service.get().default_mode == "chat"
        
        service.update(default_mode="agent")
        assert service.get().default_mode == "agent"
        
        # Invalid mode should fail
        with pytest.raises(ValueError, match="must be 'chat' or 'agent'"):
            service.update(default_mode="invalid")

    def test_context_truncation_enabled_boolean(self, tmp_path):
        """Test that context_truncation_enabled is properly converted to boolean."""
        settings_path = tmp_path / "settings.json"
        logger = Logger(tmp_path / "log.jsonl")
        service = SettingsService(settings_path, logger)
        
        # Test boolean values
        service.update(context_truncation_enabled=True)
        assert service.get().context_truncation_enabled is True
        
        service.update(context_truncation_enabled=False)
        assert service.get().context_truncation_enabled is False

    def test_safety_settings_from_dict(self):
        """Test loading safety settings from dictionary."""
        payload = {
            "api_key": "test-key",
            "model": "gpt-4",
            "tool_output_max_bytes": 12000,
            "context_truncation_enabled": False,
            "default_mode": "agent"
        }
        
        settings = Settings.from_dict(payload)
        
        assert settings.tool_output_max_bytes == 12000
        assert settings.context_truncation_enabled is False
        assert settings.default_mode == "agent"

    def test_safety_settings_to_dict(self):
        """Test serializing safety settings to dictionary."""
        settings = Settings(
            api_key="test-key",
            tool_output_max_bytes=10000,
            context_truncation_enabled=True,
            default_mode="chat"
        )
        
        result = settings.to_dict()
        
        assert result["tool_output_max_bytes"] == 10000
        assert result["context_truncation_enabled"] is True
        assert result["default_mode"] == "chat"

    def test_backward_compatibility(self):
        """Test that settings without new fields still work."""
        payload = {
            "api_key": "test-key",
            "model": "gpt-4",
            # No safety settings - should use defaults
        }
        
        settings = Settings.from_dict(payload)
        
        # Should have default values
        assert settings.tool_output_max_bytes == 8000
        assert settings.context_truncation_enabled is True
        assert settings.default_mode == "chat"

    def test_mixed_settings_update(self, tmp_path):
        """Test updating safety settings alongside other settings."""
        settings_path = tmp_path / "settings.json"
        logger = Logger(tmp_path / "log.jsonl")
        service = SettingsService(settings_path, logger)
        
        # Update both standard and safety settings
        service.update(
            model="gpt-4o",
            llm_timeout=120.0,
            tool_output_max_bytes=20000,
            default_mode="agent"
        )
        
        settings = service.get()
        assert settings.model == "gpt-4o"
        assert settings.llm_timeout == 120.0
        assert settings.tool_output_max_bytes == 20000
        assert settings.default_mode == "agent"

    def test_extreme_values(self, tmp_path):
        """Test edge cases for truncation settings."""
        settings_path = tmp_path / "settings.json"
        logger = Logger(tmp_path / "log.jsonl")
        service = SettingsService(settings_path, logger)
        
        # Minimum valid value
        service.update(tool_output_max_bytes=1000)
        assert service.get().tool_output_max_bytes == 1000
        
        # Maximum valid value
        service.update(tool_output_max_bytes=100000)
        assert service.get().tool_output_max_bytes == 100000

    def test_invalid_mode_doesnt_override(self, tmp_path):
        """Test that invalid mode doesn't override existing valid mode."""
        settings_path = tmp_path / "settings.json"
        logger = Logger(tmp_path / "log.jsonl")
        service = SettingsService(settings_path, logger)
        
        # Set valid mode
        service.update(default_mode="agent")
        assert service.get().default_mode == "agent"
        
        # Try to set invalid mode (should fail)
        with pytest.raises(ValueError):
            service.update(default_mode="invalid")
        
        # Original valid mode should be unchanged
        assert service.get().default_mode == "agent"
