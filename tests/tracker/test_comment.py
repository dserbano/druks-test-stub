"""Tests for ``app.tracker.models.comment``."""

from __future__ import annotations

import pytest
import sqlite3

from app.tracker.models import comment, project, task


@pytest.fixture
def ids(conn):
    pid = project.create(conn, "P")
    tid = task.create(conn, pid, "t")
    return pid, tid


def test_create_on_task(conn, ids):
    _, tid = ids
    cid = comment.create_on_task(conn, tid, "body", "me")
    row = comment.get(conn, cid)
    assert row["task_id"] == tid and row["project_id"] is None
    assert row["body"] == "body" and row["author"] == "me"


def test_create_on_project(conn, ids):
    pid, _ = ids
    cid = comment.create_on_project(conn, pid, "pbody", "boss")
    row = comment.get(conn, cid)
    assert row["project_id"] == pid and row["task_id"] is None


def test_get_missing(conn):
    assert comment.get(conn, 999) is None


def test_list_for_task_empty(conn, ids):
    _, tid = ids
    assert comment.list_for_task(conn, tid) == []


def test_list_for_task_filters(conn, ids):
    pid, tid = ids
    comment.create_on_task(conn, tid, "a")
    comment.create_on_project(conn, pid, "p")
    assert len(comment.list_for_task(conn, tid)) == 1


def test_list_for_project_empty(conn, ids):
    pid, _ = ids
    assert comment.list_for_project(conn, pid) == []


def test_list_for_project_filters(conn, ids):
    pid, tid = ids
    comment.create_on_project(conn, pid, "p")
    comment.create_on_task(conn, tid, "t")
    assert len(comment.list_for_project(conn, pid)) == 1


def test_list_all(conn, ids):
    pid, tid = ids
    comment.create_on_task(conn, tid, "a")
    comment.create_on_project(conn, pid, "b")
    assert len(comment.list_all(conn)) == 2


def test_count(conn, ids):
    _, tid = ids
    assert comment.count(conn) == 0
    comment.create_on_task(conn, tid, "x")
    assert comment.count(conn) == 1


def test_update_body(conn, ids):
    _, tid = ids
    cid = comment.create_on_task(conn, tid, "old")
    comment.update(conn, cid, body="new")
    assert comment.get(conn, cid)["body"] == "new"


def test_update_author(conn, ids):
    _, tid = ids
    cid = comment.create_on_task(conn, tid, "x")
    comment.update(conn, cid, author="a")
    assert comment.get(conn, cid)["author"] == "a"


def test_update_both(conn, ids):
    _, tid = ids
    cid = comment.create_on_task(conn, tid, "x")
    comment.update(conn, cid, body="b", author="c")
    row = comment.get(conn, cid)
    assert row["body"] == "b" and row["author"] == "c"


def test_update_noop(conn, ids):
    _, tid = ids
    cid = comment.create_on_task(conn, tid, "x")
    assert comment.update(conn, cid) == 0


def test_delete(conn, ids):
    _, tid = ids
    cid = comment.create_on_task(conn, tid, "x")
    assert comment.delete(conn, cid) == 1
    assert comment.get(conn, cid) is None


def test_delete_missing(conn):
    assert comment.delete(conn, 9999) == 0


def test_cascade_on_task_delete(conn, ids):
    _, tid = ids
    cid = comment.create_on_task(conn, tid, "x")
    task.delete(conn, tid)
    assert comment.get(conn, cid) is None


def test_cascade_on_project_delete(conn, ids):
    pid, _ = ids
    cid = comment.create_on_project(conn, pid, "x")
    project.delete(conn, pid)
    assert comment.get(conn, cid) is None


def test_requires_exactly_one_parent(conn, ids):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO comments(task_id, project_id, body) VALUES (NULL, NULL, 'x')"
        )
        conn.commit()


def test_rejects_both_parents(conn, ids):
    pid, tid = ids
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO comments(task_id, project_id, body) VALUES (?, ?, 'x')",
            (tid, pid),
        )
        conn.commit()


@pytest.mark.parametrize("n", list(range(1, 11)))
def test_many_comments(conn, ids, n):
    _, tid = ids
    for i in range(n):
        comment.create_on_task(conn, tid, f"b{n}-{i}")
    assert len(comment.list_for_task(conn, tid)) == n


@pytest.mark.parametrize("body", ["short", "a" * 200, "unicode: café", "multi\nline"])
def test_body_round_trip(conn, ids, body):
    _, tid = ids
    cid = comment.create_on_task(conn, tid, body)
    assert comment.get(conn, cid)["body"] == body
