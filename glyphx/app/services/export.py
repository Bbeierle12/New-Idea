"""OS-specific exporters for glyph launchers."""

from __future__ import annotations

import os
import platform
import re
import shlex
import stat
from pathlib import Path
from typing import Iterable, List

from ..infra.logger import Logger
from .registry import Glyph


class ExportSummary:
    """Return value that describes files emitted during export."""

    def __init__(self, created: Iterable[Path]) -> None:
        self.created = list(created)


class ExportService:
    """Generate platform-native launchers for glyphs."""

    def __init__(self, logger: Logger) -> None:
        self._logger = logger

    def export(self, glyphs: Iterable[Glyph], destination: Path) -> ExportSummary:
        """Export the provided glyphs and return a summary.

        Depending on the platform, generates Windows batch files, macOS .command
        scripts, or Linux .desktop launchers. Each output is logged and written
        with execute permissions where relevant.
        """
        destination.mkdir(parents=True, exist_ok=True)
        glyph_list = list(glyphs)
        self._logger.info(
            "export_requested",
            glyphs=str(len(glyph_list)),
            destination=str(destination),
        )
        created: List[Path] = []
        system = platform.system()
        if system == "Windows":
            created.extend(_export_windows(glyph_list, destination, self._logger))
        elif system == "Darwin":
            created.extend(_export_macos(glyph_list, destination, self._logger))
        else:
            created.extend(_export_linux(glyph_list, destination, self._logger))
        return ExportSummary(created=created)


def _slug(name: str) -> str:
    # Lowercase, replace spaces with dashes, strip invalid filename characters.
    s = name.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9._-]", "-", s)
    s = s.strip(".-") or "glyph"
    return s[:80]


def _render_windows_bat(g: Glyph) -> str:
    lines: List[str] = ["@echo off"]
    if g.cwd:
        lines.append(f"pushd \"{g.cwd}\"")
    # Print the command for visibility
    lines.append(f"echo Running: {g.cmd}")
    lines.append(g.cmd)
    lines.append("set EXITCODE=%ERRORLEVEL%")
    if g.cwd:
        lines.append("popd")
    lines.append("echo Exit code: %EXITCODE%")
    lines.append("pause")
    return "\r\n".join(lines) + "\r\n"


def _render_macos_command(g: Glyph) -> str:
    lines: List[str] = ["#!/bin/bash", "set -e"]
    if g.cwd:
        lines.append(f"cd \"{g.cwd}\"")
    lines.append(f"echo \"Running: {g.cmd}\"")
    lines.append(g.cmd)
    lines.append('status=$?')
    lines.append('echo "Exit code: $status"')
    lines.append('read -n 1 -s -r -p "Press any key to close"')
    lines.append('echo')
    return "\n".join(lines) + "\n"


def _render_linux_desktop(g: Glyph) -> str:
    name = g.name
    exec_cmd = _build_linux_exec(g)
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Version=1.0",
        f"Name={name}",
        f"Comment=GlyphX launcher for {name}",
        "Terminal=true",
        f"Exec={exec_cmd}",
    ]
    return "\n".join(lines) + "\n"


def _build_linux_exec(g: Glyph) -> str:
    pieces = []
    if g.cwd:
        pieces.append(f"cd {shlex.quote(g.cwd)}")
    pieces.append(g.cmd)
    joined = " && ".join(pieces)
    return f"bash -lc {shlex.quote(joined)}"


def _export_windows(glyphs: Iterable[Glyph], dest: Path, logger: Logger) -> List[Path]:
    created: List[Path] = []
    for g in glyphs:
        path = dest / f"{_slug(g.name)}.bat"
        path.write_text(_render_windows_bat(g), encoding="utf-8")
        created.append(path)
        logger.info("export_created", path=str(path))
    return created


def _export_macos(glyphs: Iterable[Glyph], dest: Path, logger: Logger) -> List[Path]:
    created: List[Path] = []
    for g in glyphs:
        path = dest / f"{_slug(g.name)}.command"
        path.write_text(_render_macos_command(g), encoding="utf-8")
        _make_executable(path)
        created.append(path)
        logger.info("export_created", path=str(path))
    return created


def _export_linux(glyphs: Iterable[Glyph], dest: Path, logger: Logger) -> List[Path]:
    created: List[Path] = []
    for g in glyphs:
        path = dest / f"{_slug(g.name)}.desktop"
        path.write_text(_render_linux_desktop(g), encoding="utf-8")
        _make_executable(path)
        created.append(path)
        logger.info("export_created", path=str(path))
    return created


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
