from __future__ import annotations

import time
from pathlib import Path

from glyphx.app.infra.logger import Logger
from glyphx.app.infra.worker import Worker


def test_worker_executes_task(tmp_path: Path) -> None:
    logger = Logger(tmp_path / "app.log")
    worker = Worker(logger, name="TestWorker")
    worker.start()
    flag = {"done": False}

    def job() -> None:
        flag["done"] = True

    worker.submit(job, description="unit-test-job")
    timeout = time.time() + 2
    while not flag["done"] and time.time() < timeout:
        time.sleep(0.01)
    worker.shutdown()
    assert flag["done"]
