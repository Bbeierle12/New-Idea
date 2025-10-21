from __future__ import annotations

import platform
from pathlib import Path

import pytest

from glyphx.app.infra.logger import Logger
from glyphx.app.services.export import ExportService
from glyphx.app.services.registry import Glyph


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows .bat exporter test")
def test_export_windows_bat(tmp_path: Path) -> None:
    logger = Logger(tmp_path / "log.jsonl")
    svc = ExportService(logger)
    g1 = Glyph(id="g1", index=1, name="Echo Hi", cmd="echo hi")
    out = svc.export([g1], tmp_path)
    assert len(out.created) == 1
    bat = out.created[0]
    assert bat.suffix == ".bat"
    content = bat.read_text(encoding="utf-8")
    assert "@echo off" in content
    assert "echo hi" in content
    assert "pause" in content


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS .command exporter test")
def test_export_macos_command(tmp_path: Path) -> None:
    logger = Logger(tmp_path / "log.jsonl")
    svc = ExportService(logger)
    glyph = Glyph(id="g1", index=1, name="Deploy", cmd="bash deploy.sh", cwd="/Users/test/app")
    summary = svc.export([glyph], tmp_path)
    assert summary.created
    script = summary.created[0]
    assert script.suffix == ".command"
    text = script.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/bash")
    assert "cd \"/Users/test/app\"" in text
    mode = script.stat().st_mode
    assert mode & 0o111


@pytest.mark.skipif(platform.system() != "Linux", reason="Linux .desktop exporter test")
def test_export_linux_desktop(tmp_path: Path) -> None:
    logger = Logger(tmp_path / "log.jsonl")
    svc = ExportService(logger)
    glyph = Glyph(id="g1", index=1, name="Run Tests", cmd="pytest", cwd="/home/me/project")
    summary = svc.export([glyph], tmp_path)
    assert summary.created
    desktop = summary.created[0]
    assert desktop.suffix == ".desktop"
    text = desktop.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in text
    assert "Exec=bash -lc" in text
    assert "pytest" in text
    mode = desktop.stat().st_mode
    assert mode & 0o111
