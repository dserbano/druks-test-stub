"""Incremental build manifest.

The manifest is a JSON file keyed by source path with a SHA256 content
hash. It also tracks the aggregate hash of templates/theme/plugins so a
change there invalidates every page.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Set


MANIFEST_NAME = ".sitegen-manifest.json"


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_path(p: Path) -> str:
    return hash_bytes(p.read_bytes())


def hash_tree(paths: Iterable[Path]) -> str:
    """Combined hash of the contents of the given paths, order-insensitive."""
    h = hashlib.sha256()
    for p in sorted(paths):
        if p.is_file():
            h.update(str(p).encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()


@dataclass
class Manifest:
    sources: Dict[str, str] = field(default_factory=dict)
    global_hash: str = ""

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(sources=dict(data.get("sources", {})), global_hash=data.get("global_hash", ""))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"sources": self.sources, "global_hash": self.global_hash}, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def is_dirty(self, rel: str, content_hash: str, global_hash: str) -> bool:
        if global_hash != self.global_hash:
            return True
        return self.sources.get(rel) != content_hash

    def update(self, rel: str, content_hash: str) -> None:
        self.sources[rel] = content_hash


def plan_rebuild(
    content_files: Dict[str, bytes],
    manifest: Manifest,
    global_hash: str,
) -> Set[str]:
    """Return the subset of ``content_files`` that need rebuilding."""
    if global_hash != manifest.global_hash:
        return set(content_files.keys())
    out = set()
    for rel, data in content_files.items():
        content_hash = hash_bytes(data)
        if manifest.sources.get(rel) != content_hash:
            out.add(rel)
    return out
