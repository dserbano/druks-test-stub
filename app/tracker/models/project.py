"""Project CRUD."""

from __future__ import annotations

import sqlite3
from typing import List, Optional


def create(conn: sqlite3.Connection, name: str, description: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO projects(name, description) VALUES (?, ?)",
        (name, description),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, project_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM projects WHERE id = ?", (project_id,)
    ).fetchone()


def get_by_name(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM projects WHERE name = ?", (name,)
    ).fetchone()


def list_all(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM projects ORDER BY name").fetchall()


def update(
    conn: sqlite3.Connection,
    project_id: int,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> int:
    fields = []
    params: List[object] = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if not fields:
        return 0
    params.append(project_id)
    cur = conn.execute(
        f"UPDATE projects SET {', '.join(fields)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cur.rowcount


def delete(conn: sqlite3.Connection, project_id: int) -> int:
    cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    return cur.rowcount


def count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM projects").fetchone()
    return int(row["c"])
