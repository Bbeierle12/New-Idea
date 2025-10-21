from __future__ import annotations

from pathlib import Path

from glyphx.app.infra.logger import Logger


def test_logger_rotates(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    logger = Logger(log_path, max_bytes=64, backup_count=2)
    for i in range(10):
        logger.info("entry", index=str(i))
    assert log_path.exists()
    backup = tmp_path / "app.log.1"
    assert backup.exists()
