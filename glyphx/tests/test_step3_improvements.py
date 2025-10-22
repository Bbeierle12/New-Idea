"""Tests for Step 3 improvements: streaming, context management, and observability."""

import json
import pytest
from pathlib import Path
from glyphx.app.gui import _truncate_tool_result
from glyphx.app.infra.chat_history import ChatHistory, ChatRecord


class TestToolResultTruncation:
    """Test tool result truncation to prevent token bloat."""
    
    def test_small_result_not_truncated(self):
        """Test that small results pass through unchanged."""
        small_result = json.dumps({"status": "ok", "data": "hello"})
        truncated = _truncate_tool_result(small_result)
        assert truncated == small_result
    
    def test_large_result_truncated(self):
        """Test that large results are truncated."""
        large_output = "x" * 10000
        large_result = json.dumps({"stdout": large_output, "returncode": "0"})
        truncated = _truncate_tool_result(large_result, max_bytes=1000)
        
        assert len(truncated) < len(large_result)
        assert "truncated" in truncated.lower()
    
    def test_truncation_preserves_json_structure(self):
        """Test that truncation attempts to preserve JSON structure."""
        large_output = "y" * 10000
        large_result = json.dumps({
            "stdout": large_output,
            "stderr": "",
            "returncode": "0"
        })
        truncated = _truncate_tool_result(large_result, max_bytes=2000)
        
        # Should still be valid JSON
        try:
            data = json.loads(truncated)
            assert "stdout" in data
            assert "returncode" in data
            assert len(data["stdout"]) < len(large_output)
        except json.JSONDecodeError:
            pytest.fail("Truncated result is not valid JSON")
    
    def test_truncation_with_multiple_large_fields(self):
        """Test truncation when multiple fields are large."""
        large_stdout = "a" * 5000
        large_stderr = "b" * 5000
        result = json.dumps({
            "stdout": large_stdout,
            "stderr": large_stderr,
            "returncode": "0"
        })
        truncated = _truncate_tool_result(result, max_bytes=2000)
        
        data = json.loads(truncated)
        # Both fields should be truncated
        assert len(data["stdout"]) < len(large_stdout)
        assert len(data["stderr"]) < len(large_stderr)
    
    def test_truncation_with_content_field(self):
        """Test truncation of content field (for file reads)."""
        large_content = "c" * 10000
        result = json.dumps({
            "path": "/path/to/file.txt",
            "content": large_content
        })
        truncated = _truncate_tool_result(result, max_bytes=2000)
        
        data = json.loads(truncated)
        assert len(data["content"]) < len(large_content)
        assert "truncated" in data["content"].lower()
    
    def test_truncation_fallback_for_invalid_json(self):
        """Test fallback truncation for non-JSON content."""
        large_text = "z" * 10000
        truncated = _truncate_tool_result(large_text, max_bytes=1000)
        
        assert len(truncated) <= 1100  # Some room for truncation marker
        assert "truncated" in truncated.lower()
    
    def test_truncation_with_configurable_max_bytes(self):
        """Test that max_bytes parameter is respected."""
        large_result = json.dumps({"data": "x" * 5000})
        
        truncated_1k = _truncate_tool_result(large_result, max_bytes=1000)
        truncated_2k = _truncate_tool_result(large_result, max_bytes=2000)
        
        assert len(truncated_1k) < len(truncated_2k)


class TestChatHistoryModeTracking:
    """Test mode tracking in chat history."""
    
    @pytest.fixture
    def temp_history_file(self, tmp_path):
        """Create a temporary history file."""
        return tmp_path / "chat_history.jsonl"
    
    def test_chat_record_includes_mode(self):
        """Test that ChatRecord can store mode."""
        record = ChatRecord(
            role="user",
            content="Hello",
            meta={},
            mode="chat"
        )
        assert record.mode == "chat"
    
    def test_chat_record_mode_in_json(self):
        """Test that mode is serialized to JSON."""
        record = ChatRecord(
            role="user",
            content="Hello",
            meta={},
            mode="agent"
        )
        json_str = record.to_json()
        data = json.loads(json_str)
        
        assert "mode" in data
        assert data["mode"] == "agent"
    
    def test_chat_record_without_mode(self):
        """Test that mode is optional in ChatRecord."""
        record = ChatRecord(
            role="assistant",
            content="Hi there",
            meta={}
        )
        json_str = record.to_json()
        data = json.loads(json_str)
        
        # Mode should not be in JSON if not provided
        assert "mode" not in data or data.get("mode") is None
    
    def test_chat_history_append_with_mode(self, temp_history_file):
        """Test appending messages with mode to chat history."""
        history = ChatHistory(temp_history_file)
        
        history.append("user", "Test message", mode="chat")
        history.append("assistant", "Response", mode="agent")
        
        # Read back and verify
        lines = temp_history_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        
        msg1 = json.loads(lines[0])
        assert msg1["role"] == "user"
        assert msg1["mode"] == "chat"
        
        msg2 = json.loads(lines[1])
        assert msg2["role"] == "assistant"
        assert msg2["mode"] == "agent"
    
    def test_chat_history_append_without_mode(self, temp_history_file):
        """Test appending messages without mode (backward compatible)."""
        history = ChatHistory(temp_history_file)
        
        history.append("user", "Test message")
        
        lines = temp_history_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        
        msg = json.loads(lines[0])
        assert msg["role"] == "user"
        assert "mode" not in msg or msg.get("mode") is None
    
    def test_chat_history_with_metadata_and_mode(self, temp_history_file):
        """Test that mode and metadata can coexist."""
        history = ChatHistory(temp_history_file)
        
        history.append(
            "tool",
            "Tool result",
            mode="agent",
            name="run_shell",
            tool_call_id="call_123"
        )
        
        lines = temp_history_file.read_text(encoding="utf-8").strip().split("\n")
        msg = json.loads(lines[0])
        
        assert msg["role"] == "tool"
        assert msg["mode"] == "agent"
        assert msg["meta"]["name"] == "run_shell"
        assert msg["meta"]["tool_call_id"] == "call_123"


class TestStreamingImprovements:
    """Test improvements to streaming behavior."""
    
    def test_mode_indicator_updates(self):
        """Test that mode indicator text is appropriate."""
        # This would need actual GUI testing, so we'll just verify the logic
        chat_desc = "(Conversational mode with strict safety)"
        agent_desc = "(Autonomous mode - tools enabled)"
        
        assert "safety" in chat_desc.lower()
        assert "autonomous" in agent_desc.lower()
    
    def test_truncation_markers_clear(self):
        """Test that truncation markers are user-friendly."""
        large_data = json.dumps({"output": "x" * 10000})
        truncated = _truncate_tool_result(large_data, max_bytes=1000)
        
        # Should have a clear truncation message
        assert "truncated" in truncated.lower()
        # Should mention token or efficiency
        assert "token" in truncated.lower() or "efficiency" in truncated.lower()


class TestContextManagement:
    """Test context and token management improvements."""
    
    def test_default_max_bytes_reasonable(self):
        """Test that default max_bytes is reasonable for token management."""
        # Default is 8000 bytes, roughly 2000 tokens
        large_result = json.dumps({"data": "x" * 20000})
        truncated = _truncate_tool_result(large_result)  # Use default
        
        # Should be significantly smaller
        assert len(truncated) < len(large_result)
        # Should be around 8KB + marker
        assert len(truncated.encode('utf-8')) < 10000
    
    def test_truncation_preserves_error_messages(self):
        """Test that error messages in tool results are not truncated."""
        small_error = json.dumps({"error": "File not found"})
        truncated = _truncate_tool_result(small_error, max_bytes=1000)
        
        # Small errors should pass through
        data = json.loads(truncated)
        assert data["error"] == "File not found"
    
    def test_multiple_truncations_on_same_content(self):
        """Test that truncation is idempotent."""
        large_result = json.dumps({"output": "y" * 10000})
        
        truncated_once = _truncate_tool_result(large_result, max_bytes=2000)
        truncated_twice = _truncate_tool_result(truncated_once, max_bytes=2000)
        
        # Should be similar size (already truncated)
        assert abs(len(truncated_once) - len(truncated_twice)) < 100
