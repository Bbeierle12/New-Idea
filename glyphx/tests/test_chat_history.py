from __future__ import annotations

import json
from pathlib import Path

from glyphx.app.infra.chat_history import ChatHistory
from glyphx.app.infra.history import CommandHistory


def test_chat_history_appends_jsonl(tmp_path: Path) -> None:
    history = ChatHistory(tmp_path / "chat.jsonl")
    history.append("user", "List glyphs")
    history.append("assistant", "Here they are", tool_call_id="tool-1")

    lines = (tmp_path / "chat.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["role"] == "user"
    assert first["content"] == "List glyphs"
    assert second["meta"]["tool_call_id"] == "tool-1"


def test_command_history_tail(tmp_path: Path) -> None:
    history = CommandHistory(tmp_path / "cmd_history.jsonl", keep=3)
    history.append("glyph", "echo 1")
    history.append("chat", "run tests")
    tail = history.tail()
    assert len(tail) == 2
    assert tail[0].source == "glyph"
    assert tail[1].command == "run tests"
