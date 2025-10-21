from __future__ import annotations

from pathlib import Path
import pytest

from glyphx.app.infra.logger import Logger
from glyphx.app.services.settings import SettingsService


def create_service(tmp_path: Path) -> SettingsService:
    config_path = tmp_path / "config.json"
    logger = Logger(tmp_path / "log.jsonl")
    return SettingsService(config_path, logger)


def test_settings_update_and_persist(tmp_path: Path) -> None:
    service = create_service(tmp_path)
    service.update(api_key="sk-test", model="gpt-test", base_url="https://example.com/v1", agent_prompt="Be concise")

    current = service.get()
    assert current.api_key == "sk-test"
    assert current.model == "gpt-test"
    assert current.base_url == "https://example.com/v1"
    assert current.agent_prompt == "Be concise"

    reloaded = create_service(tmp_path)
    loaded_settings = reloaded.get()
    assert loaded_settings.api_key == "sk-test"
    assert loaded_settings.model == "gpt-test"
    assert loaded_settings.base_url == "https://example.com/v1"
    assert loaded_settings.agent_prompt == "Be concise"


def test_invalid_base_url(tmp_path: Path) -> None:
    service = create_service(tmp_path)
    with pytest.raises(ValueError) as exc:
        service.update(base_url="ftp://example.com")
    assert "Base URL" in str(exc.value)