"""Label CRUD and label<->task helpers."""

from __future__ import annotations

import sqlite3
from typing import List, Optional


def create(conn: sqlite3.Connection, name: str, color: str = "#888888") -> int:
    cur = conn.execute(
        "INSERT INTO labels(name, color) VALUES (?, ?)",
        (name, color),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, label_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM labels WHERE id = ?", (label_id,)).fetchone()


def get_by_name(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM labels WHERE name = ?", (name,)).fetchone()


def list_all(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM labels ORDER BY name").fetchall()


def update(
    conn: sqlite3.Connection,
    label_id: int,
    *,
    name: Optional[str] = None,
    color: Optional[str] = None,
) -> int:
    fields = []
    params: List[object] = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if color is not None:
        fields.append("color = ?")
        params.append(color)
    if not fields:
        return 0
    params.append(label_id)
    cur = conn.execute(
        f"UPDATE labels SET {', '.join(fields)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cur.rowcount


def delete(conn: sqlite3.Connection, label_id: int) -> int:
    cur = conn.execute("DELETE FROM labels WHERE id = ?", (label_id,))
    conn.commit()
    return cur.rowcount


def tasks_for(conn: sqlite3.Connection, label_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT tasks.* FROM tasks
        JOIN task_labels ON task_labels.task_id = tasks.id
        WHERE task_labels.label_id = ?
        ORDER BY tasks.id
        """,
        (label_id,),
    ).fetchall()


def count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM labels").fetchone()
    return int(row["c"])
