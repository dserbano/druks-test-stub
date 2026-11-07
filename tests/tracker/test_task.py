"""Tests for ``app.tracker.models.task``."""

from __future__ import annotations

import pytest

from app.tracker.models import assignee, label, project, sprint, task


@pytest.fixture
def project_id(conn):
    return project.create(conn, "TaskProj")


def test_create_minimal(conn, project_id):
    tid = task.create(conn, project_id, "t1")
    row = task.get(conn, tid)
    assert row["title"] == "t1" and row["status"] == "todo"


def test_create_full_fields(conn, project_id):
    sp = sprint.create(conn, project_id, "S", "2026-01-01", "2026-01-05")
    a = assignee.create(conn, "A1")
    tid = task.create(
        conn, project_id, "full",
        description="d", status="in_progress", estimate=2.5,
        sprint_id=sp, assignee_id=a, completed_at=None,
    )
    row = task.get(conn, tid)
    assert row["description"] == "d"
    assert row["status"] == "in_progress"
    assert row["estimate"] == 2.5
    assert row["sprint_id"] == sp
    assert row["assignee_id"] == a


def test_create_unknown_status_raises(conn, project_id):
    with pytest.raises(ValueError):
        task.create(conn, project_id, "t", status="nope")


def test_get_missing(conn):
    assert task.get(conn, 42) is None


def test_list_for_project_empty(conn, project_id):
    assert task.list_for_project(conn, project_id) == []


def test_list_for_project_filters(conn, project_id):
    other = project.create(conn, "Other")
    task.create(conn, project_id, "a")
    task.create(conn, other, "b")
    rows = task.list_for_project(conn, project_id)
    assert len(rows) == 1 and rows[0]["title"] == "a"


def test_list_for_sprint_filters(conn, project_id):
    sp = sprint.create(conn, project_id, "S", "2026-01-01", "2026-01-05")
    task.create(conn, project_id, "a", sprint_id=sp)
    task.create(conn, project_id, "b")
    rows = task.list_for_sprint(conn, sp)
    assert len(rows) == 1


def test_list_for_assignee_filters(conn, project_id):
    a = assignee.create(conn, "Zed")
    task.create(conn, project_id, "a", assignee_id=a)
    task.create(conn, project_id, "b")
    rows = task.list_for_assignee(conn, a)
    assert len(rows) == 1


def test_list_all(conn, project_id):
    for i in range(3):
        task.create(conn, project_id, f"t{i}")
    assert len(task.list_all(conn)) == 3


def test_count(conn, project_id):
    assert task.count(conn) == 0
    task.create(conn, project_id, "x")
    assert task.count(conn) == 1


def test_update_title(conn, project_id):
    tid = task.create(conn, project_id, "orig")
    task.update(conn, tid, title="new")
    assert task.get(conn, tid)["title"] == "new"


def test_update_status(conn, project_id):
    tid = task.create(conn, project_id, "x")
    task.update(conn, tid, status="done")
    assert task.get(conn, tid)["status"] == "done"


def test_update_bad_status(conn, project_id):
    tid = task.create(conn, project_id, "x")
    with pytest.raises(ValueError):
        task.update(conn, tid, status="??")


def test_update_estimate(conn, project_id):
    tid = task.create(conn, project_id, "x", estimate=1)
    task.update(conn, tid, estimate=9.5)
    assert task.get(conn, tid)["estimate"] == 9.5


def test_update_description(conn, project_id):
    tid = task.create(conn, project_id, "x")
    task.update(conn, tid, description="new")
    assert task.get(conn, tid)["description"] == "new"


def test_update_sprint(conn, project_id):
    sp = sprint.create(conn, project_id, "S", "2026-01-01", "2026-01-02")
    tid = task.create(conn, project_id, "x")
    task.update(conn, tid, sprint_id=sp)
    assert task.get(conn, tid)["sprint_id"] == sp


def test_update_clear_sprint(conn, project_id):
    sp = sprint.create(conn, project_id, "S", "2026-01-01", "2026-01-02")
    tid = task.create(conn, project_id, "x", sprint_id=sp)
    task.update(conn, tid, clear_sprint=True)
    assert task.get(conn, tid)["sprint_id"] is None


def test_update_assignee(conn, project_id):
    a = assignee.create(conn, "N")
    tid = task.create(conn, project_id, "x")
    task.update(conn, tid, assignee_id=a)
    assert task.get(conn, tid)["assignee_id"] == a


def test_update_clear_assignee(conn, project_id):
    a = assignee.create(conn, "N")
    tid = task.create(conn, project_id, "x", assignee_id=a)
    task.update(conn, tid, clear_assignee=True)
    assert task.get(conn, tid)["assignee_id"] is None


def test_update_completed_at(conn, project_id):
    tid = task.create(conn, project_id, "x")
    task.update(conn, tid, completed_at="2026-05-05")
    assert task.get(conn, tid)["completed_at"] == "2026-05-05"


def test_update_clear_completed_at(conn, project_id):
    tid = task.create(conn, project_id, "x", completed_at="2026-01-01")
    task.update(conn, tid, clear_completed_at=True)
    assert task.get(conn, tid)["completed_at"] is None


def test_update_noop_returns_zero(conn, project_id):
    tid = task.create(conn, project_id, "x")
    assert task.update(conn, tid) == 0


def test_mark_done(conn, project_id):
    tid = task.create(conn, project_id, "x")
    task.mark_done(conn, tid, "2026-07-01")
    row = task.get(conn, tid)
    assert row["status"] == "done" and row["completed_at"] == "2026-07-01"


def test_delete(conn, project_id):
    tid = task.create(conn, project_id, "x")
    assert task.delete(conn, tid) == 1
    assert task.get(conn, tid) is None


def test_delete_missing(conn):
    assert task.delete(conn, 9999) == 0


def test_delete_cascades_subtasks(conn, project_id):
    tid = task.create(conn, project_id, "x")
    conn.execute("INSERT INTO subtasks(task_id, title) VALUES (?, 's')", (tid,))
    conn.commit()
    task.delete(conn, tid)
    rows = conn.execute("SELECT * FROM subtasks WHERE task_id = ?", (tid,)).fetchall()
    assert rows == []


def test_attach_label(conn, project_id):
    tid = task.create(conn, project_id, "x")
    lid = label.create(conn, "L")
    task.attach_label(conn, tid, lid)
    labs = task.labels_for(conn, tid)
    assert len(labs) == 1 and labs[0]["name"] == "L"


def test_attach_label_idempotent(conn, project_id):
    tid = task.create(conn, project_id, "x")
    lid = label.create(conn, "L")
    task.attach_label(conn, tid, lid)
    task.attach_label(conn, tid, lid)
    assert len(task.labels_for(conn, tid)) == 1


def test_detach_label(conn, project_id):
    tid = task.create(conn, project_id, "x")
    lid = label.create(conn, "L")
    task.attach_label(conn, tid, lid)
    assert task.detach_label(conn, tid, lid) == 1
    assert task.labels_for(conn, tid) == []


def test_detach_label_missing(conn, project_id):
    tid = task.create(conn, project_id, "x")
    assert task.detach_label(conn, tid, 999) == 0


def test_set_labels_replaces(conn, project_id):
    tid = task.create(conn, project_id, "x")
    a = label.create(conn, "A")
    b = label.create(conn, "B")
    c = label.create(conn, "C")
    task.attach_label(conn, tid, a)
    task.set_labels(conn, tid, [b, c])
    names = sorted(r["name"] for r in task.labels_for(conn, tid))
    assert names == ["B", "C"]


def test_count_by_status_empty(conn):
    counts = task.count_by_status(conn)
    assert counts == {"todo": 0, "in_progress": 0, "blocked": 0, "done": 0}


def test_count_by_status_mixed(conn, project_id):
    task.create(conn, project_id, "a")
    task.create(conn, project_id, "b", status="done")
    task.create(conn, project_id, "c", status="done")
    task.create(conn, project_id, "d", status="blocked")
    counts = task.count_by_status(conn)
    assert counts == {"todo": 1, "in_progress": 0, "blocked": 1, "done": 2}


def test_count_by_status_project_scope(conn, project_id):
    other = project.create(conn, "Other")
    task.create(conn, project_id, "a", status="done")
    task.create(conn, other, "b", status="done")
    counts = task.count_by_status(conn, project_id)
    assert counts["done"] == 1


@pytest.mark.parametrize("status", ["todo", "in_progress", "blocked", "done"])
def test_create_each_status(conn, project_id, status):
    tid = task.create(conn, project_id, "x", status=status)
    assert task.get(conn, tid)["status"] == status


@pytest.mark.parametrize("status", ["todo", "in_progress", "blocked", "done"])
def test_update_each_status(conn, project_id, status):
    tid = task.create(conn, project_id, "x")
    task.update(conn, tid, status=status)
    assert task.get(conn, tid)["status"] == status


@pytest.mark.parametrize("n", list(range(0, 8)))
def test_subtask_fk_cascade_count(conn, project_id, n):
    tid = task.create(conn, project_id, "x")
    for i in range(n):
        conn.execute("INSERT INTO subtasks(task_id, title) VALUES (?, ?)", (tid, f"s{i}"))
    conn.commit()
    task.delete(conn, tid)
    assert conn.execute("SELECT COUNT(*) AS c FROM subtasks WHERE task_id=?", (tid,)).fetchone()["c"] == 0


@pytest.mark.parametrize("n", list(range(1, 8)))
def test_create_many_in_project(conn, project_id, n):
    for i in range(n):
        task.create(conn, project_id, f"t{n}-{i}")
    assert len(task.list_for_project(conn, project_id)) == n
