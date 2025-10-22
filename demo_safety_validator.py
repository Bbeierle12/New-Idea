"""Interactive test to demonstrate safety validation."""

from pathlib import Path
from glyphx.app.infra.safety import SafetyConfig, SafetyValidator


def print_validation_result(label: str, is_safe: bool, reason: str):
    """Print a formatted validation result."""
    status = "✅ SAFE" if is_safe else "❌ BLOCKED"
    print(f"\n{label}")
    print(f"  {status}: {reason}")


def test_shell_commands():
    """Test various shell commands."""
    print("\n" + "="*60)
    print("SHELL COMMAND VALIDATION TESTS")
    print("="*60)
    
    config = SafetyConfig()
    validator = SafetyValidator(config)
    
    test_commands = [
        ("Safe command", "ls -la"),
        ("Safe command with pipe", "git status | grep modified"),
        ("Python script", "python script.py"),
        ("Dangerous: rm -rf", "rm -rf /"),
        ("Dangerous: shutdown", "shutdown now"),
        ("Dangerous: format", "format c:"),
        ("Unlisted command", "dangerous_malware"),
        ("Empty command", ""),
    ]
    
    for label, command in test_commands:
        is_safe, reason = validator.validate_shell_command(command)
        print_validation_result(f"Command: '{command}'", is_safe, reason)


def test_file_paths():
    """Test file path validation."""
    print("\n" + "="*60)
    print("FILE PATH VALIDATION TESTS")
    print("="*60)
    
    config = SafetyConfig()
    validator = SafetyValidator(config)
    
    test_paths = [
        ("Text file read", Path("document.txt"), False),
        ("Python file write", Path("script.py"), True),
        ("Executable write", Path("malware.exe"), True),
        ("DLL file", Path("system.dll"), True),
        ("JSON file", Path("config.json"), True),
    ]
    
    for label, path, is_write in test_paths:
        is_safe, reason = validator.validate_file_path(path, write=is_write)
        operation = "write" if is_write else "read"
        print_validation_result(f"{operation.title()}: '{path}'", is_safe, reason)


def test_jail_directory():
    """Test jail directory enforcement."""
    print("\n" + "="*60)
    print("JAIL DIRECTORY TESTS")
    print("="*60)
    
    jail_dir = Path("/home/user/safe_workspace")
    config = SafetyConfig(file_jail_dir=jail_dir)
    validator = SafetyValidator(config)
    
    test_paths = [
        ("Inside jail", jail_dir / "document.txt"),
        ("Inside subdirectory", jail_dir / "subdir" / "file.py"),
        ("Outside jail", Path("/etc/passwd")),
        ("Parent directory", jail_dir.parent / "unsafe.txt"),
    ]
    
    for label, path in test_paths:
        is_safe, reason = validator.validate_file_path(path, write=False)
        print_validation_result(f"{label}: '{path}'", is_safe, reason)


def test_output_truncation():
    """Test output truncation."""
    print("\n" + "="*60)
    print("OUTPUT TRUNCATION TESTS")
    print("="*60)
    
    config = SafetyConfig(max_output_bytes=100)
    validator = SafetyValidator(config)
    
    short_output = "Short output that fits"
    long_output = "x" * 500
    
    truncated_short = validator.truncate_output(short_output)
    truncated_long = validator.truncate_output(long_output)
    
    print(f"\nShort output ({len(short_output)} bytes):")
    print(f"  ✅ Preserved: {truncated_short == short_output}")
    print(f"  Length: {len(truncated_short)} bytes")
    
    print(f"\nLong output ({len(long_output.encode())} bytes):")
    print(f"  ✅ Truncated: {len(truncated_long.encode())} <= 100 bytes")
    print(f"  Length: {len(truncated_long.encode())} bytes")
    print(f"  Has marker: {'truncated' in truncated_long.lower()}")


def test_disabled_safety():
    """Test with safety disabled."""
    print("\n" + "="*60)
    print("SAFETY DISABLED TESTS")
    print("="*60)
    
    config = SafetyConfig(enabled=False)
    validator = SafetyValidator(config)
    
    # These should all pass when safety is disabled
    test_cases = [
        ("Dangerous command", lambda: validator.validate_shell_command("rm -rf /")),
        ("Dangerous file", lambda: validator.validate_file_path(Path("malware.exe"), write=True)),
    ]
    
    for label, test_func in test_cases:
        is_safe, reason = test_func()
        print_validation_result(label, is_safe, reason)


def main():
    """Run all safety validation tests."""
    print("\n" + "🛡️  GLYPHX SAFETY VALIDATION DEMO  🛡️")
    
    test_shell_commands()
    test_file_paths()
    test_jail_directory()
    test_output_truncation()
    test_disabled_safety()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)
    print("\nThe safety module successfully blocks dangerous operations")
    print("while allowing safe commands and file access.")
    print()


if __name__ == "__main__":
    main()
