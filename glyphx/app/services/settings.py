"""Settings persistence for API credentials and preferences."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Optional

from ..infra.logger import Logger


@dataclass(frozen=True)
class Settings:
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    agent_prompt: Optional[str] = None
    llm_timeout: float = 60.0
    llm_rate_limit_per_minute: Optional[int] = None
    shell_timeout: float = 600.0
    # Gemma background worker settings
    gemma_enabled: bool = False
    gemma_base_url: str = "http://localhost:11434/v1"
    gemma_model: str = "gemma:300m"
    # Safety and context management settings
    tool_output_max_bytes: int = 8000
    context_truncation_enabled: bool = True
    default_mode: str = "chat"  # "chat" or "agent"

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Return a JSON-serializable representation of the settings."""
        return {
            "api_key": self.api_key,
            "model": self.model,
            "base_url": self.base_url,
            "agent_prompt": self.agent_prompt,
            "llm_timeout": self.llm_timeout,
            "llm_rate_limit_per_minute": self.llm_rate_limit_per_minute,
            "shell_timeout": self.shell_timeout,
            "gemma_enabled": self.gemma_enabled,
            "gemma_base_url": self.gemma_base_url,
            "gemma_model": self.gemma_model,
            "tool_output_max_bytes": self.tool_output_max_bytes,
            "context_truncation_enabled": self.context_truncation_enabled,
            "default_mode": self.default_mode,
        }

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "Settings":
        api_key = payload.get("api_key")
        model = payload.get("model") or "gpt-4o-mini"
        base_url = payload.get("base_url") or "https://api.openai.com/v1"
        agent_prompt = payload.get("agent_prompt")
        llm_timeout = payload.get("llm_timeout", 60.0)
        shell_timeout = payload.get("shell_timeout", 600.0)
        rate_limit = payload.get("llm_rate_limit_per_minute")
        gemma_enabled = payload.get("gemma_enabled", False)
        gemma_base_url = payload.get("gemma_base_url", "http://localhost:11434/v1")
        gemma_model = payload.get("gemma_model", "gemma:300m")
        tool_output_max_bytes = payload.get("tool_output_max_bytes", 8000)
        context_truncation_enabled = payload.get("context_truncation_enabled", True)
        default_mode = payload.get("default_mode", "chat")
        return Settings(
            api_key=str(api_key) if api_key else None,
            model=str(model),
            base_url=str(base_url),
            agent_prompt=str(agent_prompt) if agent_prompt else None,
            llm_timeout=float(llm_timeout) if llm_timeout is not None else 60.0,
            llm_rate_limit_per_minute=int(rate_limit) if rate_limit not in (None, "") else None,
            shell_timeout=float(shell_timeout) if shell_timeout is not None else 600.0,
            gemma_enabled=bool(gemma_enabled),
            gemma_base_url=str(gemma_base_url),
            gemma_model=str(gemma_model),
            tool_output_max_bytes=int(tool_output_max_bytes) if tool_output_max_bytes is not None else 8000,
            context_truncation_enabled=bool(context_truncation_enabled),
            default_mode=str(default_mode) if default_mode in ("chat", "agent") else "chat",
        )


class SettingsService:
    """Load and persist user settings."""

    def __init__(self, path: Path, logger: Logger) -> None:
        self._path = path
        self._logger = logger
        self._lock = threading.Lock()
        self._settings = Settings()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def get(self) -> Settings:
        """Return the current settings snapshot."""
        with self._lock:
            return self._settings

    def update(self, **updates: Optional[str]) -> Settings:
        """Persist updated settings values and return the new instance."""
        updates = self._validate_updates(updates)
        with self._lock:
            new_settings = self._apply_updates(self._settings, updates)
            self._settings = new_settings
            self._persist_locked()
            self._logger.info("settings_updated")
            return new_settings

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                with self._lock:
                    self._settings = Settings.from_dict(payload)
            self._logger.info("settings_loaded")
        except (json.JSONDecodeError, OSError) as exc:
            self._logger.error(
                "settings_corrupt",
                error=f"{type(exc).__name__}: {exc}",
            )

    def _persist_locked(self) -> None:
        """Write the current settings to disk.

        The caller must hold ``self._lock`` while invoking this helper.
        """
        self._path.write_text(
            json.dumps(self._settings.to_dict(), indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _apply_updates(settings: Settings, updates: Dict[str, Optional[str]]) -> Settings:
        return replace(settings, **updates)

    @staticmethod
    def _validate_updates(updates: Dict[str, Optional[str]]) -> Dict[str, Any]:
        from urllib.parse import urlparse

        validated: Dict[str, Any] = {}
        for key, value in updates.items():
            if key == "base_url" and value:
                parsed = urlparse(value)
                if parsed.scheme not in ("http", "https") or not parsed.netloc:
                    raise ValueError("Base URL must be an HTTP or HTTPS endpoint.")
                validated[key] = value.rstrip("/")
            elif key in {"llm_timeout", "shell_timeout"} and value is not None:
                try:
                    timeout = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{key} must be a positive number") from exc
                if timeout <= 0:
                    raise ValueError(f"{key} must be greater than zero.")
                validated[key] = timeout
            elif key == "llm_rate_limit_per_minute":
                if value in (None, "", "0"):
                    validated[key] = None
                else:
                    try:
                        limit = int(value)
                    except (TypeError, ValueError) as exc:
                        raise ValueError("Rate limit must be an integer.") from exc
                    if limit <= 0:
                        raise ValueError("Rate limit must be positive.")
                    validated[key] = limit
            elif key == "tool_output_max_bytes" and value is not None:
                try:
                    max_bytes = int(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("Tool output max bytes must be an integer.") from exc
                if max_bytes < 1000:
                    raise ValueError("Tool output max bytes must be at least 1000 (1KB).")
                if max_bytes > 100000:
                    raise ValueError("Tool output max bytes cannot exceed 100000 (100KB).")
                validated[key] = max_bytes
            elif key == "context_truncation_enabled" and value is not None:
                validated[key] = bool(value)
            elif key == "default_mode" and value is not None:
                if value not in ("chat", "agent"):
                    raise ValueError("Default mode must be 'chat' or 'agent'.")
                validated[key] = value
            else:
                validated[key] = value
        return validated
