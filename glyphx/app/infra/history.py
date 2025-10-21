"""Append-only command history store."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class CommandRecord:
    timestamp: float
    source: str
    command: str

    def to_json(self) -> str:
        payload = {
            "ts": round(self.timestamp, 3),
            "source": self.source,
            "command": self.command,
        }
        return json.dumps(payload, ensure_ascii=False)


class CommandHistory:
    """Thread-safe append-only command history."""

    def __init__(self, path: Path, keep: int = 50) -> None:
        self._path = path
        self._keep = keep
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, source: str, command: str) -> None:
        record = CommandRecord(time.time(), source, command)
        line = record.to_json()
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def tail(self) -> List[CommandRecord]:
        with self._lock:
            if not self._path.exists():
                return []
            lines = self._path.read_text(encoding="utf-8").splitlines()[-self._keep :]
        records: List[CommandRecord] = []
        for line in lines:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            record = CommandRecord(
                timestamp=float(data.get("ts", 0.0)),
                source=str(data.get("source", "")),
                command=str(data.get("command", "")),
            )
            records.append(record)
        return records
