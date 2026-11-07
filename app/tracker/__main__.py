"""CLI entry: ``python -m app.tracker``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from app.tracker import dashboard as dashboard_mod
from app.tracker import db as db_mod
from app.tracker import migrations as migrations_mod
from app.tracker import seed as seed_mod


def _add_db_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        default="tracker.db",
        help="path to the SQLite database file (default: tracker.db)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    p_mig = sub.add_parser("migrate", help="apply pending migrations")
    _add_db_arg(p_mig)

    p_seed = sub.add_parser("seed", help="populate the database with seed data")
    _add_db_arg(p_seed)

    p_dash = sub.add_parser("dashboard", help="render the dashboard to an HTML file")
    _add_db_arg(p_dash)
    p_dash.add_argument("--output", required=True, help="output HTML path")
    p_dash.add_argument("--search", default="", help="search term to include")
    p_dash.add_argument("--sprint", type=int, default=None, help="sprint id for burndown")

    return parser


def cmd_migrate(args: argparse.Namespace) -> int:
    conn = db_mod.connect(args.db)
    try:
        applied = migrations_mod.apply(conn)
        print(f"applied {len(applied)} migration(s): {','.join(applied) if applied else '(none)'}")
    finally:
        conn.close()
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    conn = db_mod.connect(args.db)
    try:
        migrations_mod.apply(conn)
        counts = seed_mod.run(conn)
        print("seeded:", counts)
    finally:
        conn.close()
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    conn = db_mod.connect(args.db)
    try:
        migrations_mod.apply(conn)
        out = dashboard_mod.render(
            conn,
            Path(args.output),
            search_term=args.search,
            sprint_id=args.sprint,
        )
        print(f"wrote dashboard to {out}")
    finally:
        conn.close()
    return 0


HANDLERS = {
    "migrate": cmd_migrate,
    "seed": cmd_seed,
    "dashboard": cmd_dashboard,
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = HANDLERS.get(args.command)
    if handler is None:
        parser.error(f"unknown command: {args.command}")
        return 2
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
