"""Tests for ``app.tracker.dashboard``."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.tracker import dashboard
from app.tracker.models import project


def test_render_to_path(tmp_path, seeded_conn):
    out = dashboard.render(seeded_conn, tmp_path / "x.html")
    assert out.exists()


def test_render_returns_path(tmp_path, seeded_conn):
    out = dashboard.render(seeded_conn, tmp_path / "y.html")
    assert isinstance(out, Path)


def test_render_creates_missing_parent(tmp_path, seeded_conn):
    target = tmp_path / "new" / "deep" / "a.html"
    dashboard.render(seeded_conn, target)
    assert target.exists()


def test_render_string_returns_html(seeded_conn):
    html = dashboard.render_string(seeded_conn)
    assert "<html" in html
    assert "</html>" in html


@pytest.mark.parametrize("anchor", [
    'id="projects"',
    'id="sprint-burndown"',
    'id="tasks-per-assignee"',
    'id="search-results"',
])
def test_sections_present(seeded_conn, anchor):
    html = dashboard.render_string(seeded_conn)
    assert anchor in html


def test_search_term_appears_when_matching(seeded_conn):
    html = dashboard.render_string(seeded_conn, search_term="cache")
    assert "cache" in html.lower()


def test_search_term_empty_still_renders(seeded_conn):
    html = dashboard.render_string(seeded_conn, search_term="")
    assert "No matches" in html


def test_renders_for_empty_db(conn, tmp_path):
    out = dashboard.render(conn, tmp_path / "empty.html")
    html = out.read_text()
    assert "No projects" in html
    assert "No sprints configured" in html


def test_sprint_id_override(seeded_conn):
    row = seeded_conn.execute("SELECT id FROM sprints ORDER BY id LIMIT 1").fetchone()
    html = dashboard.render_string(seeded_conn, sprint_id=row["id"])
    assert "Alpha-S1" in html or "Beta" in html or "Gamma" in html


def test_renders_project_rows(seeded_conn):
    html = dashboard.render_string(seeded_conn)
    assert "Alpha" in html and "Beta" in html and "Gamma" in html


def test_renders_all_assignees(seeded_conn):
    html = dashboard.render_string(seeded_conn)
    for n in ("Alice", "Bob", "Carol", "Dave"):
        assert n in html


def test_render_search_hits_include_kinds(seeded_conn):
    html = dashboard.render_string(seeded_conn, search_term="cache")
    assert "task#" in html or "project#" in html or "comment#" in html


def test_renders_header_h1(seeded_conn):
    html = dashboard.render_string(seeded_conn)
    assert 'id="tracker-dashboard"' in html


def test_html_well_formed_ends_with_html_close(seeded_conn):
    html = dashboard.render_string(seeded_conn)
    assert html.rstrip().endswith("</html>")


def test_project_without_tasks_still_rendered(conn, tmp_path):
    project.create(conn, "Loner", "no tasks")
    html = dashboard.render_string(conn)
    assert "Loner" in html
