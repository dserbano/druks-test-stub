"""Tests for ``app.tracker.models.sprint``."""

from __future__ import annotations

import pytest
import sqlite3

from app.tracker.models import project, sprint, task


@pytest.fixture
def project_id(conn):
    return project.create(conn, "SP")


def test_create(conn, project_id):
    sid = sprint.create(conn, project_id, "S1", "2026-01-01", "2026-01-14")
    row = sprint.get(conn, sid)
    assert row["name"] == "S1"
    assert row["start_date"] == "2026-01-01"
    assert row["end_date"] == "2026-01-14"


def test_create_duplicate_name_same_project(conn, project_id):
    sprint.create(conn, project_id, "S", "2026-01-01", "2026-01-02")
    with pytest.raises(sqlite3.IntegrityError):
        sprint.create(conn, project_id, "S", "2026-02-01", "2026-02-02")


def test_create_same_name_different_projects(conn, project_id):
    other = project.create(conn, "Other")
    sprint.create(conn, project_id, "S", "2026-01-01", "2026-01-02")
    sprint.create(conn, other, "S", "2026-01-01", "2026-01-02")


def test_get_missing(conn):
    assert sprint.get(conn, 999) is None


def test_list_for_project_empty(conn, project_id):
    assert sprint.list_for_project(conn, project_id) == []


def test_list_for_project_sorted(conn, project_id):
    sprint.create(conn, project_id, "B", "2026-02-01", "2026-02-10")
    sprint.create(conn, project_id, "A", "2026-01-01", "2026-01-10")
    names = [r["name"] for r in sprint.list_for_project(conn, project_id)]
    assert names == ["A", "B"]


def test_list_all_sorted(conn, project_id):
    sprint.create(conn, project_id, "A", "2026-01-01", "2026-01-10")
    sprint.create(conn, project_id, "B", "2026-02-01", "2026-02-10")
    names = [r["name"] for r in sprint.list_all(conn)]
    assert names == ["A", "B"]


def test_count(conn, project_id):
    assert sprint.count(conn) == 0
    sprint.create(conn, project_id, "S", "2026-01-01", "2026-01-02")
    assert sprint.count(conn) == 1


def test_update_name(conn, project_id):
    sid = sprint.create(conn, project_id, "O", "2026-01-01", "2026-01-02")
    sprint.update(conn, sid, name="N")
    assert sprint.get(conn, sid)["name"] == "N"


def test_update_dates(conn, project_id):
    sid = sprint.create(conn, project_id, "O", "2026-01-01", "2026-01-02")
    sprint.update(conn, sid, start_date="2026-03-01", end_date="2026-03-15")
    row = sprint.get(conn, sid)
    assert row["start_date"] == "2026-03-01" and row["end_date"] == "2026-03-15"


def test_update_noop(conn, project_id):
    sid = sprint.create(conn, project_id, "O", "2026-01-01", "2026-01-02")
    assert sprint.update(conn, sid) == 0


def test_delete(conn, project_id):
    sid = sprint.create(conn, project_id, "O", "2026-01-01", "2026-01-02")
    assert sprint.delete(conn, sid) == 1
    assert sprint.get(conn, sid) is None


def test_delete_missing(conn):
    assert sprint.delete(conn, 999) == 0


def test_delete_sets_task_sprint_null(conn, project_id):
    sid = sprint.create(conn, project_id, "O", "2026-01-01", "2026-01-02")
    tid = task.create(conn, project_id, "x", sprint_id=sid)
    sprint.delete(conn, sid)
    assert task.get(conn, tid)["sprint_id"] is None


def test_tasks_for_empty(conn, project_id):
    sid = sprint.create(conn, project_id, "S", "2026-01-01", "2026-01-02")
    assert sprint.tasks_for(conn, sid) == []


def test_tasks_for_populated(conn, project_id):
    sid = sprint.create(conn, project_id, "S", "2026-01-01", "2026-01-02")
    task.create(conn, project_id, "a", sprint_id=sid)
    task.create(conn, project_id, "b")
    assert len(sprint.tasks_for(conn, sid)) == 1


def test_project_cascade_deletes_sprints(conn, project_id):
    sid = sprint.create(conn, project_id, "S", "2026-01-01", "2026-01-02")
    project.delete(conn, project_id)
    assert sprint.get(conn, sid) is None


@pytest.mark.parametrize("n", list(range(1, 11)))
def test_many_sprints(conn, project_id, n):
    for i in range(n):
        sprint.create(conn, project_id, f"S{n}-{i}", "2026-01-01", "2026-01-02")
    assert len(sprint.list_for_project(conn, project_id)) == n


@pytest.mark.parametrize("start,end", [
    ("2026-01-01", "2026-01-01"),
    ("2026-01-01", "2026-01-05"),
    ("2026-06-10", "2026-07-15"),
    ("2026-12-31", "2027-01-15"),
])
def test_date_round_trip(conn, project_id, start, end):
    sid = sprint.create(conn, project_id, f"R-{start}", start, end)
    row = sprint.get(conn, sid)
    assert row["start_date"] == start and row["end_date"] == end
