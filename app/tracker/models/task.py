"""Task CRUD, status transitions, labels, and listing helpers."""

from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional

STATUSES = ("todo", "in_progress", "blocked", "done")


def create(
    conn: sqlite3.Connection,
    project_id: int,
    title: str,
    *,
    description: str = "",
    status: str = "todo",
    estimate: float = 0.0,
    sprint_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    completed_at: Optional[str] = None,
) -> int:
    if status not in STATUSES:
        raise ValueError(f"unknown status: {status}")
    cur = conn.execute(
        """
        INSERT INTO tasks(project_id, sprint_id, assignee_id, title, description,
                          status, estimate, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (project_id, sprint_id, assignee_id, title, description, status, estimate, completed_at),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, task_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()


def list_for_project(conn: sqlite3.Connection, project_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM tasks WHERE project_id = ? ORDER BY id",
        (project_id,),
    ).fetchall()


def list_for_sprint(conn: sqlite3.Connection, sprint_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM tasks WHERE sprint_id = ? ORDER BY id",
        (sprint_id,),
    ).fetchall()


def list_for_assignee(conn: sqlite3.Connection, assignee_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM tasks WHERE assignee_id = ? ORDER BY id",
        (assignee_id,),
    ).fetchall()


def list_all(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()


def update(
    conn: sqlite3.Connection,
    task_id: int,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    estimate: Optional[float] = None,
    sprint_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    completed_at: Optional[str] = None,
    clear_sprint: bool = False,
    clear_assignee: bool = False,
    clear_completed_at: bool = False,
) -> int:
    fields = []
    params: List[object] = []
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if status is not None:
        if status not in STATUSES:
            raise ValueError(f"unknown status: {status}")
        fields.append("status = ?")
        params.append(status)
    if estimate is not None:
        fields.append("estimate = ?")
        params.append(estimate)
    if sprint_id is not None:
        fields.append("sprint_id = ?")
        params.append(sprint_id)
    elif clear_sprint:
        fields.append("sprint_id = NULL")
    if assignee_id is not None:
        fields.append("assignee_id = ?")
        params.append(assignee_id)
    elif clear_assignee:
        fields.append("assignee_id = NULL")
    if completed_at is not None:
        fields.append("completed_at = ?")
        params.append(completed_at)
    elif clear_completed_at:
        fields.append("completed_at = NULL")
    if not fields:
        return 0
    params.append(task_id)
    cur = conn.execute(
        f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cur.rowcount


def mark_done(conn: sqlite3.Connection, task_id: int, at: str) -> int:
    cur = conn.execute(
        "UPDATE tasks SET status='done', completed_at=? WHERE id = ?",
        (at, task_id),
    )
    conn.commit()
    return cur.rowcount


def delete(conn: sqlite3.Connection, task_id: int) -> int:
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    return cur.rowcount


def attach_label(conn: sqlite3.Connection, task_id: int, label_id: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO task_labels(task_id, label_id) VALUES (?, ?)",
        (task_id, label_id),
    )
    conn.commit()


def detach_label(conn: sqlite3.Connection, task_id: int, label_id: int) -> int:
    cur = conn.execute(
        "DELETE FROM task_labels WHERE task_id = ? AND label_id = ?",
        (task_id, label_id),
    )
    conn.commit()
    return cur.rowcount


def labels_for(conn: sqlite3.Connection, task_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT labels.* FROM labels
        JOIN task_labels ON task_labels.label_id = labels.id
        WHERE task_labels.task_id = ?
        ORDER BY labels.name
        """,
        (task_id,),
    ).fetchall()


def set_labels(conn: sqlite3.Connection, task_id: int, label_ids: Iterable[int]) -> None:
    conn.execute("DELETE FROM task_labels WHERE task_id = ?", (task_id,))
    conn.executemany(
        "INSERT OR IGNORE INTO task_labels(task_id, label_id) VALUES (?, ?)",
        [(task_id, lid) for lid in label_ids],
    )
    conn.commit()


def count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()
    return int(row["c"])


def count_by_status(conn: sqlite3.Connection, project_id: Optional[int] = None) -> dict:
    if project_id is None:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS c FROM tasks GROUP BY status"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS c FROM tasks WHERE project_id = ? GROUP BY status",
            (project_id,),
        ).fetchall()
    out = {s: 0 for s in STATUSES}
    for row in rows:
        out[row["status"]] = int(row["c"])
    return out
