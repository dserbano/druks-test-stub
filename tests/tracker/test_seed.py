"""Tests for ``app.tracker.seed``."""

from __future__ import annotations

import pytest

from app.tracker import seed
from app.tracker.models import (
    assignee, comment, dependency, label, project, sprint, subtask, task,
)


def test_run_returns_counts_dict(conn):
    counts = seed.run(conn)
    assert isinstance(counts, dict)


def test_expected_counts_matches_run(conn):
    counts = seed.run(conn)
    assert counts == seed.expected_counts()


@pytest.mark.parametrize("entity,module", [
    ("projects", project),
    ("assignees", assignee),
    ("sprints", sprint),
    ("tasks", task),
    ("labels", label),
    ("comments", comment),
])
def test_entity_count_matches(conn, entity, module):
    counts = seed.run(conn)
    assert module.count(conn) == counts[entity]


def test_subtasks_count_matches(conn):
    counts = seed.run(conn)
    rows = conn.execute("SELECT COUNT(*) AS c FROM subtasks").fetchone()
    assert rows["c"] == counts["subtasks"]


def test_dependencies_count_matches(conn):
    counts = seed.run(conn)
    rows = conn.execute("SELECT COUNT(*) AS c FROM dependencies").fetchone()
    assert rows["c"] == counts["dependencies"]


def test_projects_have_sprints(conn):
    seed.run(conn)
    rows = conn.execute("SELECT project_id, COUNT(*) AS c FROM sprints GROUP BY project_id").fetchall()
    assert all(r["c"] >= 1 for r in rows)


def test_at_least_two_sprints(conn):
    seed.run(conn)
    assert sprint.count(conn) >= 2


def test_some_task_has_dependency(conn):
    seed.run(conn)
    rows = dependency.list_all(conn)
    assert len(rows) >= 1


def test_labels_attached(conn):
    seed.run(conn)
    rows = conn.execute("SELECT COUNT(*) AS c FROM task_labels").fetchone()
    assert rows["c"] >= 1


def test_comments_on_tasks_and_projects(conn):
    seed.run(conn)
    task_comments = conn.execute(
        "SELECT COUNT(*) AS c FROM comments WHERE task_id IS NOT NULL"
    ).fetchone()["c"]
    project_comments = conn.execute(
        "SELECT COUNT(*) AS c FROM comments WHERE project_id IS NOT NULL"
    ).fetchone()["c"]
    assert task_comments >= 1 and project_comments >= 1


def test_run_against_clean_db(empty_conn):
    from app.tracker import migrations
    migrations.apply(empty_conn)
    seed.run(empty_conn)
    assert project.count(empty_conn) >= 1


def test_run_populates_fts_indexes(conn):
    from app.tracker import search
    seed.run(conn)
    assert search.search_tasks(conn, "cache")


def test_expected_counts_copy(conn):
    a = seed.expected_counts()
    b = seed.expected_counts()
    assert a == b and a is not b
