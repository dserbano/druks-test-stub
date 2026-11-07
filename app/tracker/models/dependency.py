"""Task dependency edges."""

from __future__ import annotations

import sqlite3
from typing import List, Optional

KINDS = ("blocks", "relates_to", "duplicates")


def create(
    conn: sqlite3.Connection,
    from_task_id: int,
    to_task_id: int,
    kind: str = "blocks",
) -> int:
    if kind not in KINDS:
        raise ValueError(f"unknown dependency kind: {kind}")
    if from_task_id == to_task_id:
        raise ValueError("a task cannot depend on itself")
    cur = conn.execute(
        "INSERT INTO dependencies(from_task_id, to_task_id, kind) VALUES (?, ?, ?)",
        (from_task_id, to_task_id, kind),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, dep_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM dependencies WHERE id = ?", (dep_id,)
    ).fetchone()


def outgoing(conn: sqlite3.Connection, task_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM dependencies WHERE from_task_id = ? ORDER BY id",
        (task_id,),
    ).fetchall()


def incoming(conn: sqlite3.Connection, task_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM dependencies WHERE to_task_id = ? ORDER BY id",
        (task_id,),
    ).fetchall()


def list_all(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM dependencies ORDER BY id").fetchall()


def update(
    conn: sqlite3.Connection,
    dep_id: int,
    *,
    kind: Optional[str] = None,
) -> int:
    if kind is None:
        return 0
    if kind not in KINDS:
        raise ValueError(f"unknown dependency kind: {kind}")
    cur = conn.execute(
        "UPDATE dependencies SET kind = ? WHERE id = ?",
        (kind, dep_id),
    )
    conn.commit()
    return cur.rowcount


def delete(conn: sqlite3.Connection, dep_id: int) -> int:
    cur = conn.execute("DELETE FROM dependencies WHERE id = ?", (dep_id,))
    conn.commit()
    return cur.rowcount


def blockers_for(conn: sqlite3.Connection, task_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT tasks.* FROM tasks
        JOIN dependencies ON dependencies.from_task_id = tasks.id
        WHERE dependencies.to_task_id = ? AND dependencies.kind = 'blocks'
        ORDER BY tasks.id
        """,
        (task_id,),
    ).fetchall()


def blocked_by_count(conn: sqlite3.Connection, task_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM dependencies WHERE to_task_id = ? AND kind='blocks'",
        (task_id,),
    ).fetchone()
    return int(row["c"])
