"""Assignee CRUD."""

from __future__ import annotations

import sqlite3
from typing import List, Optional


def create(conn: sqlite3.Connection, name: str, email: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO assignees(name, email) VALUES (?, ?)",
        (name, email),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, assignee_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM assignees WHERE id = ?", (assignee_id,)
    ).fetchone()


def get_by_name(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM assignees WHERE name = ?", (name,)
    ).fetchone()


def list_all(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM assignees ORDER BY name").fetchall()


def update(
    conn: sqlite3.Connection,
    assignee_id: int,
    *,
    name: Optional[str] = None,
    email: Optional[str] = None,
) -> int:
    fields = []
    params: List[object] = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if email is not None:
        fields.append("email = ?")
        params.append(email)
    if not fields:
        return 0
    params.append(assignee_id)
    cur = conn.execute(
        f"UPDATE assignees SET {', '.join(fields)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cur.rowcount


def delete(conn: sqlite3.Connection, assignee_id: int) -> int:
    cur = conn.execute("DELETE FROM assignees WHERE id = ?", (assignee_id,))
    conn.commit()
    return cur.rowcount


def tasks_for(conn: sqlite3.Connection, assignee_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM tasks WHERE assignee_id = ? ORDER BY id",
        (assignee_id,),
    ).fetchall()


def count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM assignees").fetchone()
    return int(row["c"])
