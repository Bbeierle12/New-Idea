"""Safety controls for tool execution."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List, Set
from dataclasses import dataclass, field


@dataclass
class SafetyConfig:
    """Safety configuration for tool execution."""
    
    # General settings
    enabled: bool = True
    require_confirmation: bool = True
    
    # Shell command restrictions
    shell_allowed_commands: Set[str] = field(default_factory=lambda: {
        "ls", "dir", "echo", "pwd", "cd", "git", "npm", "pip", "python", 
        "node", "cat", "type", "find", "grep", "curl", "wget", "pytest",
        "make", "cargo", "go", "dotnet", "java", "mvn", "gradle"
    })
    shell_denied_patterns: List[str] = field(default_factory=lambda: [
        r"rm\s+-rf", r"del\s+/f", r"format\s+", r"shutdown", r"reboot",
        r"kill\s+-9", r"taskkill\s+/f", r"net\s+user", r"reg\s+",
        r"mkfs\.", r"dd\s+if=", r"fdisk", r"diskpart"
    ])
    max_output_bytes: int = 50000  # 50KB max output
    
    # File system restrictions
    file_jail_dir: Optional[Path] = None
    file_max_size_bytes: int = 1048576  # 1MB
    file_allowed_extensions: Set[str] = field(default_factory=lambda: {
        ".txt", ".md", ".json", ".yml", ".yaml", ".py", ".js", ".ts",
        ".html", ".css", ".csv", ".log", ".conf", ".ini", ".toml",
        ".xml", ".rst", ".sh", ".bash", ".sql", ".c", ".cpp", ".h",
        ".java", ".go", ".rs", ".rb", ".php", ".pl", ".r", ".m"
    })
    file_denied_paths: List[str] = field(default_factory=lambda: [
        r".*\.exe$", r".*\.dll$", r".*\.sys$", r".*\.bat$", r".*\.cmd$",
        r".*/System32/.*", r".*/Windows/.*", r".*/etc/passwd.*",
        r".*\.so$", r".*\.dylib$", r".*/bin/.*"
    ])


class SafetyValidator:
    """Validates tool operations against safety rules."""
    
    def __init__(self, config: SafetyConfig):
        self.config = config
    
    def validate_shell_command(self, command: str) -> tuple[bool, str]:
        """Validate a shell command against safety rules.
        
        Returns:
            (is_safe, reason) tuple
        """
        if not self.config.enabled:
            return True, "Safety checks disabled"
        
        # Check against denied patterns
        for pattern in self.config.shell_denied_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command matches denied pattern: {pattern}"
        
        # Extract base command
        parts = command.strip().split()
        if not parts:
            return False, "Empty command"
        
        base_cmd = parts[0].lower()
        # Remove path separators
        if '/' in base_cmd or '\\' in base_cmd:
            base_cmd = Path(base_cmd).name
        
        # Check if in allowed list (if list is not empty)
        if self.config.shell_allowed_commands:
            if base_cmd not in self.config.shell_allowed_commands:
                # Allow compound commands with allowed parts
                if not any(cmd in self.config.shell_allowed_commands 
                          for cmd in base_cmd.split('|')[0].split('&')[0].split(';')[0].split()):
                    return False, f"Command '{base_cmd}' not in allowed list"
        
        return True, "Command validated"
    
    def validate_file_path(self, path: Path, write: bool = False) -> tuple[bool, str]:
        """Validate a file path against safety rules.
        
        Returns:
            (is_safe, reason) tuple
        """
        if not self.config.enabled:
            return True, "Safety checks disabled"
        
        # Resolve to absolute path
        try:
            abs_path = path.resolve()
        except Exception as e:
            return False, f"Invalid path: {e}"
        
        # Check jail directory
        if self.config.file_jail_dir:
            jail_path = self.config.file_jail_dir.resolve()
            try:
                abs_path.relative_to(jail_path)
            except ValueError:
                return False, f"Path outside jail directory: {jail_path}"
        
        # Check denied patterns
        path_str = str(abs_path)
        for pattern in self.config.file_denied_paths:
            if re.match(pattern, path_str, re.IGNORECASE):
                return False, f"Path matches denied pattern: {pattern}"
        
        # Check file extension for writes
        if write and self.config.file_allowed_extensions:
            if abs_path.suffix.lower() not in self.config.file_allowed_extensions:
                return False, f"File type '{abs_path.suffix}' not allowed for writing"
        
        # Check file size for reads
        if not write and abs_path.exists():
            if abs_path.stat().st_size > self.config.file_max_size_bytes:
                return False, f"File too large: {abs_path.stat().st_size} bytes"
        
        return True, "Path validated"
    
    def truncate_output(self, output: str) -> str:
        """Truncate output to configured maximum."""
        output_bytes = output.encode('utf-8', errors='ignore')
        if len(output_bytes) <= self.config.max_output_bytes:
            return output
        
        # Truncate and add marker
        truncated = output_bytes[:self.config.max_output_bytes].decode('utf-8', errors='ignore')
        return truncated + "\n\n[Output truncated - exceeded maximum size]"
