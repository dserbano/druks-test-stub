"""Render the static HTML dashboard from Jinja templates."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.tracker import burndown as burndown_mod
from app.tracker import search as search_mod

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2", "html.j2"]),
    )


def _assignee_open_counts(conn: sqlite3.Connection):
    return conn.execute(
        """
        SELECT assignees.name AS name,
               SUM(CASE WHEN tasks.status != 'done' THEN 1 ELSE 0 END) AS open_count
        FROM assignees
        LEFT JOIN tasks ON tasks.assignee_id = assignees.id
        GROUP BY assignees.id
        ORDER BY assignees.name
        """
    ).fetchall()


def _pick_sprint(conn: sqlite3.Connection, sprint_id: Optional[int]):
    if sprint_id is not None:
        return conn.execute(
            "SELECT * FROM sprints WHERE id = ?", (sprint_id,)
        ).fetchone()
    return conn.execute("SELECT * FROM sprints ORDER BY start_date LIMIT 1").fetchone()


def render(
    conn: sqlite3.Connection,
    output_path: os.PathLike,
    *,
    search_term: str = "",
    sprint_id: Optional[int] = None,
) -> Path:
    """Render the dashboard to ``output_path`` and return that path."""
    env = _env()
    template = env.get_template("dashboard.html.j2")

    projects = conn.execute(
        "SELECT id, name, description FROM projects ORDER BY name"
    ).fetchall()
    sprint = _pick_sprint(conn, sprint_id)
    points = burndown_mod.compute(conn, sprint["id"]) if sprint is not None else []
    hits = search_mod.search_all(conn, search_term) if search_term else []
    assignees = _assignee_open_counts(conn)

    html = template.render(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
        projects=projects,
        burndown_sprint=sprint,
        burndown=[p.as_dict() for p in points],
        search_term=search_term,
        search_hits=[h.as_dict() for h in hits],
        assignees=assignees,
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def render_string(
    conn: sqlite3.Connection,
    *,
    search_term: str = "",
    sprint_id: Optional[int] = None,
) -> str:
    env = _env()
    template = env.get_template("dashboard.html.j2")
    projects = conn.execute(
        "SELECT id, name, description FROM projects ORDER BY name"
    ).fetchall()
    sprint = _pick_sprint(conn, sprint_id)
    points = burndown_mod.compute(conn, sprint["id"]) if sprint is not None else []
    hits = search_mod.search_all(conn, search_term) if search_term else []
    assignees = _assignee_open_counts(conn)
    return template.render(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
        projects=projects,
        burndown_sprint=sprint,
        burndown=[p.as_dict() for p in points],
        search_term=search_term,
        search_hits=[h.as_dict() for h in hits],
        assignees=assignees,
    )
