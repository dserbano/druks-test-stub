"""Tests for ``app.tracker.search``."""

from __future__ import annotations

import pytest

from app.tracker import search
from app.tracker.models import comment, project, task


def test_search_projects_empty(conn):
    assert search.search_projects(conn, "anything") == []


def test_search_tasks_empty(conn):
    assert search.search_tasks(conn, "anything") == []


def test_search_comments_empty(conn):
    assert search.search_comments(conn, "anything") == []


def test_search_projects_hit(conn):
    pid = project.create(conn, "Alpha", "the quick brown fox")
    hits = search.search_projects(conn, "brown")
    assert len(hits) == 1 and hits[0].rowid == pid


def test_search_tasks_hit(conn):
    pid = project.create(conn, "P")
    tid = task.create(conn, pid, "widget", description="the lazy dog")
    hits = search.search_tasks(conn, "lazy")
    assert len(hits) == 1 and hits[0].rowid == tid


def test_search_comments_hit(conn):
    pid = project.create(conn, "P")
    tid = task.create(conn, pid, "t")
    cid = comment.create_on_task(conn, tid, "an urgent concern")
    hits = search.search_comments(conn, "urgent")
    assert len(hits) == 1 and hits[0].rowid == cid


def test_search_all_crosses_kinds(conn):
    pid = project.create(conn, "match-me", "")
    task.create(conn, pid, "match-me title")
    comment.create_on_project(conn, pid, "match-me comment")
    hits = search.search_all(conn, "match-me")
    kinds = {h.kind for h in hits}
    assert kinds >= {"project", "task", "comment"}


def test_search_empty_term_returns_empty(conn):
    assert search.search_tasks(conn, "") == []
    assert search.search_tasks(conn, "   ") == []


def test_search_result_shape(conn):
    pid = project.create(conn, "A", "match found here")
    hits = search.search_projects(conn, "match")
    assert hits[0].kind == "project"
    assert hits[0].rowid == pid
    assert "match" in hits[0].snippet.lower() or "[" in hits[0].snippet


def test_search_rank_sorted(conn):
    task.create(conn, project.create(conn, "p1"), "apple")
    task.create(conn, project.create(conn, "p2"), "apple apple apple")
    hits = search.search_tasks(conn, "apple")
    assert len(hits) == 2
    assert hits[0].rank <= hits[1].rank


def test_search_hit_as_dict(conn):
    project.create(conn, "Alpha", "cat")
    hit = search.search_projects(conn, "cat")[0]
    d = hit.as_dict()
    assert d["kind"] == "project"
    assert "snippet" in d and "rank" in d


def test_search_tracks_updates(conn):
    pid = project.create(conn, "Updateable", "banana")
    assert search.search_projects(conn, "banana")
    project_mod_update_desc(conn, pid, "pear")
    assert not search.search_projects(conn, "banana")
    assert search.search_projects(conn, "pear")


def project_mod_update_desc(conn, pid, desc):
    conn.execute("UPDATE projects SET description = ? WHERE id = ?", (desc, pid))
    conn.commit()


def test_search_tracks_deletes(conn):
    pid = project.create(conn, "DelMe", "purple")
    assert search.search_projects(conn, "purple")
    project.delete(conn, pid)
    assert not search.search_projects(conn, "purple")


def test_search_limit(conn):
    pid = project.create(conn, "P")
    for i in range(10):
        task.create(conn, pid, f"needle-{i}")
    hits = search.search_tasks(conn, "needle", limit=3)
    assert len(hits) == 3


def test_rebuild_indexes(conn):
    pid = project.create(conn, "Any", "content here")
    search.rebuild_indexes(conn)
    assert search.search_projects(conn, "content")


def test_reindex_project_runs(conn):
    pid = project.create(conn, "Any", "whatever")
    search.reindex_project(conn)


@pytest.mark.parametrize("term,expected", [
    ("", 0),
    ("   ", 0),
    ("nomatch", 0),
    ("alpha", 1),
])
def test_param_terms(conn, term, expected):
    project.create(conn, "Alpha", "alpha gets a hit")
    assert len(search.search_projects(conn, term)) == expected


@pytest.mark.parametrize("n", list(range(1, 6)))
def test_many_tasks_search(conn, n):
    pid = project.create(conn, f"P{n}")
    for i in range(n):
        task.create(conn, pid, f"carrot {i}")
    hits = search.search_tasks(conn, "carrot")
    assert len(hits) == n


def test_search_comment_update(conn):
    pid = project.create(conn, "P")
    tid = task.create(conn, pid, "t")
    cid = comment.create_on_task(conn, tid, "apple")
    assert search.search_comments(conn, "apple")
    conn.execute("UPDATE comments SET body = ? WHERE id = ?", ("pear", cid))
    conn.commit()
    assert not search.search_comments(conn, "apple")
    assert search.search_comments(conn, "pear")


def test_search_task_delete(conn):
    pid = project.create(conn, "P")
    tid = task.create(conn, pid, "mangosteen")
    assert search.search_tasks(conn, "mangosteen")
    task.delete(conn, tid)
    assert not search.search_tasks(conn, "mangosteen")
