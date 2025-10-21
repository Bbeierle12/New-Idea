"""Diagnostics helpers: crash reporting and update checking stubs."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional

from .logger import Logger


class CrashReporter:
    """Very small crash reporter that writes uncaught exceptions to disk."""

    def __init__(self, dump_path: Path, logger: Logger) -> None:
        self._dump_path = dump_path
        self._logger = logger
        self._previous: Optional[callable] = None

    def install(self) -> None:
        if self._previous is None:
            self._previous = sys.excepthook
            sys.excepthook = self._handle

    def _handle(self, exc_type, exc, tb) -> None:
        payload = {
            "type": exc_type.__name__,
            "message": str(exc),
            "time": time.time(),
        }
        try:
            self._dump_path.parent.mkdir(parents=True, exist_ok=True)
            with self._dump_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False))
                fh.write('\n')
        except OSError:
            pass
        self._logger.error("unhandled_exception", error=f"{exc_type.__name__}: {exc}")
        if self._previous:
            self._previous(exc_type, exc, tb)


class UpdateChecker:
    """Placeholder update checker that logs when invoked."""

    def __init__(self, current_version: str, logger: Logger) -> None:
        self._current_version = current_version
        self._logger = logger

    def schedule(self, worker, *, delay: float = 0.0) -> None:
        def task() -> None:
            if delay > 0:
                time.sleep(delay)
            self._logger.info("update_check", version=self._current_version, status="not_implemented")

        worker.submit(task, description="update_check")
