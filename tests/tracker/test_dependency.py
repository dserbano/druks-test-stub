"""Tests for ``app.tracker.models.dependency``."""

from __future__ import annotations

import pytest

from app.tracker.models import dependency, project, task


@pytest.fixture
def two_tasks(conn):
    pid = project.create(conn, "P")
    a = task.create(conn, pid, "a")
    b = task.create(conn, pid, "b")
    return a, b


def test_create_default_kind(conn, two_tasks):
    a, b = two_tasks
    did = dependency.create(conn, a, b)
    row = dependency.get(conn, did)
    assert row["kind"] == "blocks"


@pytest.mark.parametrize("kind", ["blocks", "relates_to", "duplicates"])
def test_create_each_kind(conn, two_tasks, kind):
    a, b = two_tasks
    did = dependency.create(conn, a, b, kind=kind)
    assert dependency.get(conn, did)["kind"] == kind


def test_create_unknown_kind_raises(conn, two_tasks):
    a, b = two_tasks
    with pytest.raises(ValueError):
        dependency.create(conn, a, b, kind="??")


def test_self_dependency_raises(conn, two_tasks):
    a, _ = two_tasks
    with pytest.raises(ValueError):
        dependency.create(conn, a, a)


def test_duplicate_edge_raises(conn, two_tasks):
    a, b = two_tasks
    dependency.create(conn, a, b)
    with pytest.raises(Exception):
        dependency.create(conn, a, b)


def test_different_kinds_allowed(conn, two_tasks):
    a, b = two_tasks
    dependency.create(conn, a, b, "blocks")
    dependency.create(conn, a, b, "relates_to")
    assert len(dependency.list_all(conn)) == 2


def test_get_missing(conn):
    assert dependency.get(conn, 999) is None


def test_outgoing(conn, two_tasks):
    a, b = two_tasks
    dependency.create(conn, a, b)
    out = dependency.outgoing(conn, a)
    assert len(out) == 1 and out[0]["to_task_id"] == b


def test_incoming(conn, two_tasks):
    a, b = two_tasks
    dependency.create(conn, a, b)
    inc = dependency.incoming(conn, b)
    assert len(inc) == 1 and inc[0]["from_task_id"] == a


def test_list_all_empty(conn):
    assert dependency.list_all(conn) == []


def test_list_all_many(conn):
    pid = project.create(conn, "Q")
    ids = [task.create(conn, pid, f"t{i}") for i in range(4)]
    dependency.create(conn, ids[0], ids[1])
    dependency.create(conn, ids[1], ids[2])
    dependency.create(conn, ids[2], ids[3])
    assert len(dependency.list_all(conn)) == 3


def test_update_kind(conn, two_tasks):
    a, b = two_tasks
    did = dependency.create(conn, a, b)
    assert dependency.update(conn, did, kind="relates_to") == 1
    assert dependency.get(conn, did)["kind"] == "relates_to"


def test_update_bad_kind(conn, two_tasks):
    a, b = two_tasks
    did = dependency.create(conn, a, b)
    with pytest.raises(ValueError):
        dependency.update(conn, did, kind="??")


def test_update_noop(conn, two_tasks):
    a, b = two_tasks
    did = dependency.create(conn, a, b)
    assert dependency.update(conn, did) == 0


def test_delete(conn, two_tasks):
    a, b = two_tasks
    did = dependency.create(conn, a, b)
    assert dependency.delete(conn, did) == 1
    assert dependency.get(conn, did) is None


def test_delete_missing(conn):
    assert dependency.delete(conn, 9999) == 0


def test_delete_cascade_on_task(conn, two_tasks):
    a, b = two_tasks
    did = dependency.create(conn, a, b)
    task.delete(conn, a)
    assert dependency.get(conn, did) is None


def test_blockers_for_only_blocks_kind(conn, two_tasks):
    a, b = two_tasks
    dependency.create(conn, a, b, "blocks")
    c = task.create(conn, 1, "c")
    dependency.create(conn, c, b, "relates_to")
    blockers = dependency.blockers_for(conn, b)
    assert len(blockers) == 1 and blockers[0]["id"] == a


def test_blocked_by_count(conn, two_tasks):
    a, b = two_tasks
    dependency.create(conn, a, b)
    assert dependency.blocked_by_count(conn, b) == 1


def test_blocked_by_count_zero(conn, two_tasks):
    _, b = two_tasks
    assert dependency.blocked_by_count(conn, b) == 0


@pytest.mark.parametrize("kind", ["blocks", "relates_to", "duplicates"])
def test_update_each_kind(conn, two_tasks, kind):
    a, b = two_tasks
    did = dependency.create(conn, a, b)
    dependency.update(conn, did, kind=kind)
    assert dependency.get(conn, did)["kind"] == kind


@pytest.mark.parametrize("fanout", list(range(1, 7)))
def test_fanout_blockers(conn, fanout):
    pid = project.create(conn, f"F{fanout}")
    target = task.create(conn, pid, "target")
    for i in range(fanout):
        src = task.create(conn, pid, f"src{i}")
        dependency.create(conn, src, target)
    assert dependency.blocked_by_count(conn, target) == fanout
