"""Seed a representative dataset into a migrated database."""

from __future__ import annotations

import sqlite3

from app.tracker.models import (
    assignee as assignee_mod,
    comment as comment_mod,
    dependency as dependency_mod,
    label as label_mod,
    project as project_mod,
    sprint as sprint_mod,
    subtask as subtask_mod,
    task as task_mod,
)

SEED_COUNTS = {
    "projects": 3,
    "assignees": 4,
    "sprints": 4,
    "labels": 5,
    "tasks": 12,
    "subtasks": 10,
    "dependencies": 4,
    "comments": 10,
}


def run(conn: sqlite3.Connection) -> dict:
    """Populate ``conn`` with a non-trivial dataset and return the counts."""
    proj_alpha = project_mod.create(conn, "Alpha", "Core platform work")
    proj_beta = project_mod.create(conn, "Beta", "Growth experiments")
    proj_gamma = project_mod.create(conn, "Gamma", "Infrastructure")

    alice = assignee_mod.create(conn, "Alice", "alice@example.com")
    bob = assignee_mod.create(conn, "Bob", "bob@example.com")
    carol = assignee_mod.create(conn, "Carol", "carol@example.com")
    dave = assignee_mod.create(conn, "Dave", "dave@example.com")

    sprint_a1 = sprint_mod.create(conn, proj_alpha, "Alpha-S1", "2026-01-05", "2026-01-16")
    sprint_a2 = sprint_mod.create(conn, proj_alpha, "Alpha-S2", "2026-01-19", "2026-01-30")
    sprint_b1 = sprint_mod.create(conn, proj_beta, "Beta-S1", "2026-01-05", "2026-01-16")
    sprint_g1 = sprint_mod.create(conn, proj_gamma, "Gamma-S1", "2026-02-02", "2026-02-13")

    label_bug = label_mod.create(conn, "bug", "#cc0000")
    label_feat = label_mod.create(conn, "feature", "#007700")
    label_chore = label_mod.create(conn, "chore", "#777777")
    label_doc = label_mod.create(conn, "docs", "#3333aa")
    label_perf = label_mod.create(conn, "performance", "#aa7700")

    tasks = []
    tasks.append(task_mod.create(conn, proj_alpha, "Design schema",
                                 description="initial data model sketch",
                                 status="done", estimate=3, sprint_id=sprint_a1,
                                 assignee_id=alice, completed_at="2026-01-07"))
    tasks.append(task_mod.create(conn, proj_alpha, "Implement API",
                                 description="HTTP endpoints for tasks",
                                 status="in_progress", estimate=5, sprint_id=sprint_a1,
                                 assignee_id=bob))
    tasks.append(task_mod.create(conn, proj_alpha, "Write unit tests",
                                 description="exhaustive pytest coverage",
                                 status="todo", estimate=4, sprint_id=sprint_a1,
                                 assignee_id=carol))
    tasks.append(task_mod.create(conn, proj_alpha, "Add caching",
                                 description="LRU cache for hot queries",
                                 status="todo", estimate=2, sprint_id=sprint_a2,
                                 assignee_id=bob))
    tasks.append(task_mod.create(conn, proj_beta, "AB test landing page",
                                 description="measure conversion lift",
                                 status="in_progress", estimate=3, sprint_id=sprint_b1,
                                 assignee_id=dave))
    tasks.append(task_mod.create(conn, proj_beta, "Instrument funnels",
                                 description="event tracking",
                                 status="done", estimate=2, sprint_id=sprint_b1,
                                 assignee_id=alice, completed_at="2026-01-10"))
    tasks.append(task_mod.create(conn, proj_beta, "Analyse cohort retention",
                                 description="week-over-week",
                                 status="blocked", estimate=5, sprint_id=sprint_b1,
                                 assignee_id=carol))
    tasks.append(task_mod.create(conn, proj_gamma, "Harden CI",
                                 description="flaky job cleanup",
                                 status="todo", estimate=3, sprint_id=sprint_g1,
                                 assignee_id=dave))
    tasks.append(task_mod.create(conn, proj_gamma, "Upgrade Python",
                                 description="python 3.12 for every service",
                                 status="in_progress", estimate=4, sprint_id=sprint_g1,
                                 assignee_id=bob))
    tasks.append(task_mod.create(conn, proj_gamma, "Document deploys",
                                 description="runbooks for on-call",
                                 status="todo", estimate=2, sprint_id=sprint_g1,
                                 assignee_id=alice))
    tasks.append(task_mod.create(conn, proj_alpha, "Rate limiting",
                                 description="per-user throttles",
                                 status="todo", estimate=3, sprint_id=sprint_a2,
                                 assignee_id=carol))
    tasks.append(task_mod.create(conn, proj_beta, "Email digest",
                                 description="weekly roll-up emails",
                                 status="todo", estimate=2, sprint_id=sprint_b1,
                                 assignee_id=dave))

    # Subtasks on a few tasks
    subtask_mod.create(conn, tasks[1], "Sketch route tree")
    subtask_mod.create(conn, tasks[1], "Pick request-body schema")
    subtask_mod.create(conn, tasks[1], "Write happy-path handlers", done=True)
    subtask_mod.create(conn, tasks[2], "Set up fixtures")
    subtask_mod.create(conn, tasks[2], "Cover error paths")
    subtask_mod.create(conn, tasks[4], "Build variant renderer")
    subtask_mod.create(conn, tasks[4], "Wire metrics", done=True)
    subtask_mod.create(conn, tasks[7], "Audit flakes")
    subtask_mod.create(conn, tasks[7], "Retry only on known-transient errors")
    subtask_mod.create(conn, tasks[8], "Confirm on canary", done=True)

    # Dependencies (blocks)
    dependency_mod.create(conn, tasks[0], tasks[1], "blocks")
    dependency_mod.create(conn, tasks[1], tasks[2], "blocks")
    dependency_mod.create(conn, tasks[8], tasks[7], "blocks")
    dependency_mod.create(conn, tasks[4], tasks[5], "relates_to")

    # Labels
    task_mod.attach_label(conn, tasks[1], label_feat)
    task_mod.attach_label(conn, tasks[2], label_chore)
    task_mod.attach_label(conn, tasks[3], label_perf)
    task_mod.attach_label(conn, tasks[6], label_bug)
    task_mod.attach_label(conn, tasks[9], label_doc)

    # Comments (mix of task + project)
    comment_mod.create_on_task(conn, tasks[0], "Looks solid, approved.", "alice")
    comment_mod.create_on_task(conn, tasks[1], "Blocked waiting on schema review.", "bob")
    comment_mod.create_on_task(conn, tasks[2], "Will add integration tests after unit.", "carol")
    comment_mod.create_on_task(conn, tasks[4], "Preliminary numbers look good.", "dave")
    comment_mod.create_on_task(conn, tasks[6], "Analysis stalled; need warehouse access.", "carol")
    comment_mod.create_on_task(conn, tasks[8], "Upgrade on canary is stable.", "bob")
    comment_mod.create_on_project(conn, proj_alpha, "Kick-off notes archived.", "alice")
    comment_mod.create_on_project(conn, proj_beta, "Growth plan draft circulated.", "dave")
    comment_mod.create_on_project(conn, proj_gamma, "Capacity planning review next week.", "bob")
    comment_mod.create_on_task(conn, tasks[9], "Runbook outline in docs folder.", "alice")

    return SEED_COUNTS.copy()


def expected_counts() -> dict:
    return SEED_COUNTS.copy()
