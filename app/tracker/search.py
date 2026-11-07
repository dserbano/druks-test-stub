"""Full-text search over projects, tasks and comments via SQLite FTS5."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SearchHit:
    kind: str            # 'project' | 'task' | 'comment'
    rowid: int
    snippet: str
    rank: float

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "rowid": self.rowid,
            "snippet": self.snippet,
            "rank": self.rank,
        }


def _escape_query(term: str) -> str:
    """Wrap a search term for FTS5, letting callers pass plain strings."""
    term = term.strip()
    if not term:
        return ""
    if any(ch in term for ch in "\"'()*"):
        return term
    tokens = [t for t in term.split() if t]
    return " ".join(f'"{t}"' for t in tokens)


def search_projects(conn: sqlite3.Connection, term: str, limit: int = 20) -> List[SearchHit]:
    q = _escape_query(term)
    if not q:
        return []
    rows = conn.execute(
        """
        SELECT rowid,
               snippet(projects_fts, -1, '[', ']', '…', 10) AS snip,
               bm25(projects_fts) AS rank
        FROM projects_fts
        WHERE projects_fts MATCH ?
        ORDER BY rank LIMIT ?
        """,
        (q, limit),
    ).fetchall()
    return [SearchHit("project", int(r["rowid"]), r["snip"], float(r["rank"])) for r in rows]


def search_tasks(conn: sqlite3.Connection, term: str, limit: int = 20) -> List[SearchHit]:
    q = _escape_query(term)
    if not q:
        return []
    rows = conn.execute(
        """
        SELECT rowid,
               snippet(tasks_fts, -1, '[', ']', '…', 10) AS snip,
               bm25(tasks_fts) AS rank
        FROM tasks_fts
        WHERE tasks_fts MATCH ?
        ORDER BY rank LIMIT ?
        """,
        (q, limit),
    ).fetchall()
    return [SearchHit("task", int(r["rowid"]), r["snip"], float(r["rank"])) for r in rows]


def search_comments(conn: sqlite3.Connection, term: str, limit: int = 20) -> List[SearchHit]:
    q = _escape_query(term)
    if not q:
        return []
    rows = conn.execute(
        """
        SELECT rowid,
               snippet(comments_fts, -1, '[', ']', '…', 10) AS snip,
               bm25(comments_fts) AS rank
        FROM comments_fts
        WHERE comments_fts MATCH ?
        ORDER BY rank LIMIT ?
        """,
        (q, limit),
    ).fetchall()
    return [SearchHit("comment", int(r["rowid"]), r["snip"], float(r["rank"])) for r in rows]


def search_all(conn: sqlite3.Connection, term: str, limit: int = 20) -> List[SearchHit]:
    hits: List[SearchHit] = []
    hits.extend(search_projects(conn, term, limit))
    hits.extend(search_tasks(conn, term, limit))
    hits.extend(search_comments(conn, term, limit))
    hits.sort(key=lambda h: h.rank)
    return hits[:limit]


def rebuild_indexes(conn: sqlite3.Connection) -> None:
    """Force a rebuild of every FTS index from its content table."""
    for name in ("projects_fts", "tasks_fts", "comments_fts"):
        conn.execute(f"INSERT INTO {name}({name}) VALUES('rebuild')")
    conn.commit()


def reindex_project(conn: sqlite3.Connection, project_id: Optional[int] = None) -> None:
    rebuild_indexes(conn)
