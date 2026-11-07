"""Tests for ``app.tracker.models.project``."""

from __future__ import annotations

import pytest
import sqlite3

from app.tracker.models import project


def test_create_returns_int_id(conn):
    pid = project.create(conn, "P1")
    assert isinstance(pid, int) and pid > 0


def test_create_with_description(conn):
    pid = project.create(conn, "P2", "a project")
    row = project.get(conn, pid)
    assert row["description"] == "a project"


def test_create_default_description_blank(conn):
    pid = project.create(conn, "P3")
    row = project.get(conn, pid)
    assert row["description"] == ""


def test_create_duplicate_name_raises(conn):
    project.create(conn, "Dup")
    with pytest.raises(sqlite3.IntegrityError):
        project.create(conn, "Dup")


def test_get_missing_returns_none(conn):
    assert project.get(conn, 9999) is None


def test_get_by_name_hit(conn):
    pid = project.create(conn, "Named")
    row = project.get_by_name(conn, "Named")
    assert row["id"] == pid


def test_get_by_name_miss(conn):
    assert project.get_by_name(conn, "Nope") is None


def test_list_all_empty(conn):
    assert project.list_all(conn) == []


def test_list_all_sorted(conn):
    project.create(conn, "Bravo")
    project.create(conn, "Alpha")
    project.create(conn, "Charlie")
    names = [r["name"] for r in project.list_all(conn)]
    assert names == ["Alpha", "Bravo", "Charlie"]


def test_count_empty(conn):
    assert project.count(conn) == 0


def test_count_after_insert(conn):
    project.create(conn, "A")
    project.create(conn, "B")
    assert project.count(conn) == 2


def test_update_name(conn):
    pid = project.create(conn, "Old")
    assert project.update(conn, pid, name="New") == 1
    assert project.get(conn, pid)["name"] == "New"


def test_update_description(conn):
    pid = project.create(conn, "Any")
    project.update(conn, pid, description="hi")
    assert project.get(conn, pid)["description"] == "hi"


def test_update_both(conn):
    pid = project.create(conn, "X")
    project.update(conn, pid, name="Y", description="d")
    row = project.get(conn, pid)
    assert row["name"] == "Y" and row["description"] == "d"


def test_update_noop(conn):
    pid = project.create(conn, "No")
    assert project.update(conn, pid) == 0


def test_update_missing_returns_zero(conn):
    assert project.update(conn, 9999, name="x") == 0


def test_delete(conn):
    pid = project.create(conn, "Del")
    assert project.delete(conn, pid) == 1
    assert project.get(conn, pid) is None


def test_delete_missing(conn):
    assert project.delete(conn, 9999) == 0


@pytest.mark.parametrize("n", list(range(1, 11)))
def test_create_many(conn, n):
    for i in range(n):
        project.create(conn, f"P_{n}_{i}")
    assert project.count(conn) == n


@pytest.mark.parametrize("desc", ["", "short", "a" * 500, "unicode: café"])
def test_description_round_trip(conn, desc):
    pid = project.create(conn, f"D-{len(desc)}", desc)
    assert project.get(conn, pid)["description"] == desc


def test_created_at_populated(conn):
    pid = project.create(conn, "T")
    assert project.get(conn, pid)["created_at"]


def test_update_preserves_other_field(conn):
    pid = project.create(conn, "Keep", "original")
    project.update(conn, pid, name="Keep2")
    row = project.get(conn, pid)
    assert row["description"] == "original"


def test_delete_cascades_tasks(conn):
    pid = project.create(conn, "WithTasks")
    conn.execute("INSERT INTO tasks(project_id, title) VALUES (?, 'x')", (pid,))
    conn.commit()
    project.delete(conn, pid)
    rows = conn.execute("SELECT * FROM tasks WHERE project_id = ?", (pid,)).fetchall()
    assert rows == []
