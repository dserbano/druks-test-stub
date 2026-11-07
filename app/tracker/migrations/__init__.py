"""Ordered SQL migrations runner.

Each file in this directory matching ``NNNN_*.sql`` is applied in order,
with the applied version recorded in the ``schema_migrations`` table.
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import List, Tuple

MIGRATIONS_DIR = Path(__file__).parent
MIGRATION_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


def _ensure_registry(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def discover() -> List[Tuple[str, Path]]:
    """Return ``(version, path)`` for every migration file, sorted."""
    files: List[Tuple[str, Path]] = []
    for entry in sorted(os.listdir(MIGRATIONS_DIR)):
        match = MIGRATION_RE.match(entry)
        if not match:
            continue
        files.append((match.group(1), MIGRATIONS_DIR / entry))
    files.sort(key=lambda item: item[0])
    return files


def applied_versions(conn: sqlite3.Connection) -> List[str]:
    _ensure_registry(conn)
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    return [row["version"] for row in rows]


def pending(conn: sqlite3.Connection) -> List[Tuple[str, Path]]:
    done = set(applied_versions(conn))
    return [item for item in discover() if item[0] not in done]


def apply(conn: sqlite3.Connection) -> List[str]:
    """Apply any pending migrations idempotently, returning applied versions."""
    _ensure_registry(conn)
    applied: List[str] = []
    for version, path in pending(conn):
        sql = path.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations(version) VALUES (?)",
            (version,),
        )
        conn.commit()
        applied.append(version)
    return applied


def current_version(conn: sqlite3.Connection) -> str:
    versions = applied_versions(conn)
    return versions[-1] if versions else ""


__all__ = [
    "MIGRATIONS_DIR",
    "discover",
    "applied_versions",
    "pending",
    "apply",
    "current_version",
]
