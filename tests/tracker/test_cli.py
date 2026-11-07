"""Tests for ``app.tracker.__main__``."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.tracker.__main__ import build_parser, main

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(args, cwd=None):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "app.tracker", *args],
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )


def test_parser_exists():
    parser = build_parser()
    assert parser is not None


@pytest.mark.parametrize("cmd", ["migrate", "seed", "dashboard"])
def test_subcommand_in_help(cmd):
    out = _run(["--help"])
    assert out.returncode == 0
    assert cmd in out.stdout


def test_unknown_subcommand_exits_nonzero():
    out = _run(["bogus"])
    assert out.returncode != 0


def test_missing_subcommand_exits_nonzero():
    out = _run([])
    assert out.returncode != 0


def test_migrate_runs(tmp_path):
    db = tmp_path / "mig.db"
    out = _run(["migrate", "--db", str(db)])
    assert out.returncode == 0
    assert db.exists()


def test_migrate_twice_idempotent(tmp_path):
    db = tmp_path / "x.db"
    _run(["migrate", "--db", str(db)])
    out = _run(["migrate", "--db", str(db)])
    assert out.returncode == 0


def test_seed_runs(tmp_path):
    db = tmp_path / "s.db"
    out = _run(["seed", "--db", str(db)])
    assert out.returncode == 0
    assert "seeded" in out.stdout


def test_dashboard_requires_output(tmp_path):
    db = tmp_path / "d.db"
    _run(["seed", "--db", str(db)])
    out = _run(["dashboard", "--db", str(db)])
    assert out.returncode != 0


def test_dashboard_writes_file(tmp_path):
    db = tmp_path / "d.db"
    _run(["seed", "--db", str(db)])
    html = tmp_path / "dash.html"
    out = _run(["dashboard", "--db", str(db), "--output", str(html)])
    assert out.returncode == 0
    assert html.exists()
    assert "<html" in html.read_text()


def test_dashboard_search_flag(tmp_path):
    db = tmp_path / "d.db"
    _run(["seed", "--db", str(db)])
    html = tmp_path / "s.html"
    _run(["dashboard", "--db", str(db), "--output", str(html), "--search", "cache"])
    assert "cache" in html.read_text().lower()


def test_main_returns_int_on_migrate(tmp_path):
    rc = main(["migrate", "--db", str(tmp_path / "m.db")])
    assert rc == 0


def test_main_returns_int_on_seed(tmp_path):
    rc = main(["seed", "--db", str(tmp_path / "m.db")])
    assert rc == 0


def test_main_returns_int_on_dashboard(tmp_path):
    rc = main([
        "dashboard",
        "--db", str(tmp_path / "m.db"),
        "--output", str(tmp_path / "o.html"),
    ])
    assert rc == 0
    assert (tmp_path / "o.html").exists()


def test_bad_sprint_type_rejected(tmp_path):
    out = _run([
        "dashboard",
        "--db", str(tmp_path / "x.db"),
        "--output", str(tmp_path / "x.html"),
        "--sprint", "notanint",
    ])
    assert out.returncode != 0
