"""Tests for ``app.tracker.db``."""

from __future__ import annotations

import os
import sqlite3

import pytest

from app.tracker import db


def test_connect_memory_returns_connection():
    c = db.connect(":memory:")
    try:
        assert isinstance(c, sqlite3.Connection)
    finally:
        c.close()


def test_connect_default_is_memory():
    c = db.connect(None)
    try:
        assert isinstance(c, sqlite3.Connection)
    finally:
        c.close()


def test_connect_row_factory_is_row():
    c = db.connect(":memory:")
    try:
        c.execute("CREATE TABLE t(a INTEGER)")
        c.execute("INSERT INTO t VALUES (1)")
        row = c.execute("SELECT a FROM t").fetchone()
        assert row["a"] == 1
    finally:
        c.close()


def test_connect_foreign_keys_enabled():
    c = db.connect(":memory:")
    try:
        row = c.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1
    finally:
        c.close()


def test_connect_file(tmp_path):
    path = tmp_path / "x.db"
    c = db.connect(str(path))
    try:
        c.execute("CREATE TABLE t(a INTEGER)")
        c.commit()
    finally:
        c.close()
    assert os.path.exists(path)


def test_connect_pathlike(tmp_path):
    path = tmp_path / "y.db"
    c = db.connect(path)
    try:
        c.execute("CREATE TABLE t(a INTEGER)")
        c.commit()
    finally:
        c.close()
    assert path.exists()


def test_transaction_commits_on_success():
    c = db.connect(":memory:")
    try:
        c.execute("CREATE TABLE t(a INTEGER)")
        with db.transaction(c):
            c.execute("INSERT INTO t VALUES (1)")
        assert c.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    finally:
        c.close()


def test_transaction_rolls_back_on_error():
    c = db.connect(":memory:")
    try:
        c.execute("CREATE TABLE t(a INTEGER)")
        with pytest.raises(RuntimeError):
            with db.transaction(c):
                c.execute("INSERT INTO t VALUES (1)")
                raise RuntimeError("boom")
        assert c.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0
    finally:
        c.close()


def test_executescript_runs_multiple_statements():
    c = db.connect(":memory:")
    try:
        db.executescript(c, "CREATE TABLE t(a INTEGER); INSERT INTO t VALUES(7);")
        assert c.execute("SELECT a FROM t").fetchone()[0] == 7
    finally:
        c.close()


def test_table_exists_true_after_create():
    c = db.connect(":memory:")
    try:
        c.execute("CREATE TABLE t(a INTEGER)")
        assert db.table_exists(c, "t") is True
    finally:
        c.close()


def test_table_exists_false_when_missing():
    c = db.connect(":memory:")
    try:
        assert db.table_exists(c, "nope") is False
    finally:
        c.close()


def test_close_tolerates_none():
    db.close(None)


def test_close_closes_connection():
    c = db.connect(":memory:")
    db.close(c)
    with pytest.raises(sqlite3.ProgrammingError):
        c.execute("SELECT 1")
