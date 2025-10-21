from __future__ import annotations

try:
    import tkinter  # noqa: F401
except Exception:  # pragma: no cover - environment without Tk support
    tkinter_available = False
else:
    tkinter_available = True

import pytest

from glyphx.app.gui import Application
from glyphx.app.infra.paths import ensure_app_paths


@pytest.mark.skipif(not tkinter_available, reason="Tkinter is not available")
def test_application_smoke(tmp_path) -> None:
    paths = ensure_app_paths(tmp_path / "cfg")
    app = Application(paths)
    try:
        app.root.update_idletasks()
        app.root.update()
    finally:
        app.worker.shutdown()
        app.root.destroy()
