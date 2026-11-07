"""Sprint burndown series.

Given a sprint with ``start_date`` and ``end_date`` (ISO ``YYYY-MM-DD``),
compute remaining estimate per day. ``remaining`` on day ``d`` is the sum
of estimates of tasks whose ``completed_at`` is either NULL or strictly
after end-of-day ``d``.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterator, List, Optional


@dataclass
class BurndownPoint:
    day: str
    remaining: float
    completed: float

    def as_dict(self) -> dict:
        return {"day": self.day, "remaining": self.remaining, "completed": self.completed}


def _parse_date(s: str) -> date:
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def _iter_days(start: date, end: date) -> Iterator[date]:
    day = start
    while day <= end:
        yield day
        day = day + timedelta(days=1)


def compute(conn: sqlite3.Connection, sprint_id: int) -> List[BurndownPoint]:
    sprint = conn.execute(
        "SELECT * FROM sprints WHERE id = ?", (sprint_id,)
    ).fetchone()
    if sprint is None:
        return []
    start = _parse_date(sprint["start_date"])
    end = _parse_date(sprint["end_date"])
    rows = conn.execute(
        "SELECT estimate, completed_at FROM tasks WHERE sprint_id = ?",
        (sprint_id,),
    ).fetchall()
    total = sum(float(r["estimate"]) for r in rows)
    series: List[BurndownPoint] = []
    for day in _iter_days(start, end):
        completed = 0.0
        for row in rows:
            ca = row["completed_at"]
            if ca is None:
                continue
            try:
                cd = _parse_date(ca)
            except ValueError:
                continue
            if cd <= day:
                completed += float(row["estimate"])
        series.append(
            BurndownPoint(
                day=day.isoformat(),
                remaining=round(total - completed, 6),
                completed=round(completed, 6),
            )
        )
    return series


def as_series(points: List[BurndownPoint]) -> List[dict]:
    return [p.as_dict() for p in points]


def ideal(conn: sqlite3.Connection, sprint_id: int) -> List[float]:
    sprint = conn.execute(
        "SELECT * FROM sprints WHERE id = ?", (sprint_id,)
    ).fetchone()
    if sprint is None:
        return []
    start = _parse_date(sprint["start_date"])
    end = _parse_date(sprint["end_date"])
    days = list(_iter_days(start, end))
    n = len(days)
    if n == 0:
        return []
    rows = conn.execute(
        "SELECT estimate FROM tasks WHERE sprint_id = ?",
        (sprint_id,),
    ).fetchall()
    total = sum(float(r["estimate"]) for r in rows)
    if n == 1:
        return [total]
    return [round(total * (1 - i / (n - 1)), 6) for i in range(n)]


def summary(conn: sqlite3.Connection, sprint_id: int) -> dict:
    points = compute(conn, sprint_id)
    if not points:
        return {"days": 0, "total": 0.0, "remaining_end": 0.0, "completed_end": 0.0}
    return {
        "days": len(points),
        "total": points[0].remaining + points[0].completed,
        "remaining_end": points[-1].remaining,
        "completed_end": points[-1].completed,
    }
