from __future__ import annotations

from pathlib import Path

from glyphx.app.infra.paths import AppPaths, ensure_app_paths


def test_ensure_app_paths_custom_base(tmp_path: Path) -> None:
    base = tmp_path / "cfg"
    paths = ensure_app_paths(base)
    assert isinstance(paths, AppPaths)
    assert paths.base_dir == base
    assert paths.registry_path.parent == base
    assert paths.logs_dir.exists()
