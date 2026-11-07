"""Tests for ``app.tracker.models.assignee``."""

from __future__ import annotations

import pytest
import sqlite3

from app.tracker.models import assignee, project, task


def test_create_minimal(conn):
    aid = assignee.create(conn, "N")
    row = assignee.get(conn, aid)
    assert row["name"] == "N" and row["email"] == ""


def test_create_with_email(conn):
    aid = assignee.create(conn, "N", "n@x")
    assert assignee.get(conn, aid)["email"] == "n@x"


def test_create_duplicate_name_raises(conn):
    assignee.create(conn, "Dup")
    with pytest.raises(sqlite3.IntegrityError):
        assignee.create(conn, "Dup")


def test_get_missing(conn):
    assert assignee.get(conn, 999) is None


def test_get_by_name(conn):
    aid = assignee.create(conn, "Alice")
    assert assignee.get_by_name(conn, "Alice")["id"] == aid


def test_get_by_name_miss(conn):
    assert assignee.get_by_name(conn, "Nobody") is None


def test_list_all_empty(conn):
    assert assignee.list_all(conn) == []


def test_list_all_sorted(conn):
    assignee.create(conn, "Zed")
    assignee.create(conn, "Amy")
    names = [r["name"] for r in assignee.list_all(conn)]
    assert names == ["Amy", "Zed"]


def test_count_empty(conn):
    assert assignee.count(conn) == 0


def test_count_many(conn):
    for i in range(4):
        assignee.create(conn, f"A{i}")
    assert assignee.count(conn) == 4


def test_update_name(conn):
    aid = assignee.create(conn, "Old")
    assignee.update(conn, aid, name="New")
    assert assignee.get(conn, aid)["name"] == "New"


def test_update_email(conn):
    aid = assignee.create(conn, "N")
    assignee.update(conn, aid, email="x@y")
    assert assignee.get(conn, aid)["email"] == "x@y"


def test_update_both(conn):
    aid = assignee.create(conn, "N")
    assignee.update(conn, aid, name="M", email="m@y")
    row = assignee.get(conn, aid)
    assert row["name"] == "M" and row["email"] == "m@y"


def test_update_noop(conn):
    aid = assignee.create(conn, "N")
    assert assignee.update(conn, aid) == 0


def test_delete(conn):
    aid = assignee.create(conn, "N")
    assert assignee.delete(conn, aid) == 1
    assert assignee.get(conn, aid) is None


def test_delete_missing(conn):
    assert assignee.delete(conn, 9999) == 0


def test_delete_nulls_task_assignee(conn):
    aid = assignee.create(conn, "N")
    pid = project.create(conn, "P")
    tid = task.create(conn, pid, "x", assignee_id=aid)
    assignee.delete(conn, aid)
    assert task.get(conn, tid)["assignee_id"] is None


def test_tasks_for_empty(conn):
    aid = assignee.create(conn, "N")
    assert assignee.tasks_for(conn, aid) == []


def test_tasks_for_populated(conn):
    aid = assignee.create(conn, "N")
    pid = project.create(conn, "P")
    task.create(conn, pid, "a", assignee_id=aid)
    task.create(conn, pid, "b")
    rows = assignee.tasks_for(conn, aid)
    assert len(rows) == 1


@pytest.mark.parametrize("n", list(range(1, 11)))
def test_create_many(conn, n):
    for i in range(n):
        assignee.create(conn, f"a_{n}_{i}")
    assert assignee.count(conn) == n


@pytest.mark.parametrize("email", ["", "a@b", "unicode: ün@x"])
def test_email_round_trip(conn, email):
    aid = assignee.create(conn, f"n_{email}", email)
    assert assignee.get(conn, aid)["email"] == email
