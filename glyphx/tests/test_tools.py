from __future__ import annotations

from pathlib import Path

import pytest

from glyphx.app.infra.logger import Logger
from glyphx.app.services.registry import GlyphCreate, RegistryService
from glyphx.app.services.tools import ToolsBridge


def make_registry(tmp_path: Path) -> RegistryService:
    logger = Logger(tmp_path / "log.jsonl")
    return RegistryService(tmp_path / "registry.json", logger)


def test_list_glyphs(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    registry.add_glyph(GlyphCreate(name="Echo", cmd="echo hi"))
    bridge = ToolsBridge(registry, Logger(tmp_path / "log2.jsonl"))
    payload = bridge.list_glyphs()
    assert payload["glyphs"]
    assert payload["glyphs"][0]["name"] == "Echo"


def test_run_shell(tmp_path: Path) -> None:
    bridge = ToolsBridge(make_registry(tmp_path), Logger(tmp_path / "log.jsonl"))
    result = bridge.run_shell("python -c \"print('ok')\"")
    assert result["returncode"] == "0"
    assert "ok" in result["stdout"]


def test_tool_descriptions_include_run_shell(tmp_path: Path) -> None:
    bridge = ToolsBridge(make_registry(tmp_path), Logger(tmp_path / "log.jsonl"))
    names = {item["function"]["name"] for item in bridge.tool_descriptions()}
    assert "run_shell" in names


def test_execute_tool_run_glyph_by_name(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    registry.add_glyph(GlyphCreate(name="Echo", cmd="python -c \"print('hi')\""))
    bridge = ToolsBridge(registry, Logger(tmp_path / "log.jsonl"))
    result = bridge.execute_tool("run_glyph", {"identifier": "Echo"})
    assert result["returncode"] == "0"
    assert "hi" in result["stdout"]


def test_execute_tool_invalid_json(tmp_path: Path) -> None:
    bridge = ToolsBridge(make_registry(tmp_path), Logger(tmp_path / "log.jsonl"))
    with pytest.raises(ValueError):
        bridge.execute_tool("run_shell", "{bad json")
