"""Append-only chat history stored as JSON lines."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class ChatRecord:
    role: str
    content: str
    meta: Dict[str, Any]

    def to_json(self) -> str:
        payload = {
            "ts": round(time.time(), 3),
            "role": self.role,
            "content": self.content,
        }
        if self.meta:
            payload["meta"] = self.meta
        return json.dumps(payload, ensure_ascii=False)


class ChatHistory:
    """Thread-safe append-only chat history."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, role: str, content: str, **meta: Any) -> None:
        """Append a single chat message with optional metadata."""
        record = ChatRecord(role=role, content=content, meta=meta)
        line = record.to_json()
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
