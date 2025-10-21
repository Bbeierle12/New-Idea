"""Platform-aware paths for GlyphX configuration and data."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


APP_FOLDER = "glyphx"


@dataclass(frozen=True)
class AppPaths:
    """Container for all on-disk locations used by the app."""

    base_dir: Path
    registry_path: Path
    settings_path: Path
    logs_dir: Path
    chat_history_path: Path
    command_history_path: Path


def _windows_config_home() -> Optional[Path]:
    appdata = Path.home() / "AppData" / "Roaming"
    if "APPDATA" in os.environ:
        return Path(os.environ["APPDATA"])
    if appdata.exists():
        return appdata
    return None


def _mac_config_home() -> Path:
    return Path.home() / "Library" / "Application Support"


def _unix_config_home() -> Path:
    xdg_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_home:
        return Path(xdg_home)
    return Path.home() / ".config"


def default_base_dir() -> Path:
    """Return the directory that should hold GlyphX configuration."""
    system = platform.system()
    if system == "Windows":
        win_home = _windows_config_home()
        if win_home is None:
            return Path.home() / APP_FOLDER
        return win_home / APP_FOLDER
    if system == "Darwin":
        return _mac_config_home() / APP_FOLDER
    return _unix_config_home() / APP_FOLDER


def ensure_app_paths(base_dir: Optional[Path] = None) -> AppPaths:
    """Create the directory structure (if needed) and return the paths."""
    root = base_dir or default_base_dir()
    registry_path = root / "registry.json"
    settings_path = root / "config.json"
    logs_dir = root / "logs"
    chat_history_path = root / "chat_history.jsonl"
    command_history_path = root / "command_history.jsonl"

    root.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    return AppPaths(
        base_dir=root,
        registry_path=registry_path,
        settings_path=settings_path,
        logs_dir=logs_dir,
        chat_history_path=chat_history_path,
        command_history_path=command_history_path,
    )
