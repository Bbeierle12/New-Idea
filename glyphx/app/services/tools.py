"""LLM-accessible tool implementations."""

from __future__ import annotations

import subprocess
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from ..infra.logger import Logger
from ..infra.safety import SafetyConfig, SafetyValidator
from .registry import RegistryService

MAX_READ_BYTES = 128 * 1024


def _normalize_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


class ToolsBridge:
    """Expose glyph, shell, and file helpers to the LLM."""

    def __init__(
        self, 
        registry: RegistryService, 
        logger: Logger, 
        *, 
        default_shell_timeout: float = 600.0,
        safety_config: Optional[SafetyConfig] = None,
        confirmation_callback: Optional[Callable[[str, dict, str], tuple[str, bool]]] = None,
    ) -> None:
        self._registry = registry
        self._logger = logger
        self._shell_timeout = default_shell_timeout
        self._safety_config = safety_config or SafetyConfig()
        self._safety_validator = SafetyValidator(self._safety_config)
        self._confirmation_callback = confirmation_callback
        self._session_approvals: Dict[str, str] = {}  # tool:args_hash -> "allow" or "deny"
        self._mode = "chat"  # Default mode

    def tool_descriptions(self) -> List[Dict[str, Any]]:
        """Return the OpenAI tool schema describing callable functions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_glyphs",
                    "description": "Return all saved glyphs (id, name, emoji, cmd, cwd).",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_glyph",
                    "description": "Run a saved glyph by id or name (case insensitive).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "identifier": {
                                "type": "string",
                                "description": "Glyph id or name.",
                            }
                        },
                        "required": ["identifier"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_shell",
                    "description": "Run a shell command. Prefer glyphs when possible.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to execute"},
                            "cwd": {
                                "type": "string",
                                "description": "Optional working directory.",
                            },
                            "timeout": {
                                "type": "number",
                                "description": "Command timeout in seconds (default: 600, min: 1, max: 3600)",
                                "minimum": 1,
                                "maximum": 3600,
                            },
                        },
                        "required": ["command"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a UTF-8 text file (size capped).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                        },
                        "required": ["path"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write UTF-8 content to a file (overwrites).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files in a directory (non-recursive, hides dotfiles).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                        },
                        "required": ["path"],
                        "additionalProperties": False,
                    },
                },
            },
        ]

    def execute_tool(self, name: str, arguments: str | Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a tool request coming from the LLM."""
        if isinstance(arguments, str) and arguments.strip():
            try:
                params = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON arguments for {name}: {exc}") from exc
        else:
            params = arguments if isinstance(arguments, dict) else {}

        if name == "list_glyphs":
            return self.list_glyphs()
        if name == "run_glyph":
            identifier = params.get("identifier")
            if not isinstance(identifier, str):
                raise ValueError("run_glyph requires 'identifier' string")
            return self.run_glyph(identifier)
        if name == "run_shell":
            command = params.get("command")
            if not isinstance(command, str):
                raise ValueError("run_shell requires 'command' string")
            cwd = params.get("cwd") if isinstance(params.get("cwd"), str) else None
            timeout_param = params.get("timeout")
            timeout = float(timeout_param) if isinstance(timeout_param, (int, float)) else None
            return self.run_shell(command, cwd=cwd, timeout=timeout)
        if name == "read_file":
            path = params.get("path")
            if not isinstance(path, str):
                raise ValueError("read_file requires 'path' string")
            return self.read_file(path)
        if name == "write_file":
            path = params.get("path")
            content = params.get("content")
            if not isinstance(path, str) or not isinstance(content, str):
                raise ValueError("write_file requires 'path' and 'content' strings")
            return self.write_file(path, content)
        if name == "list_files":
            path = params.get("path")
            if not isinstance(path, str):
                raise ValueError("list_files requires 'path' string")
            return self.list_files(path)
        raise ValueError(f"Unknown tool {name}")

    def list_glyphs(self) -> Dict[str, object]:
        """Return glyph metadata for the LLM."""
        glyphs = [g.to_dict() for g in sorted(self._registry.list_glyphs(), key=lambda glyph: glyph.index)]
        self._logger.info("[tool] list_glyphs", count=str(len(glyphs)))
        return {"glyphs": glyphs}

    def run_glyph(self, identifier: str) -> Dict[str, str]:
        """Run a glyph by id or name (case-insensitive)."""
        glyph = self._registry.get_glyph(identifier)
        if not glyph:
            glyph = next(
                (g for g in self._registry.list_glyphs() if g.name.lower() == identifier.lower()),
                None,
            )
        if not glyph:
            raise ValueError(f"Unknown glyph {identifier}")
        return self.run_shell(glyph.cmd, cwd=glyph.cwd, label=f"glyph:{glyph.name}")

    def run_shell(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        timeout: Optional[float] = None,
        label: Optional[str] = None,
    ) -> Dict[str, str]:
        """Execute a shell command and return collected stdout/stderr."""
        # Validate command safety
        is_safe, reason = self._safety_validator.validate_shell_command(command)
        if not is_safe:
            self._logger.warning("[tool] run_shell_blocked", command=command, reason=reason)
            
            # In chat mode, request confirmation for blocked commands
            if self._mode == "chat" and self._safety_config.require_confirmation:
                if not self._request_confirmation("run_shell", {"command": command, "cwd": cwd}):
                    return {
                        "label": label or "shell",
                        "returncode": "-1",
                        "stdout": "",
                        "stderr": f"Command blocked by safety validator: {reason}\nUser denied execution.",
                    }
            # In agent mode with strict safety, still block
            elif self._safety_config.enabled and not self._safety_config.require_confirmation:
                return {
                    "label": label or "shell",
                    "returncode": "-1",
                    "stdout": "",
                    "stderr": f"Command blocked by safety validator: {reason}",
                }
        
        cwd_path = _normalize_path(cwd) if cwd else None
        label = label or "shell"
        
        # Enforce timeout bounds
        effective_timeout = timeout if timeout is not None else self._shell_timeout
        effective_timeout = max(1.0, min(effective_timeout, 3600.0))  # Clamp to [1, 3600]
        
        self._logger.info("[tool] run_shell", command=command, cwd=str(cwd_path or ""), timeout=str(effective_timeout))
        
        try:
            completed = subprocess.run(  # noqa: S603,S607 - user-supplied commands
                command,
                shell=True,
                cwd=str(cwd_path) if cwd_path else None,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
            stdout = self._safety_validator.truncate_output(completed.stdout or "")
            stderr = self._safety_validator.truncate_output(completed.stderr or "")
            return {
                "label": label,
                "returncode": str(completed.returncode),
                "stdout": stdout,
                "stderr": stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "label": label,
                "returncode": "-1",
                "stdout": "",
                "stderr": f"Command timed out after {effective_timeout} seconds",
            }

    def read_file(self, path: str) -> Dict[str, str]:
        """Read a UTF-8 text file (with size cap)."""
        file_path = _normalize_path(path)
        
        # Validate file path safety
        is_safe, reason = self._safety_validator.validate_file_path(file_path, write=False)
        if not is_safe:
            self._logger.warning("[tool] read_file_blocked", path=str(file_path), reason=reason)
            
            # In chat mode, request confirmation for blocked paths
            if self._mode == "chat" and self._safety_config.require_confirmation:
                if not self._request_confirmation("read_file", {"path": path}):
                    return {
                        "path": str(file_path),
                        "content": f"Error: File access blocked by safety validator: {reason}\nUser denied access.",
                    }
            # In strict mode, block without confirmation
            elif self._safety_config.enabled and not self._safety_config.require_confirmation:
                return {
                    "path": str(file_path),
                    "content": f"Error: File access blocked by safety validator: {reason}",
                }
        
        try:
            data = file_path.read_text(encoding="utf-8")
            data = self._safety_validator.truncate_output(data)
            self._logger.info("[tool] read_file", path=str(file_path), bytes=str(len(data)))
            return {"path": str(file_path), "content": data}
        except Exception as e:
            self._logger.error("[tool] read_file_error", path=str(file_path), error=str(e))
            return {"path": str(file_path), "content": f"Error reading file: {e}"}

    def write_file(self, path: str, content: str) -> Dict[str, str]:
        """Write UTF-8 text to disk, creating parent directories as needed."""
        file_path = _normalize_path(path)
        
        # Validate file path safety
        is_safe, reason = self._safety_validator.validate_file_path(file_path, write=True)
        if not is_safe:
            self._logger.warning("[tool] write_file_blocked", path=str(file_path), reason=reason)
            
            # In chat mode, request confirmation for blocked paths
            if self._mode == "chat" and self._safety_config.require_confirmation:
                if not self._request_confirmation("write_file", {"path": path, "content": content[:100] + "..."}):
                    return {
                        "path": str(file_path),
                        "bytes": "0",
                        "error": f"File write blocked by safety validator: {reason}\nUser denied access.",
                    }
            # In strict mode, block without confirmation
            elif self._safety_config.enabled and not self._safety_config.require_confirmation:
                return {
                    "path": str(file_path),
                    "bytes": "0",
                    "error": f"File write blocked by safety validator: {reason}",
                }
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            self._logger.info("[tool] write_file", path=str(file_path), bytes=str(len(content.encode('utf-8'))))
            return {"path": str(file_path), "bytes": str(len(content.encode('utf-8')))}
        except Exception as e:
            self._logger.error("[tool] write_file_error", path=str(file_path), error=str(e))
            return {"path": str(file_path), "bytes": "0", "error": f"Error writing file: {e}"}

    def list_files(self, path: str) -> Dict[str, object]:
        """List non-hidden entries in the specified directory."""
        folder = _normalize_path(path)
        if not folder.is_dir():
            raise NotADirectoryError(str(folder))
        entries = [
            e.name
            for e in sorted(folder.iterdir())
            if not e.name.startswith(".")
        ]
        self._logger.info("[tool] list_files", path=str(folder), count=str(len(entries)))
        return {"path": str(folder), "entries": entries}

    def set_shell_timeout(self, timeout: float) -> None:
        self._shell_timeout = timeout
    
    def set_mode(self, mode: str) -> None:
        """Set the execution mode (chat or agent)."""
        self._mode = mode
    
    def _get_approval_key(self, tool_name: str, arguments: dict) -> str:
        """Generate a hash key for session approval tracking."""
        import hashlib
        args_str = json.dumps(arguments, sort_keys=True)
        return f"{tool_name}:{hashlib.md5(args_str.encode()).hexdigest()}"
    
    def _request_confirmation(self, tool_name: str, arguments: dict) -> bool:
        """Request user confirmation for potentially dangerous operations.
        
        Returns True if approved, False if denied.
        """
        # Check session approvals first
        approval_key = self._get_approval_key(tool_name, arguments)
        if approval_key in self._session_approvals:
            cached = self._session_approvals[approval_key]
            self._logger.info(
                f"[tool] cached_approval",
                tool=tool_name,
                decision=cached,
            )
            return cached == "allow"
        
        # If no confirmation callback, default to allow (for testing)
        if not self._confirmation_callback:
            return True
        
        # Request confirmation via callback
        action, remember = self._confirmation_callback(tool_name, arguments, self._mode)
        
        # Cache decision if requested
        if remember:
            self._session_approvals[approval_key] = action
            self._logger.info(
                f"[tool] cached_approval_stored",
                tool=tool_name,
                decision=action,
            )
        
        return action == "allow"
