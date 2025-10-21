from __future__ import annotations

from pathlib import Path

import json
import pytest

from glyphx.app.infra.logger import Logger
from glyphx.app.services.registry import GlyphCreate, RegistryService


def make_logger(tmp_path: Path) -> Logger:
    return Logger(tmp_path / "app.log")


def test_add_and_persist_glyph(tmp_path: Path) -> None:
    logger = make_logger(tmp_path)
    registry_path = tmp_path / "registry.json"
    service = RegistryService(registry_path, logger)

    glyph = service.add_glyph(GlyphCreate(name="Build", cmd="make build", tags=["ci", "build"]))
    assert glyph.index == 1
    assert glyph.name == "Build"

    service2 = RegistryService(registry_path, make_logger(tmp_path))
    glyphs = service2.list_glyphs()
    assert len(glyphs) == 1
    assert glyphs[0].cmd == "make build"
    assert glyphs[0].tags == ["ci", "build"]


def test_remove_reindexes(tmp_path: Path) -> None:
    logger = make_logger(tmp_path)
    registry_path = tmp_path / "registry.json"
    service = RegistryService(registry_path, logger)

    g1 = service.add_glyph(GlyphCreate(name="One", cmd="echo 1"))
    g2 = service.add_glyph(GlyphCreate(name="Two", cmd="echo 2"))
    assert service.remove_glyph(g1.id)
    remaining = service.list_glyphs()
    assert len(remaining) == 1
    assert remaining[0].index == 1
    assert remaining[0].id == g2.id


def test_import_glyphs(tmp_path: Path) -> None:
    logger = make_logger(tmp_path)
    service = RegistryService(tmp_path / "registry.json", logger)
    import_path = tmp_path / "import.json"
    payload = {"glyphs": [{"name": "Test", "cmd": "echo hi", "tags": ["sample"], "cwd": "/tmp"}, {"name": "Duplicate", "cmd": "echo hi"}]}
    import_path.write_text(json.dumps(payload), encoding="utf-8")
    count = service.import_file(import_path)
    assert count == 2
    glyphs = service.list_glyphs()
    assert glyphs[0].tags == ["sample"]
