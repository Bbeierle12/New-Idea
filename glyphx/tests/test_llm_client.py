from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from glyphx.app.infra.logger import Logger
from glyphx.app.services.llm import ChatMessage, LLMClient
from glyphx.app.services.settings import SettingsService


class DummyResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # pragma: no cover - always succeeds
        return None

    def json(self) -> Dict[str, Any]:
        return self._payload


class DummySession:
    def __init__(self) -> None:
        self.request: Optional[Dict[str, Any]] = None

    def post(
        self,
        url: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float,
    ) -> DummyResponse:
        self.request = {
            "url": url,
            "json": json,
            "headers": headers,
            "timeout": timeout,
        }
        return DummyResponse(
            {
                "id": "chatcmpl-test",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Hello!",
                        }
                    }
                ],
            }
        )


def make_settings(tmp_path: Path) -> SettingsService:
    service = SettingsService(tmp_path / "config.json", Logger(tmp_path / "log.jsonl"))
    service.update(api_key="sk-test", model="gpt-test", base_url="https://api.test/v1")
    return service


def test_llm_client_sends_payload(tmp_path: Path) -> None:
    session = DummySession()
    client = LLMClient(make_settings(tmp_path), Logger(tmp_path / "log2.jsonl"), session=session)
    response = client.chat([ChatMessage(role="user", content="Hi!")])

    assert response["id"] == "chatcmpl-test"
    assert session.request is not None
    assert session.request["url"].endswith("/chat/completions")
    assert session.request["json"]["messages"][0]["role"] == "user"
    assert session.request["headers"]["Authorization"].startswith("Bearer ")


def test_llm_client_requires_api_key(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "config.json", Logger(tmp_path / "log.jsonl"))
    client = LLMClient(service, Logger(tmp_path / "log2.jsonl"), session=DummySession())
    with pytest.raises(RuntimeError):
        client.chat([ChatMessage(role="user", content="Hi!")])
