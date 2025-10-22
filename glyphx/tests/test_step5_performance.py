"""
Step 5 Phase 2: Performance Benchmarks
Verify that safety features don't introduce performance regression.
All operations should complete within specified time thresholds.
"""

import time
import json
from pathlib import Path
import pytest

from glyphx.app.services.settings import SettingsService
from glyphx.app.infra.logger import Logger
from glyphx.app.infra.safety import SafetyValidator, SafetyConfig


class TestSafetyValidationPerformance:
    """Benchmark safety validation operations."""
    
    def test_shell_command_validation_speed(self, tmp_path: Path) -> None:
        """Verify shell command validation completes in <1ms."""
        config = SafetyConfig()
        validator = SafetyValidator(config)
        
        # Test safe command validation speed
        commands = [
            "echo hello",
            "ls -la",
            "python script.py",
            "git status",
            "npm install"
        ]
        
        total_time = 0
        iterations = 100
        
        for _ in range(iterations):
            for cmd in commands:
                start = time.perf_counter()
                validator.validate_shell_command(cmd)
                end = time.perf_counter()
                total_time += (end - start)
        
        # Average time per validation should be < 1ms
        avg_time_ms = (total_time / (iterations * len(commands))) * 1000
        assert avg_time_ms < 1.0, f"Command validation too slow: {avg_time_ms:.3f}ms (expected <1ms)"
    
    def test_file_path_validation_speed(self, tmp_path: Path) -> None:
        """Verify file path validation completes in <1ms."""
        config = SafetyConfig()
        validator = SafetyValidator(config)
        
        # Create test files
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        total_time = 0
        iterations = 100
        
        for _ in range(iterations):
            start = time.perf_counter()
            validator.validate_file_path(str(test_file), write=False)
            end = time.perf_counter()
            total_time += (end - start)
        
        # Average time per validation should be < 1ms
        avg_time_ms = (total_time / iterations) * 1000
        assert avg_time_ms < 1.0, f"File validation too slow: {avg_time_ms:.3f}ms (expected <1ms)"
    
    def test_output_truncation_speed(self, tmp_path: Path) -> None:
        """Verify output truncation handles 100KB in <10ms."""
        config = SafetyConfig(max_output_bytes=50000)
        validator = SafetyValidator(config)
        
        # Create 100KB of output
        large_output = "x" * 100000
        
        total_time = 0
        iterations = 10
        
        for _ in range(iterations):
            start = time.perf_counter()
            validator.truncate_output(large_output)
            end = time.perf_counter()
            total_time += (end - start)
        
        # Average time should be < 10ms
        avg_time_ms = (total_time / iterations) * 1000
        assert avg_time_ms < 10.0, f"Truncation too slow: {avg_time_ms:.3f}ms (expected <10ms)"


class TestSettingsServicePerformance:
    """Benchmark settings service operations."""
    
    def test_settings_load_speed(self, tmp_path: Path) -> None:
        """Verify settings load completes in <5ms."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        
        # Create config file with typical settings
        config_data = {
            "api_key": "sk-test",
            "model": "gpt-4o",
            "base_url": "https://api.openai.com/v1",
            "llm_timeout": 30.0,
            "tool_output_max_bytes": 8000,
            "context_truncation_enabled": True,
            "default_mode": "chat"
        }
        config_file.write_text(json.dumps(config_data))
        
        total_time = 0
        iterations = 100
        
        for _ in range(iterations):
            logger = Logger(log_file)
            start = time.perf_counter()
            service = SettingsService(config_file, logger)
            service.get()
            end = time.perf_counter()
            total_time += (end - start)
        
        # Average time should be < 5ms
        avg_time_ms = (total_time / iterations) * 1000
        assert avg_time_ms < 5.0, f"Settings load too slow: {avg_time_ms:.3f}ms (expected <5ms)"
    
    def test_settings_save_speed(self, tmp_path: Path) -> None:
        """Verify settings save completes in <10ms."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        service = SettingsService(config_file, logger)
        
        total_time = 0
        iterations = 100
        
        for i in range(iterations):
            start = time.perf_counter()
            service.update(
                tool_output_max_bytes=8000 + (i % 10) * 1000
            )
            end = time.perf_counter()
            total_time += (end - start)
        
        # Average time should be < 10ms
        avg_time_ms = (total_time / iterations) * 1000
        assert avg_time_ms < 10.0, f"Settings save too slow: {avg_time_ms:.3f}ms (expected <10ms)"
    
    def test_settings_update_speed(self, tmp_path: Path) -> None:
        """Verify settings update completes in <10ms."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        service = SettingsService(config_file, logger)
        
        total_time = 0
        iterations = 100
        
        for i in range(iterations):
            start = time.perf_counter()
            service.update(
                default_mode="chat" if i % 2 == 0 else "agent"
            )
            end = time.perf_counter()
            total_time += (end - start)
        
        # Average time should be < 10ms
        avg_time_ms = (total_time / iterations) * 1000
        assert avg_time_ms < 10.0, f"Settings update too slow: {avg_time_ms:.3f}ms (expected <10ms)"


class TestEndToEndPerformance:
    """Benchmark complete workflows."""
    
    def test_complete_safety_workflow_performance(self, tmp_path: Path) -> None:
        """Verify complete safety workflow (validation + truncation) is fast."""
        config = SafetyConfig(max_output_bytes=8000)
        validator = SafetyValidator(config)
        
        # Simulate complete workflow: validate command, truncate output
        command = "python script.py --arg value"
        large_output = "x" * 50000
        
        total_time = 0
        iterations = 100
        
        for _ in range(iterations):
            start = time.perf_counter()
            
            # Step 1: Validate command
            is_safe, reason = validator.validate_shell_command(command)
            
            # Step 2: Truncate output
            truncated = validator.truncate_output(large_output)
            
            end = time.perf_counter()
            total_time += (end - start)
        
        # Complete workflow should be < 2ms
        avg_time_ms = (total_time / iterations) * 1000
        assert avg_time_ms < 2.0, f"Complete workflow too slow: {avg_time_ms:.3f}ms (expected <2ms)"
    
    def test_settings_persistence_workflow_performance(self, tmp_path: Path) -> None:
        """Verify settings save + load workflow is fast."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        
        total_time = 0
        iterations = 50
        
        for i in range(iterations):
            start = time.perf_counter()
            
            # Step 1: Create service and update settings
            logger1 = Logger(log_file)
            service1 = SettingsService(config_file, logger1)
            service1.update(
                tool_output_max_bytes=8000 + (i * 100),
                default_mode="agent" if i % 2 == 0 else "chat"
            )
            
            # Step 2: Create new service and load settings
            logger2 = Logger(log_file)
            service2 = SettingsService(config_file, logger2)
            settings = service2.get()
            
            end = time.perf_counter()
            total_time += (end - start)
        
        # Complete workflow should be < 15ms
        avg_time_ms = (total_time / iterations) * 1000
        assert avg_time_ms < 15.0, f"Settings workflow too slow: {avg_time_ms:.3f}ms (expected <15ms)"


class TestScalabilityBenchmarks:
    """Test performance with large inputs."""
    
    def test_large_output_truncation(self, tmp_path: Path) -> None:
        """Verify truncation scales well with very large outputs."""
        config = SafetyConfig(max_output_bytes=10000)
        validator = SafetyValidator(config)
        
        # Test with 1MB output
        large_output = "x" * 1000000
        
        start = time.perf_counter()
        truncated = validator.truncate_output(large_output)
        end = time.perf_counter()
        
        time_ms = (end - start) * 1000
        
        # Should handle 1MB in < 50ms
        assert time_ms < 50.0, f"1MB truncation too slow: {time_ms:.3f}ms (expected <50ms)"
        assert len(truncated) < 11000  # Should be truncated to around max_output_bytes
    
    def test_many_validation_calls(self, tmp_path: Path) -> None:
        """Verify validation doesn't degrade with many calls."""
        config = SafetyConfig()
        validator = SafetyValidator(config)
        
        # Test 1000 validations
        commands = [
            "echo test",
            "ls -la",
            "python script.py",
            "git status",
            "npm install"
        ] * 200
        
        start = time.perf_counter()
        for cmd in commands:
            validator.validate_shell_command(cmd)
        end = time.perf_counter()
        
        time_ms = (end - start) * 1000
        
        # 1000 validations should complete in < 100ms
        assert time_ms < 100.0, f"1000 validations too slow: {time_ms:.3f}ms (expected <100ms)"
    
    def test_concurrent_settings_access(self, tmp_path: Path) -> None:
        """Verify settings service handles multiple rapid accesses."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        service = SettingsService(config_file, logger)
        
        # Simulate rapid setting changes (user clicking through settings)
        start = time.perf_counter()
        
        for i in range(50):
            service.update(tool_output_max_bytes=8000 + (i * 100))
            service.get()
        
        end = time.perf_counter()
        time_ms = (end - start) * 1000
        
        # 50 updates + gets should complete in < 500ms
        assert time_ms < 500.0, f"Rapid settings access too slow: {time_ms:.3f}ms (expected <500ms)"


class TestBaselinePerformance:
    """Establish performance baselines for comparison."""
    
    def test_establish_validation_baseline(self, tmp_path: Path) -> None:
        """Establish baseline for validation performance."""
        config = SafetyConfig()
        validator = SafetyValidator(config)
        
        command = "python test.py"
        
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            validator.validate_shell_command(command)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]
        
        # Log baseline metrics (these will appear in test output)
        print(f"\n=== Validation Performance Baseline ===")
        print(f"Average: {avg_time:.4f}ms")
        print(f"Min: {min_time:.4f}ms")
        print(f"Max: {max_time:.4f}ms")
        print(f"P95: {p95_time:.4f}ms")
        
        # Just verify it's reasonable
        assert avg_time < 1.0
    
    def test_establish_truncation_baseline(self, tmp_path: Path) -> None:
        """Establish baseline for truncation performance."""
        config = SafetyConfig(max_output_bytes=8000)
        validator = SafetyValidator(config)
        
        output = "x" * 100000
        
        times = []
        for _ in range(100):
            start = time.perf_counter()
            validator.truncate_output(output)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]
        
        print(f"\n=== Truncation Performance Baseline (100KB) ===")
        print(f"Average: {avg_time:.4f}ms")
        print(f"Min: {min_time:.4f}ms")
        print(f"Max: {max_time:.4f}ms")
        print(f"P95: {p95_time:.4f}ms")
        
        # Just verify it's reasonable
        assert avg_time < 10.0
    
    def test_establish_settings_baseline(self, tmp_path: Path) -> None:
        """Establish baseline for settings operations."""
        config_file = tmp_path / "config.json"
        log_file = tmp_path / "log.jsonl"
        logger = Logger(log_file)
        service = SettingsService(config_file, logger)
        
        times = []
        for i in range(100):
            start = time.perf_counter()
            service.update(tool_output_max_bytes=8000 + i)
            service.get()
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]
        
        print(f"\n=== Settings Performance Baseline ===")
        print(f"Average: {avg_time:.4f}ms")
        print(f"Min: {min_time:.4f}ms")
        print(f"Max: {max_time:.4f}ms")
        print(f"P95: {p95_time:.4f}ms")
        
        # Just verify it's reasonable
        assert avg_time < 10.0
