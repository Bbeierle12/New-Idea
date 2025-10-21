"""Single background worker thread to avoid blocking the UI."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any, Callable, Optional

from .logger import Logger

TaskCallable = Callable[..., Any]
TaskCallback = Optional[Callable[[Any], None]]


@dataclass
class Task:
    func: TaskCallable
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    callback: TaskCallback
    description: str


class Worker:
    """Executes tasks on a single background thread."""

    def __init__(self, logger: Logger, name: str = "Worker") -> None:
        self._logger = logger
        self._queue: Queue[Optional[Task]] = Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)
        self._started = False

    def start(self) -> None:
        if not self._started:
            self._thread.start()
            self._started = True
            self._logger.info("worker_started", thread=self._thread.name)

    def submit(
        self,
        func: TaskCallable,
        *args: Any,
        description: str = "task",
        callback: TaskCallback = None,
        **kwargs: Any,
    ) -> None:
        if not self._started:
            raise RuntimeError("Worker must be started before submitting tasks.")
        self._queue.put(Task(func, args, kwargs, callback, description))
        self._logger.info("task_enqueued", description=description)

    def shutdown(self, timeout: float = 2.0) -> None:
        self._stop.set()
        self._queue.put(None)
        self._thread.join(timeout=timeout)
        self._logger.info("worker_stopped", graceful=str(self._thread.is_alive() is False))

    # Internal -------------------------------------------------------------
    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                task = self._queue.get(timeout=0.2)
            except Empty:
                continue
            if task is None:
                break
            self._execute(task)
        self._logger.info("worker_exit")

    def _execute(self, task: Task) -> None:
        self._logger.info("task_started", description=task.description)
        try:
            result = task.func(*task.args, **task.kwargs)
            if task.callback:
                task.callback(result)
            self._logger.info("task_finished", description=task.description)
        except Exception as exc:
            self._logger.error(
                "task_failed",
                description=task.description,
                error=f"{type(exc).__name__}: {exc}",
            )
