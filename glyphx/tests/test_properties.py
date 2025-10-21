from __future__ import annotations

import string

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st

from glyphx.app.services.export import _slug
from glyphx.app.services.registry import GlyphCreate, RegistryService
from glyphx.app.infra.logger import Logger


@given(st.text(alphabet=string.printable, max_size=200))
def test_slug_always_non_empty_and_safe(text: str) -> None:
    value = _slug(text)
    assert value
    assert len(value) <= 80
    for char in value:
        assert char in string.ascii_lowercase + string.digits + "._-"


@given(
    st.lists(
        st.tuples(
            st.text(min_size=1, max_size=24, alphabet=string.ascii_letters + string.digits + " -_"),
            st.text(min_size=1, max_size=48, alphabet=string.printable.replace("\n", "")),
        ),
        min_size=1,
        max_size=5,
    )
)
def test_registry_roundtrip_preserves_commands(tmp_path, entries) -> None:
    logger = Logger(tmp_path / "log.jsonl")
    registry_path = tmp_path / "registry.json"
    svc = RegistryService(registry_path, logger)
    for name, cmd in entries:
        svc.add_glyph(GlyphCreate(name=name, cmd=cmd))

    reloaded = RegistryService(registry_path, Logger(tmp_path / "log2.jsonl")).list_glyphs()
    assert [glyph.cmd for glyph in reloaded] == [cmd for _name, cmd in entries]
