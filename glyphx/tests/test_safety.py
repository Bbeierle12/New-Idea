"""Tests for safety validation module."""

from pathlib import Path
import pytest
from glyphx.app.infra.safety import SafetyConfig, SafetyValidator


class TestSafetyValidator:
    """Test cases for SafetyValidator."""
    
    def test_validate_allowed_shell_command(self):
        """Test that allowed commands pass validation."""
        config = SafetyConfig()
        validator = SafetyValidator(config)
        
        # Test allowed commands
        is_safe, reason = validator.validate_shell_command("ls -la")
        assert is_safe is True
        
        is_safe, reason = validator.validate_shell_command("git status")
        assert is_safe is True
        
        is_safe, reason = validator.validate_shell_command("python script.py")
        assert is_safe is True
    
    def test_validate_denied_shell_command(self):
        """Test that dangerous commands are denied."""
        config = SafetyConfig()
        validator = SafetyValidator(config)
        
        # Test denied patterns
        is_safe, reason = validator.validate_shell_command("rm -rf /")
        assert is_safe is False
        assert "denied pattern" in reason.lower()
        
        is_safe, reason = validator.validate_shell_command("shutdown now")
        assert is_safe is False
        
        is_safe, reason = validator.validate_shell_command("format c:")
        assert is_safe is False
    
    def test_validate_unlisted_shell_command(self):
        """Test that unlisted commands are denied when allow list is active."""
        config = SafetyConfig()
        validator = SafetyValidator(config)
        
        is_safe, reason = validator.validate_shell_command("dangerous_command")
        assert is_safe is False
        assert "not in allowed list" in reason.lower()
    
    def test_validate_empty_command(self):
        """Test that empty commands are rejected."""
        config = SafetyConfig()
        validator = SafetyValidator(config)
        
        is_safe, reason = validator.validate_shell_command("")
        assert is_safe is False
        assert "empty" in reason.lower()
    
    def test_validate_file_path_allowed(self, tmp_path):
        """Test that allowed file paths pass validation."""
        config = SafetyConfig(file_jail_dir=tmp_path)
        validator = SafetyValidator(config)
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        is_safe, reason = validator.validate_file_path(test_file, write=False)
        assert is_safe is True
    
    def test_validate_file_path_outside_jail(self, tmp_path):
        """Test that paths outside jail directory are denied."""
        jail_dir = tmp_path / "jail"
        jail_dir.mkdir()
        
        config = SafetyConfig(file_jail_dir=jail_dir)
        validator = SafetyValidator(config)
        
        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("test")
        
        is_safe, reason = validator.validate_file_path(outside_file, write=False)
        assert is_safe is False
        assert "outside jail" in reason.lower()
    
    def test_validate_file_path_denied_extension(self, tmp_path):
        """Test that dangerous file extensions are denied for writes."""
        config = SafetyConfig()
        validator = SafetyValidator(config)
        
        exe_file = tmp_path / "malware.exe"
        
        is_safe, reason = validator.validate_file_path(exe_file, write=True)
        assert is_safe is False
        # Could be caught by denied pattern or extension check
        assert ("denied pattern" in reason.lower() or "not allowed" in reason.lower())
    
    def test_validate_file_path_too_large(self, tmp_path):
        """Test that files exceeding size limit are denied."""
        config = SafetyConfig(file_max_size_bytes=100)
        validator = SafetyValidator(config)
        
        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 1000)  # Create file larger than 100 bytes
        
        is_safe, reason = validator.validate_file_path(large_file, write=False)
        assert is_safe is False
        assert "too large" in reason.lower()
    
    def test_truncate_output(self):
        """Test output truncation."""
        config = SafetyConfig(max_output_bytes=50)
        validator = SafetyValidator(config)
        
        short_output = "Short output"
        assert validator.truncate_output(short_output) == short_output
        
        long_output = "x" * 1000
        truncated = validator.truncate_output(long_output)
        assert len(truncated) < len(long_output)
        assert "truncated" in truncated.lower()
    
    def test_safety_disabled(self):
        """Test that validation is bypassed when safety is disabled."""
        config = SafetyConfig(enabled=False)
        validator = SafetyValidator(config)
        
        # Dangerous command should pass when disabled
        is_safe, reason = validator.validate_shell_command("rm -rf /")
        assert is_safe is True
        assert "disabled" in reason.lower()
        
        # Dangerous path should pass when disabled
        is_safe, reason = validator.validate_file_path(Path("/etc/passwd"), write=True)
        assert is_safe is True
        assert "disabled" in reason.lower()
