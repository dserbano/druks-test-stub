"""Sprint CRUD."""

from __future__ import annotations

import sqlite3
from typing import List, Optional


def create(
    conn: sqlite3.Connection,
    project_id: int,
    name: str,
    start_date: str,
    end_date: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO sprints(project_id, name, start_date, end_date) VALUES (?, ?, ?, ?)",
        (project_id, name, start_date, end_date),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, sprint_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM sprints WHERE id = ?", (sprint_id,)).fetchone()


def list_for_project(conn: sqlite3.Connection, project_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM sprints WHERE project_id = ? ORDER BY start_date",
        (project_id,),
    ).fetchall()


def list_all(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM sprints ORDER BY start_date").fetchall()


def update(
    conn: sqlite3.Connection,
    sprint_id: int,
    *,
    name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> int:
    fields = []
    params: List[object] = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if start_date is not None:
        fields.append("start_date = ?")
        params.append(start_date)
    if end_date is not None:
        fields.append("end_date = ?")
        params.append(end_date)
    if not fields:
        return 0
    params.append(sprint_id)
    cur = conn.execute(
        f"UPDATE sprints SET {', '.join(fields)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cur.rowcount


def delete(conn: sqlite3.Connection, sprint_id: int) -> int:
    cur = conn.execute("DELETE FROM sprints WHERE id = ?", (sprint_id,))
    conn.commit()
    return cur.rowcount


def tasks_for(conn: sqlite3.Connection, sprint_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM tasks WHERE sprint_id = ? ORDER BY id",
        (sprint_id,),
    ).fetchall()


def count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM sprints").fetchone()
    return int(row["c"])
