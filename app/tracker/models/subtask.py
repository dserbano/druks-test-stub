"""Subtask CRUD."""

from __future__ import annotations

import sqlite3
from typing import List, Optional


def create(conn: sqlite3.Connection, task_id: int, title: str, done: bool = False) -> int:
    cur = conn.execute(
        "INSERT INTO subtasks(task_id, title, done) VALUES (?, ?, ?)",
        (task_id, title, 1 if done else 0),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, subtask_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()


def list_for_task(conn: sqlite3.Connection, task_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM subtasks WHERE task_id = ? ORDER BY id",
        (task_id,),
    ).fetchall()


def update(
    conn: sqlite3.Connection,
    subtask_id: int,
    *,
    title: Optional[str] = None,
    done: Optional[bool] = None,
) -> int:
    fields = []
    params: List[object] = []
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    if done is not None:
        fields.append("done = ?")
        params.append(1 if done else 0)
    if not fields:
        return 0
    params.append(subtask_id)
    cur = conn.execute(
        f"UPDATE subtasks SET {', '.join(fields)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cur.rowcount


def mark_done(conn: sqlite3.Connection, subtask_id: int) -> int:
    return update(conn, subtask_id, done=True)


def mark_open(conn: sqlite3.Connection, subtask_id: int) -> int:
    return update(conn, subtask_id, done=False)


def delete(conn: sqlite3.Connection, subtask_id: int) -> int:
    cur = conn.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
    conn.commit()
    return cur.rowcount


def count_for_task(conn: sqlite3.Connection, task_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM subtasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    return int(row["c"])


def done_fraction(conn: sqlite3.Connection, task_id: int) -> float:
    rows = conn.execute(
        "SELECT done FROM subtasks WHERE task_id = ?",
        (task_id,),
    ).fetchall()
    if not rows:
        return 0.0
    done = sum(1 for r in rows if r["done"])
    return done / len(rows)
