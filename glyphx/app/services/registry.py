"""Persistence for glyph definitions."""

from __future__ import annotations

import json
import secrets
import threading
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ..infra.logger import Logger


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _generate_id() -> str:
    return secrets.token_hex(4)


@dataclass(frozen=True)
class Glyph:
    id: str
    index: int
    name: str
    cmd: str
    emoji: Optional[str] = None
    cwd: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "id": self.id,
            "index": self.index,
            "name": self.name,
            "emoji": self.emoji,
            "cmd": self.cmd,
            "cwd": self.cwd,
            "tags": list(self.tags),
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(payload: Dict[str, Optional[str]]) -> "Glyph":
        tags_raw = payload.get("tags", []) or []
        tags = [str(tag) for tag in tags_raw if isinstance(tag, str)]
        return Glyph(
            id=str(payload["id"]),
            index=int(payload["index"]),
            name=str(payload["name"]),
            emoji=payload.get("emoji"),
            cmd=str(payload["cmd"]),
            cwd=payload.get("cwd"),
            tags=tags,
            created_at=str(payload["created_at"]),
        )


@dataclass(frozen=True)
class GlyphCreate:
    name: str
    cmd: str
    emoji: Optional[str] = None
    cwd: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class Registry:
    glyphs: List[Glyph] = field(default_factory=list)

    def to_dict(self) -> Dict[str, List[Dict[str, Optional[str]]]]:
        return {"glyphs": [glyph.to_dict() for glyph in self.glyphs]}

    @staticmethod
    def from_dict(payload: Dict[str, object]) -> "Registry":
        items = payload.get("glyphs", [])
        glyphs = []
        if isinstance(items, list):
            for raw in items:
                if isinstance(raw, dict):
                    try:
                        glyphs.append(Glyph.from_dict(raw))
                    except (KeyError, TypeError, ValueError):
                        continue
        return Registry(glyphs=glyphs)


class RegistryService:
    """Manages glyph persistence and indexing."""

    def __init__(self, path: Path, logger: Logger) -> None:
        self._path = path
        self._logger = logger
        self._lock = threading.Lock()
        self._registry = Registry()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    # CRUD ----------------------------------------------------------------
    def list_glyphs(self) -> List[Glyph]:
        with self._lock:
            return list(self._registry.glyphs)

    def get_glyph(self, glyph_id: str) -> Optional[Glyph]:
        with self._lock:
            return next((g for g in self._registry.glyphs if g.id == glyph_id), None)

    def add_glyph(self, payload: GlyphCreate) -> Glyph:
        with self._lock:
            glyph = Glyph(
                id=_generate_id(),
                index=self._next_index_locked(),
                name=payload.name,
                emoji=payload.emoji,
                cmd=payload.cmd,
                cwd=payload.cwd,
                tags=list(payload.tags),
                created_at=_utcnow_iso(),
            )
            self._registry.glyphs.append(glyph)
            self._persist_locked()
            self._logger.info("glyph_added", glyph_id=glyph.id, name=glyph.name)
            return glyph

    def update_glyph(self, glyph_id: str, payload: GlyphCreate) -> Optional[Glyph]:
        with self._lock:
            for idx, glyph in enumerate(self._registry.glyphs):
                if glyph.id == glyph_id:
                    updated = replace(
                        glyph,
                        name=payload.name,
                        cmd=payload.cmd,
                        emoji=payload.emoji,
                        cwd=payload.cwd,
                        tags=list(payload.tags),
                    )
                    self._registry.glyphs[idx] = updated
                    self._persist_locked()
                    self._logger.info("glyph_updated", glyph_id=glyph.id)
                    return updated
        return None

    def remove_glyph(self, glyph_id: str) -> bool:
        with self._lock:
            filtered = [g for g in self._registry.glyphs if g.id != glyph_id]
            if len(filtered) == len(self._registry.glyphs):
                return False
            self._registry.glyphs = filtered
            self._reindex_locked()
            self._persist_locked()
            self._logger.info("glyph_removed", glyph_id=glyph_id)
            return True

    def next_index(self) -> int:
        with self._lock:
            return self._next_index_locked()

    def import_file(self, json_path: Path) -> int:
        """Import glyph definitions from a JSON file."""
        payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            items = payload.get("glyphs", [])
        elif isinstance(payload, list):
            items = payload
        else:
            raise ValueError("Unsupported glyph import format")

        added = 0
        for raw in items:
            if not isinstance(raw, dict):
                continue
            try:
                name = str(raw["name"])
                cmd = str(raw["cmd"])
            except KeyError:
                continue
            tags_raw = raw.get("tags", []) or []
            tags = [str(tag).strip() for tag in tags_raw if isinstance(tag, str) and tag.strip()]
            create = GlyphCreate(
                name=name,
                cmd=cmd,
                emoji=raw.get("emoji"),
                cwd=raw.get("cwd"),
                tags=tags,
            )
            if self._glyph_exists(create):
                continue
            self.add_glyph(create)
            added += 1
        return added

    # Internal -------------------------------------------------------------
    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            registry = Registry.from_dict(data)
            with self._lock:
                self._registry = registry
            self._logger.info(
                "registry_loaded", glyphs=str(len(self._registry.glyphs))
            )
        except (json.JSONDecodeError, OSError) as exc:
            self._logger.error(
                "registry_corrupt",
                error=f"{type(exc).__name__}: {exc}",
            )
            backup = self._path.with_suffix(".corrupt")
            try:
                self._path.rename(backup)
                self._logger.warning("registry_moved_to_backup", backup=str(backup))
            except OSError:
                self._logger.error("registry_backup_failed", path=str(backup))

    def _persist_locked(self) -> None:
        serialized = self._registry.to_dict()
        self._path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

    def _reindex_locked(self) -> None:
        ordered = sorted(self._registry.glyphs, key=lambda glyph: glyph.index)
        new_glyphs = [
            replace(glyph, index=idx) for idx, glyph in enumerate(ordered, start=1)
        ]
        self._registry.glyphs = new_glyphs

    def _next_index_locked(self) -> int:
        if not self._registry.glyphs:
            return 1
        return max(g.index for g in self._registry.glyphs) + 1

    def _glyph_exists(self, candidate: GlyphCreate) -> bool:
        existing = self.list_glyphs()
        return any(g.name == candidate.name and g.cmd == candidate.cmd for g in existing)
