"""Shared fixtures for tracker tests."""

from __future__ import annotations

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.tracker import db as db_mod
from app.tracker import migrations as migrations_mod
from app.tracker import seed as seed_mod


@pytest.fixture
def conn():
    c = db_mod.connect(":memory:")
    try:
        migrations_mod.apply(c)
        yield c
    finally:
        c.close()


@pytest.fixture
def empty_conn():
    c = db_mod.connect(":memory:")
    try:
        yield c
    finally:
        c.close()


@pytest.fixture
def seeded_conn(conn):
    seed_mod.run(conn)
    return conn
