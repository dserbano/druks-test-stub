"""Command-line entry point for ``sitegen``."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import build as build_site
from .server import serve as serve_site


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sitegen", description="Static site generator")
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="Build the site")
    b.add_argument("src", help="Source directory")
    b.add_argument("out", help="Output directory")
    b.add_argument("--config", help="Path to site.toml", default=None)
    s = sub.add_parser("serve", help="Serve the site with live reload")
    s.add_argument("src", help="Source directory")
    s.add_argument("out", help="Output directory")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--config", help="Path to site.toml", default=None)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build":
        result = build_site(Path(args.src), Path(args.out), config_path=args.config)
        print(f"rendered {len(result.rendered)} pages, skipped {len(result.skipped)}")
        return 0
    if args.command == "serve":
        serve_site(Path(args.src), Path(args.out), host=args.host, port=args.port, config_path=args.config)
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
