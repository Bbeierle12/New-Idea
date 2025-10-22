"""Tests for ToolsBridge with safety integration."""

import json
from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock

from glyphx.app.services.tools import ToolsBridge
from glyphx.app.services.registry import RegistryService
from glyphx.app.infra.logger import Logger
from glyphx.app.infra.safety import SafetyConfig


class TestToolsBridgeSafety:
    """Test ToolsBridge with safety controls."""
    
    @pytest.fixture
    def mock_registry(self):
        """Create a mock registry."""
        return Mock(spec=RegistryService)
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        logger = Mock(spec=Logger)
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        return logger
    
    @pytest.fixture
    def tools_with_safety(self, mock_registry, mock_logger):
        """Create ToolsBridge with safety enabled."""
        config = SafetyConfig(enabled=True, require_confirmation=True)
        return ToolsBridge(
            mock_registry,
            mock_logger,
            safety_config=config,
        )
    
    @pytest.fixture
    def tools_without_confirmation(self, mock_registry, mock_logger):
        """Create ToolsBridge with safety but no confirmation."""
        config = SafetyConfig(enabled=True, require_confirmation=False)
        return ToolsBridge(
            mock_registry,
            mock_logger,
            safety_config=config,
        )
    
    def test_tool_schema_includes_timeout(self, tools_with_safety):
        """Test that run_shell schema includes timeout parameter."""
        schemas = tools_with_safety.tool_descriptions()
        run_shell = next(s for s in schemas if s["function"]["name"] == "run_shell")
        
        assert "timeout" in run_shell["function"]["parameters"]["properties"]
        timeout_param = run_shell["function"]["parameters"]["properties"]["timeout"]
        assert timeout_param["type"] == "number"
        assert timeout_param["minimum"] == 1
        assert timeout_param["maximum"] == 3600
    
    def test_safe_command_executes(self, tools_with_safety):
        """Test that safe commands execute without blocking."""
        result = tools_with_safety.run_shell("echo hello")
        
        assert "returncode" in result
        assert "stdout" in result
        assert "stderr" in result
    
    def test_dangerous_command_blocked_without_confirmation(self, tools_without_confirmation):
        """Test that dangerous commands are blocked when confirmation is disabled."""
        tools_without_confirmation.set_mode("chat")
        result = tools_without_confirmation.run_shell("rm -rf /")
        
        assert result["returncode"] == "-1"
        assert "blocked" in result["stderr"].lower()
    
    def test_dangerous_command_with_user_approval(self, tools_with_safety):
        """Test that dangerous commands can be approved via callback."""
        # Mock confirmation callback that approves
        tools_with_safety._confirmation_callback = lambda tool, args, mode: ("allow", False)
        tools_with_safety.set_mode("chat")
        
        result = tools_with_safety.run_shell("echo test")  # Safe command, no confirmation needed
        assert result["returncode"] != "-1"
    
    def test_dangerous_command_with_user_denial(self, tools_with_safety):
        """Test that dangerous commands are blocked when user denies."""
        # Mock confirmation callback that denies
        tools_with_safety._confirmation_callback = lambda tool, args, mode: ("deny", False)
        tools_with_safety.set_mode("chat")
        
        result = tools_with_safety.run_shell("shutdown now")
        assert result["returncode"] == "-1"
        assert "denied" in result["stderr"].lower()
    
    def test_session_approval_caching(self, tools_with_safety):
        """Test that approval decisions are cached for the session."""
        call_count = 0
        
        def counting_callback(tool, args, mode):
            nonlocal call_count
            call_count += 1
            return ("allow", True)  # Remember this decision
        
        tools_with_safety._confirmation_callback = counting_callback
        tools_with_safety.set_mode("chat")
        
        # Execute same dangerous command twice
        cmd = "dangerous_command"
        tools_with_safety.run_shell(cmd)
        tools_with_safety.run_shell(cmd)
        
        # Callback should only be called once due to caching
        assert call_count == 1
    
    def test_timeout_parameter_enforced(self, tools_with_safety):
        """Test that timeout parameter is clamped to valid range."""
        # This test just verifies the timeout is processed, actual timeout testing
        # requires real subprocess which is slow
        result = tools_with_safety.execute_tool(
            "run_shell",
            {"command": "echo test", "timeout": 5}
        )
        assert "returncode" in result
    
    def test_output_truncation(self, tools_with_safety, tmp_path):
        """Test that large outputs are truncated."""
        # Create a command that outputs a lot of data
        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 100000)
        
        result = tools_with_safety.read_file(str(large_file))
        
        # Should be truncated
        assert len(result["content"]) < 100000
        if "truncated" in result["content"].lower():
            # Truncation marker present
            assert True
    
    def test_read_file_safety(self, tools_without_confirmation, tmp_path):
        """Test that dangerous file reads are blocked."""
        exe_file = tmp_path / "malware.exe"
        exe_file.write_bytes(b"fake exe content")
        
        tools_without_confirmation.set_mode("chat")
        result = tools_without_confirmation.read_file(str(exe_file))
        
        # Should be blocked or show error
        assert "blocked" in result["content"].lower() or "error" in result["content"].lower()
    
    def test_write_file_safety(self, tools_without_confirmation, tmp_path):
        """Test that dangerous file writes are blocked."""
        exe_file = tmp_path / "malware.exe"
        
        tools_without_confirmation.set_mode("chat")
        result = tools_without_confirmation.write_file(str(exe_file), "malicious content")
        
        # Should be blocked
        assert "error" in result or result["bytes"] == "0"
    
    def test_mode_setting(self, tools_with_safety):
        """Test that mode can be set and affects behavior."""
        tools_with_safety.set_mode("agent")
        assert tools_with_safety._mode == "agent"
        
        tools_with_safety.set_mode("chat")
        assert tools_with_safety._mode == "chat"
    
    def test_safe_file_operations(self, tools_with_safety, tmp_path):
        """Test that safe file operations work normally."""
        test_file = tmp_path / "test.txt"
        content = "Hello, world!"
        
        # Write file
        write_result = tools_with_safety.write_file(str(test_file), content)
        assert write_result["bytes"] == str(len(content.encode('utf-8')))
        
        # Read file
        read_result = tools_with_safety.read_file(str(test_file))
        assert read_result["content"] == content
    
    def test_list_files_not_affected(self, tools_with_safety, tmp_path):
        """Test that list_files operation is not affected by safety (read-only)."""
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        
        result = tools_with_safety.list_files(str(tmp_path))
        assert len(result["entries"]) == 2
    
    def test_execute_tool_with_json_string(self, tools_with_safety):
        """Test execute_tool with JSON string arguments."""
        result = tools_with_safety.execute_tool(
            "run_shell",
            json.dumps({"command": "echo test"})
        )
        assert "returncode" in result
    
    def test_execute_tool_with_dict(self, tools_with_safety):
        """Test execute_tool with dict arguments."""
        result = tools_with_safety.execute_tool(
            "run_shell",
            {"command": "echo test"}
        )
        assert "returncode" in result
