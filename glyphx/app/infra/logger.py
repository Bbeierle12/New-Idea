"""Structured logger faning out to UI and jsonl file."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Dict, Optional


LogSink = Callable[["LogEvent"], None]


@dataclass
class LogEvent:
    """Single log line captured by the application."""

    ts: float
    level: str
    message: str
    context: Dict[str, str]

    def to_json(self) -> str:
        """Return the json representation suitable for persistence."""
        payload = asdict(self)
        payload["ts"] = round(self.ts, 3)
        return json.dumps(payload, ensure_ascii=False)


class Logger:
    """Tiny structured logger that notifies UI and appends to disk."""

    def __init__(
        self,
        log_path: Path,
        sink: Optional[LogSink] = None,
        *,
        max_bytes: int = 256_000,
        backup_count: int = 3,
    ) -> None:
        self._log_path = log_path
        self._sink = sink
        self._lock = threading.Lock()
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def set_sink(self, sink: LogSink) -> None:
        self._sink = sink

    # Convenience wrappers -------------------------------------------------
    def info(self, message: str, **context: str) -> None:
        self._emit("INFO", message, context)

    def warning(self, message: str, **context: str) -> None:
        self._emit("WARN", message, context)

    def error(self, message: str, **context: str) -> None:
        self._emit("ERROR", message, context)

    # Internal -------------------------------------------------------------
    def _emit(self, level: str, message: str, context: Dict[str, str]) -> None:
        event = LogEvent(time.time(), level.upper(), message, context)
        if self._sink:
            self._sink(event)
        with self._lock:
            self._rotate_if_needed(len(event.to_json()) + 1)
            with self._log_path.open("a", encoding="utf-8") as fp:
                fp.write(event.to_json() + "\n")

    def _rotate_if_needed(self, incoming_len: int) -> None:
        if self._max_bytes <= 0:
            return
        try:
            current_size = self._log_path.stat().st_size
        except FileNotFoundError:
            return
        if current_size + incoming_len <= self._max_bytes:
            return
        base = self._log_path
        for index in range(self._backup_count, 0, -1):
            if index == 1:
                src = base
            else:
                src = base.parent / f"{base.name}.{index-1}"
            dst = base.parent / f"{base.name}.{index}"
            if src.exists():
                try:
                    if dst.exists():
                        dst.unlink()
                except OSError:
                    pass
                try:
                    src.rename(dst)
                except OSError:
                    continue
