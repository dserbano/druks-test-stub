"""Tests for ``app.tracker.burndown``."""

from __future__ import annotations

import pytest

from app.tracker import burndown
from app.tracker.models import project, sprint, task


def _make_sprint(conn, name="S", start="2026-01-01", end="2026-01-05"):
    pid = project.create(conn, f"P-{name}")
    return pid, sprint.create(conn, pid, name, start, end)


def test_compute_missing_sprint(conn):
    assert burndown.compute(conn, 999) == []


def test_compute_empty_sprint(conn):
    _, sid = _make_sprint(conn)
    points = burndown.compute(conn, sid)
    assert len(points) == 5
    assert all(p.remaining == 0.0 and p.completed == 0.0 for p in points)


def test_compute_days_counts(conn):
    _, sid = _make_sprint(conn, start="2026-01-01", end="2026-01-10")
    points = burndown.compute(conn, sid)
    assert len(points) == 10


def test_compute_total_and_remaining(conn):
    pid, sid = _make_sprint(conn)
    task.create(conn, pid, "a", estimate=3, sprint_id=sid)
    task.create(conn, pid, "b", estimate=2, sprint_id=sid)
    points = burndown.compute(conn, sid)
    assert points[0].remaining == 5.0
    assert points[-1].remaining == 5.0


def test_compute_completed_counts_on_day(conn):
    pid, sid = _make_sprint(conn, start="2026-01-01", end="2026-01-05")
    task.create(conn, pid, "a", estimate=4, sprint_id=sid, status="done", completed_at="2026-01-03")
    points = burndown.compute(conn, sid)
    assert points[0].remaining == 4.0
    assert points[2].remaining == 0.0
    assert points[2].completed == 4.0


def test_compute_completed_after_end_not_counted(conn):
    pid, sid = _make_sprint(conn, start="2026-01-01", end="2026-01-03")
    task.create(conn, pid, "a", estimate=4, sprint_id=sid,
                status="done", completed_at="2026-02-10")
    points = burndown.compute(conn, sid)
    assert points[-1].completed == 0.0


def test_compute_null_completed_at_pending(conn):
    pid, sid = _make_sprint(conn)
    task.create(conn, pid, "a", estimate=2, sprint_id=sid)
    points = burndown.compute(conn, sid)
    assert points[-1].remaining == 2.0


def test_compute_multiple_completions(conn):
    pid, sid = _make_sprint(conn, start="2026-01-01", end="2026-01-05")
    task.create(conn, pid, "a", estimate=1, sprint_id=sid, status="done", completed_at="2026-01-02")
    task.create(conn, pid, "b", estimate=2, sprint_id=sid, status="done", completed_at="2026-01-04")
    task.create(conn, pid, "c", estimate=3, sprint_id=sid)
    points = burndown.compute(conn, sid)
    assert [p.remaining for p in points] == [6.0, 5.0, 5.0, 3.0, 3.0]


def test_as_series_dicts(conn):
    _, sid = _make_sprint(conn)
    points = burndown.compute(conn, sid)
    series = burndown.as_series(points)
    assert isinstance(series, list) and all(isinstance(p, dict) for p in series)
    assert set(series[0].keys()) == {"day", "remaining", "completed"}


def test_summary_empty(conn):
    assert burndown.summary(conn, 999) == {
        "days": 0, "total": 0.0, "remaining_end": 0.0, "completed_end": 0.0,
    }


def test_summary_nonempty(conn):
    pid, sid = _make_sprint(conn)
    task.create(conn, pid, "a", estimate=3, sprint_id=sid)
    s = burndown.summary(conn, sid)
    assert s["days"] == 5 and s["total"] == 3.0 and s["remaining_end"] == 3.0


def test_ideal_series_length(conn):
    _, sid = _make_sprint(conn, start="2026-01-01", end="2026-01-10")
    ideal = burndown.ideal(conn, sid)
    assert len(ideal) == 10


def test_ideal_series_endpoints(conn):
    pid, sid = _make_sprint(conn, start="2026-01-01", end="2026-01-05")
    task.create(conn, pid, "a", estimate=4, sprint_id=sid)
    ideal = burndown.ideal(conn, sid)
    assert ideal[0] == 4.0
    assert ideal[-1] == 0.0


def test_ideal_single_day(conn):
    _, sid = _make_sprint(conn, start="2026-01-01", end="2026-01-01")
    pid = conn.execute("SELECT project_id FROM sprints WHERE id=?", (sid,)).fetchone()[0]
    task.create(conn, pid, "a", estimate=3, sprint_id=sid)
    assert burndown.ideal(conn, sid) == [3.0]


def test_ideal_missing_sprint(conn):
    assert burndown.ideal(conn, 999) == []


def test_point_as_dict(conn):
    _, sid = _make_sprint(conn)
    pt = burndown.compute(conn, sid)[0]
    d = pt.as_dict()
    assert d["day"] == "2026-01-01"


@pytest.mark.parametrize("days", list(range(1, 11)))
def test_days_param(conn, days):
    pid = project.create(conn, f"PP{days}")
    end = f"2026-01-{days:02d}"
    sid = sprint.create(conn, pid, "x", "2026-01-01", end)
    assert len(burndown.compute(conn, sid)) == days


@pytest.mark.parametrize("est", [0, 0.5, 1, 1.5, 2, 2.5, 3, 7.25])
def test_estimate_scales_total(conn, est):
    pid = project.create(conn, f"E{est}")
    sid = sprint.create(conn, pid, "x", "2026-01-01", "2026-01-02")
    task.create(conn, pid, "a", estimate=est, sprint_id=sid)
    points = burndown.compute(conn, sid)
    assert points[0].remaining == float(est)
