"""Tests for ``app.tracker.models.label``."""

from __future__ import annotations

import pytest
import sqlite3

from app.tracker.models import label, project, task


def test_create_minimal(conn):
    lid = label.create(conn, "bug")
    row = label.get(conn, lid)
    assert row["name"] == "bug" and row["color"] == "#888888"


def test_create_with_color(conn):
    lid = label.create(conn, "feat", "#00ff00")
    assert label.get(conn, lid)["color"] == "#00ff00"


def test_create_duplicate_raises(conn):
    label.create(conn, "dup")
    with pytest.raises(sqlite3.IntegrityError):
        label.create(conn, "dup")


def test_get_missing(conn):
    assert label.get(conn, 999) is None


def test_get_by_name(conn):
    lid = label.create(conn, "n")
    assert label.get_by_name(conn, "n")["id"] == lid


def test_get_by_name_miss(conn):
    assert label.get_by_name(conn, "none") is None


def test_list_all_empty(conn):
    assert label.list_all(conn) == []


def test_list_all_sorted(conn):
    label.create(conn, "z")
    label.create(conn, "a")
    names = [r["name"] for r in label.list_all(conn)]
    assert names == ["a", "z"]


def test_count(conn):
    assert label.count(conn) == 0
    label.create(conn, "l")
    assert label.count(conn) == 1


def test_update_name(conn):
    lid = label.create(conn, "o")
    label.update(conn, lid, name="n")
    assert label.get(conn, lid)["name"] == "n"


def test_update_color(conn):
    lid = label.create(conn, "o")
    label.update(conn, lid, color="#111111")
    assert label.get(conn, lid)["color"] == "#111111"


def test_update_both(conn):
    lid = label.create(conn, "o")
    label.update(conn, lid, name="n", color="#222222")
    row = label.get(conn, lid)
    assert row["name"] == "n" and row["color"] == "#222222"


def test_update_noop(conn):
    lid = label.create(conn, "o")
    assert label.update(conn, lid) == 0


def test_delete(conn):
    lid = label.create(conn, "o")
    assert label.delete(conn, lid) == 1
    assert label.get(conn, lid) is None


def test_delete_missing(conn):
    assert label.delete(conn, 999) == 0


def test_tasks_for_empty(conn):
    lid = label.create(conn, "l")
    assert label.tasks_for(conn, lid) == []


def test_tasks_for_m2m(conn):
    pid = project.create(conn, "P")
    tid = task.create(conn, pid, "t")
    lid = label.create(conn, "l")
    task.attach_label(conn, tid, lid)
    rows = label.tasks_for(conn, lid)
    assert len(rows) == 1 and rows[0]["id"] == tid


def test_delete_label_cascades_join(conn):
    pid = project.create(conn, "P")
    tid = task.create(conn, pid, "t")
    lid = label.create(conn, "l")
    task.attach_label(conn, tid, lid)
    label.delete(conn, lid)
    rows = conn.execute("SELECT * FROM task_labels WHERE label_id = ?", (lid,)).fetchall()
    assert rows == []


@pytest.mark.parametrize("n", list(range(1, 11)))
def test_many_labels(conn, n):
    for i in range(n):
        label.create(conn, f"l_{n}_{i}")
    assert label.count(conn) == n


@pytest.mark.parametrize("color", ["#000000", "#ffffff", "#123abc", "#aabbcc"])
def test_color_round_trip(conn, color):
    lid = label.create(conn, f"c_{color}", color)
    assert label.get(conn, lid)["color"] == color
