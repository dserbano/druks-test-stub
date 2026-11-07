"""Tests for ``app.tracker.models.subtask``."""

from __future__ import annotations

import pytest

from app.tracker.models import project, subtask, task


@pytest.fixture
def task_id(conn):
    pid = project.create(conn, "SubProj")
    return task.create(conn, pid, "t")


def test_create_minimal(conn, task_id):
    sid = subtask.create(conn, task_id, "s")
    row = subtask.get(conn, sid)
    assert row["title"] == "s" and row["done"] == 0


def test_create_done_true(conn, task_id):
    sid = subtask.create(conn, task_id, "s", done=True)
    assert subtask.get(conn, sid)["done"] == 1


def test_get_missing(conn):
    assert subtask.get(conn, 999) is None


def test_list_for_task_empty(conn, task_id):
    assert subtask.list_for_task(conn, task_id) == []


def test_list_for_task_order(conn, task_id):
    a = subtask.create(conn, task_id, "a")
    b = subtask.create(conn, task_id, "b")
    c = subtask.create(conn, task_id, "c")
    ids = [r["id"] for r in subtask.list_for_task(conn, task_id)]
    assert ids == [a, b, c]


def test_list_filters_by_task(conn):
    pid = project.create(conn, "P")
    t1 = task.create(conn, pid, "t1")
    t2 = task.create(conn, pid, "t2")
    subtask.create(conn, t1, "a")
    subtask.create(conn, t2, "b")
    assert len(subtask.list_for_task(conn, t1)) == 1


def test_update_title(conn, task_id):
    sid = subtask.create(conn, task_id, "s")
    subtask.update(conn, sid, title="new")
    assert subtask.get(conn, sid)["title"] == "new"


def test_update_done(conn, task_id):
    sid = subtask.create(conn, task_id, "s")
    subtask.update(conn, sid, done=True)
    assert subtask.get(conn, sid)["done"] == 1


def test_update_done_false(conn, task_id):
    sid = subtask.create(conn, task_id, "s", done=True)
    subtask.update(conn, sid, done=False)
    assert subtask.get(conn, sid)["done"] == 0


def test_update_noop(conn, task_id):
    sid = subtask.create(conn, task_id, "s")
    assert subtask.update(conn, sid) == 0


def test_mark_done(conn, task_id):
    sid = subtask.create(conn, task_id, "s")
    subtask.mark_done(conn, sid)
    assert subtask.get(conn, sid)["done"] == 1


def test_mark_open(conn, task_id):
    sid = subtask.create(conn, task_id, "s", done=True)
    subtask.mark_open(conn, sid)
    assert subtask.get(conn, sid)["done"] == 0


def test_delete(conn, task_id):
    sid = subtask.create(conn, task_id, "s")
    assert subtask.delete(conn, sid) == 1
    assert subtask.get(conn, sid) is None


def test_delete_missing(conn):
    assert subtask.delete(conn, 9999) == 0


def test_count_for_task_empty(conn, task_id):
    assert subtask.count_for_task(conn, task_id) == 0


def test_count_for_task_many(conn, task_id):
    for i in range(5):
        subtask.create(conn, task_id, f"s{i}")
    assert subtask.count_for_task(conn, task_id) == 5


def test_done_fraction_empty(conn, task_id):
    assert subtask.done_fraction(conn, task_id) == 0.0


def test_done_fraction_half(conn, task_id):
    subtask.create(conn, task_id, "a", done=True)
    subtask.create(conn, task_id, "b", done=False)
    assert subtask.done_fraction(conn, task_id) == 0.5


def test_done_fraction_all(conn, task_id):
    subtask.create(conn, task_id, "a", done=True)
    subtask.create(conn, task_id, "b", done=True)
    assert subtask.done_fraction(conn, task_id) == 1.0


def test_done_fraction_none(conn, task_id):
    subtask.create(conn, task_id, "a")
    subtask.create(conn, task_id, "b")
    assert subtask.done_fraction(conn, task_id) == 0.0


@pytest.mark.parametrize("n", list(range(1, 11)))
def test_create_many(conn, task_id, n):
    for i in range(n):
        subtask.create(conn, task_id, f"s_{n}_{i}")
    assert subtask.count_for_task(conn, task_id) == n


@pytest.mark.parametrize("flag", [True, False])
def test_flag_round_trip(conn, task_id, flag):
    sid = subtask.create(conn, task_id, "x", done=flag)
    assert subtask.get(conn, sid)["done"] == (1 if flag else 0)
