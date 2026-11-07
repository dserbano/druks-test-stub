"""SQLite connection helpers used across the tracker package."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional, Union

PathLike = Union[str, os.PathLike, None]


def connect(path: PathLike = ":memory:") -> sqlite3.Connection:
    """Open a SQLite connection configured for the tracker.

    Foreign keys are enabled on every connection. ``row_factory`` is
    :class:`sqlite3.Row` so callers can index columns by name.
    """
    target = ":memory:" if path is None else os.fspath(path) if not isinstance(path, str) else path
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block inside a transaction, committing on success."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def executescript(conn: sqlite3.Connection, script: str) -> None:
    """Execute a multi-statement SQL script."""
    conn.executescript(script)


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def close(conn: Optional[sqlite3.Connection]) -> None:
    if conn is not None:
        conn.close()
