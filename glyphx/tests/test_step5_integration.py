"""
Step 5 Phase 1: Integration Tests (Backend Only)
Tests complete user workflows including settings persistence
and safety feature integration without GUI dependencies.
"""

import json
from pathlib import Path
import pytest

from glyphx.app.services.settings import SettingsService
from glyphx.app.infra.logger import Logger
from glyphx.app.infra.safety import SafetyValidator


class TestSettingsServiceIntegration:
    """Integration tests for Settings service with safety features."""
    
    def test_settings_save_and_load_all_fields(self, tmp_path: Path) -> None:
        """Test that all settings fields (LLM + Safety) persist correctly."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        service = SettingsService(config_file, logger)
        
        # Update all settings
        service.update(
            api_key="test-key-12345",
            model="gpt-4o",
            llm_timeout=90.0,
            tool_output_max_bytes=16000,
            context_truncation_enabled=False,
            default_mode="agent"
        )
        
        # Verify settings were saved
        settings = service.get()
        assert settings.api_key == "test-key-12345"
        assert settings.model == "gpt-4o"
        assert settings.llm_timeout == 90.0
        assert settings.tool_output_max_bytes == 16000
        assert settings.context_truncation_enabled is False
        assert settings.default_mode == "agent"
        
        # Verify persistence - reload from file
        logger2 = Logger(log_file)
        service2 = SettingsService(config_file, logger2)
        settings2 = service2.get()
        assert settings2.tool_output_max_bytes == 16000
        assert settings2.context_truncation_enabled is False
        assert settings2.default_mode == "agent"
    
    def test_settings_reset_to_defaults(self, tmp_path: Path) -> None:
        """Test that safety settings can be reset to defaults."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        service = SettingsService(config_file, logger)
        
        # Set non-default values
        service.update(
            tool_output_max_bytes=50000,
            context_truncation_enabled=False,
            default_mode="agent"
        )
        
        # Reset to defaults
        service.update(
            tool_output_max_bytes=8000,
            context_truncation_enabled=True,
            default_mode="chat"
        )
        
        # Verify reset
        settings = service.get()
        assert settings.tool_output_max_bytes == 8000
        assert settings.context_truncation_enabled is True
        assert settings.default_mode == "chat"


class TestSafetyIntegrationWorkflow:
    """Integration tests for complete safety workflows."""
    
    def test_truncation_with_validator(self, tmp_path: Path) -> None:
        """Test that SafetyValidator truncation works correctly."""
        # Create safety validator with workspace
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        # Import SafetyConfig
        from glyphx.app.infra.safety import SafetyConfig
        
        # Create validator with specific config
        config = SafetyConfig(max_output_bytes=5000)
        validator = SafetyValidator(config)
        
        # Create large output
        large_output = "x" * 10000
        
        # Truncate
        truncated = validator.truncate_output(large_output)
        
        # Verify truncation happened
        assert len(truncated) < 10000
        assert "[Output truncated - exceeded maximum size]" in truncated
    
    def test_settings_persistence_across_restarts(self, tmp_path: Path) -> None:
        """Test that safety settings persist across application restarts."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        
        # First instance: save settings
        service1 = SettingsService(config_file, logger)
        service1.update(
            tool_output_max_bytes=25000,
            context_truncation_enabled=True,
            default_mode="chat"
        )
        
        # Verify file was written
        assert config_file.exists()
        
        # Second instance: load settings
        logger2 = Logger(log_file)
        service2 = SettingsService(config_file, logger2)
        settings2 = service2.get()
        
        assert settings2.tool_output_max_bytes == 25000
        assert settings2.context_truncation_enabled is True
        assert settings2.default_mode == "chat"
        
        # Third instance: modify and verify
        service2.update(tool_output_max_bytes=30000)
        
        logger3 = Logger(log_file)
        service3 = SettingsService(config_file, logger3)
        settings3 = service3.get()
        
        assert settings3.tool_output_max_bytes == 30000


class TestEndToEndUserWorkflow:
    """Test complete user workflows from start to finish (backend only)."""
    
    def test_new_user_workflow(self, tmp_path: Path) -> None:
        """Test complete workflow for a new user setting up GlyphX."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        
        # Step 1: User starts with no config (defaults)
        service = SettingsService(config_file, logger)
        settings = service.get()
        
        assert settings.tool_output_max_bytes == 8000
        assert settings.context_truncation_enabled is True
        assert settings.default_mode == "chat"
        
        # Step 2: User opens settings and configures API
        service.update(
            api_key="sk-test123",
            model="gpt-4o-mini",
            base_url="https://api.openai.com/v1"
        )
        
        # Step 3: User adjusts safety settings for their use case
        service.update(
            tool_output_max_bytes=16000,
            context_truncation_enabled=True
        )
        
        # Verify all settings are configured
        settings = service.get()
        assert settings.api_key == "sk-test123"
        assert settings.tool_output_max_bytes == 16000
        assert settings.default_mode == "chat"
    
    def test_power_user_workflow(self, tmp_path: Path) -> None:
        """Test workflow for power user with custom configurations."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        
        # Power user wants higher limits and agent mode by default
        service = SettingsService(config_file, logger)
        service.update(
            tool_output_max_bytes=50000,
            context_truncation_enabled=True,
            default_mode="agent",
            api_key="sk-poweruser",
            model="gpt-4o"
        )
        
        # Verify settings persisted
        settings = service.get()
        assert settings.tool_output_max_bytes == 50000
        assert settings.default_mode == "agent"
        assert settings.api_key == "sk-poweruser"
    
    def test_team_safe_defaults_workflow(self, tmp_path: Path) -> None:
        """Test workflow for team using safe shared defaults."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        
        # Team administrator sets safe defaults
        admin_service = SettingsService(config_file, logger)
        admin_service.update(
            tool_output_max_bytes=8000,
            context_truncation_enabled=True,
            default_mode="chat",
            base_url="https://api.company.com/v1"
        )
        
        # Save config to file (already done by update)
        assert config_file.exists()
        
        # Team member loads the config
        logger2 = Logger(log_file)
        member_service = SettingsService(config_file, logger2)
        settings = member_service.get()
        
        # Verify safe defaults
        assert settings.tool_output_max_bytes == 8000
        assert settings.context_truncation_enabled is True
        assert settings.default_mode == "chat"
        assert settings.base_url == "https://api.company.com/v1"


class TestErrorHandlingIntegration:
    """Integration tests for error handling and edge cases."""
    
    def test_invalid_settings_values_rejected(self, tmp_path: Path) -> None:
        """Test that invalid settings values are rejected with clear errors."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        service = SettingsService(config_file, logger)
        
        # Try to set output bytes too low
        with pytest.raises(ValueError):
            service.update(tool_output_max_bytes=500)
        
        # Try to set output bytes too high
        with pytest.raises(ValueError):
            service.update(tool_output_max_bytes=200000)
        
        # Try to set invalid mode
        with pytest.raises(ValueError):
            service.update(default_mode="superuser")
    
    def test_corrupted_config_uses_defaults(self, tmp_path: Path) -> None:
        """Test that corrupted config file falls back to defaults."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        
        # Write corrupted JSON
        config_file.write_text("{invalid json content")
        
        # Service should handle corruption and use defaults
        service = SettingsService(config_file, logger)
        settings = service.get()
        
        # Should have default values
        assert settings.tool_output_max_bytes == 8000
        assert settings.context_truncation_enabled is True
        assert settings.default_mode == "chat"
    
    def test_missing_safety_fields_use_defaults(self, tmp_path: Path) -> None:
        """Test that missing safety fields in old configs use defaults."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        
        # Write old config without safety fields
        old_config = {
            "api_key": "sk-old",
            "model": "gpt-4",
            "base_url": "https://api.openai.com/v1"
        }
        config_file.write_text(json.dumps(old_config))
        
        # Load with service
        service = SettingsService(config_file, logger)
        settings = service.get()
        
        # Old fields preserved
        assert settings.api_key == "sk-old"
        assert settings.model == "gpt-4"
        
        # New fields get defaults
        assert settings.tool_output_max_bytes == 8000
        assert settings.context_truncation_enabled is True
        assert settings.default_mode == "chat"


class TestSafetySettingsValidation:
    """Test safety settings validation rules."""
    
    def test_output_bytes_boundary_values(self, tmp_path: Path) -> None:
        """Test boundary values for tool_output_max_bytes."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        service = SettingsService(config_file, logger)
        
        # Minimum valid value
        service.update(tool_output_max_bytes=1000)
        assert service.get().tool_output_max_bytes == 1000
        
        # Maximum valid value
        service.update(tool_output_max_bytes=100000)
        assert service.get().tool_output_max_bytes == 100000
        
        # Middle values
        service.update(tool_output_max_bytes=50000)
        assert service.get().tool_output_max_bytes == 50000
    
    def test_truncation_toggle(self, tmp_path: Path) -> None:
        """Test truncation can be enabled and disabled."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        service = SettingsService(config_file, logger)
        
        # Enable truncation
        service.update(context_truncation_enabled=True)
        assert service.get().context_truncation_enabled is True
        
        # Disable truncation
        service.update(context_truncation_enabled=False)
        assert service.get().context_truncation_enabled is False
    
    def test_mode_switching(self, tmp_path: Path) -> None:
        """Test mode can be switched between chat and agent."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        service = SettingsService(config_file, logger)
        
        # Set to chat mode
        service.update(default_mode="chat")
        assert service.get().default_mode == "chat"
        
        # Set to agent mode
        service.update(default_mode="agent")
        assert service.get().default_mode == "agent"
