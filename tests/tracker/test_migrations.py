"""Tests for ``app.tracker.migrations``."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.tracker import db
from app.tracker import migrations

CORE_TABLES = [
    "projects",
    "assignees",
    "sprints",
    "tasks",
    "subtasks",
    "dependencies",
    "labels",
    "task_labels",
    "comments",
]

FTS_TABLES = ["projects_fts", "tasks_fts", "comments_fts"]


def test_discover_finds_at_least_one():
    files = migrations.discover()
    assert len(files) >= 1


def test_discover_sorted():
    files = migrations.discover()
    versions = [v for v, _ in files]
    assert versions == sorted(versions)


def test_discover_versions_are_four_digit():
    for version, _ in migrations.discover():
        assert len(version) == 4
        assert version.isdigit()


def test_discover_paths_exist():
    for _, path in migrations.discover():
        assert Path(path).is_file()


def test_apply_from_empty_returns_versions(empty_conn):
    applied = migrations.apply(empty_conn)
    assert applied, "expected at least one migration"
    assert "0001" in applied


def test_apply_is_idempotent(empty_conn):
    first = migrations.apply(empty_conn)
    second = migrations.apply(empty_conn)
    assert first and not second


def test_schema_migrations_table_exists(empty_conn):
    migrations.apply(empty_conn)
    assert db.table_exists(empty_conn, "schema_migrations")


def test_schema_migrations_rows_match_versions(empty_conn):
    applied = migrations.apply(empty_conn)
    rows = migrations.applied_versions(empty_conn)
    assert rows == sorted(applied)


@pytest.mark.parametrize("table", CORE_TABLES)
def test_core_tables_exist_after_migration(empty_conn, table):
    migrations.apply(empty_conn)
    assert db.table_exists(empty_conn, table)


@pytest.mark.parametrize("table", FTS_TABLES)
def test_fts_tables_exist_after_migration(empty_conn, table):
    migrations.apply(empty_conn)
    assert db.table_exists(empty_conn, table)


def test_pending_empty_after_apply(empty_conn):
    migrations.apply(empty_conn)
    assert migrations.pending(empty_conn) == []


def test_pending_non_empty_before_apply(empty_conn):
    pending = migrations.pending(empty_conn)
    assert len(pending) == len(migrations.discover())


def test_current_version_blank_when_empty(empty_conn):
    assert migrations.current_version(empty_conn) == ""


def test_current_version_after_apply(empty_conn):
    migrations.apply(empty_conn)
    assert migrations.current_version(empty_conn) == "0001"
