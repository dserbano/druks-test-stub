"""Comments attached to tasks or projects."""

from __future__ import annotations

import sqlite3
from typing import List, Optional


def create_on_task(
    conn: sqlite3.Connection,
    task_id: int,
    body: str,
    author: str = "",
) -> int:
    cur = conn.execute(
        "INSERT INTO comments(task_id, project_id, author, body) VALUES (?, NULL, ?, ?)",
        (task_id, author, body),
    )
    conn.commit()
    return int(cur.lastrowid)


def create_on_project(
    conn: sqlite3.Connection,
    project_id: int,
    body: str,
    author: str = "",
) -> int:
    cur = conn.execute(
        "INSERT INTO comments(task_id, project_id, author, body) VALUES (NULL, ?, ?, ?)",
        (project_id, author, body),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, comment_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM comments WHERE id = ?", (comment_id,)
    ).fetchone()


def list_for_task(conn: sqlite3.Connection, task_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM comments WHERE task_id = ? ORDER BY id",
        (task_id,),
    ).fetchall()


def list_for_project(conn: sqlite3.Connection, project_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM comments WHERE project_id = ? ORDER BY id",
        (project_id,),
    ).fetchall()


def list_all(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM comments ORDER BY id").fetchall()


def update(
    conn: sqlite3.Connection,
    comment_id: int,
    *,
    body: Optional[str] = None,
    author: Optional[str] = None,
) -> int:
    fields = []
    params: List[object] = []
    if body is not None:
        fields.append("body = ?")
        params.append(body)
    if author is not None:
        fields.append("author = ?")
        params.append(author)
    if not fields:
        return 0
    params.append(comment_id)
    cur = conn.execute(
        f"UPDATE comments SET {', '.join(fields)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cur.rowcount


def delete(conn: sqlite3.Connection, comment_id: int) -> int:
    cur = conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    conn.commit()
    return cur.rowcount


def count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM comments").fetchone()
    return int(row["c"])
