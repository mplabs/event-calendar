"""Command-line entrypoint for the ingestion service.

Examples:
    python -m eventscraper.cli list-sources
    python -m eventscraper.cli run-source example-feed --dry-run
    python -m eventscraper.cli run-all
"""

from __future__ import annotations

import argparse
import logging
import sys

from .config import get_source, load_sources
from .pipeline import run_source


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )


def cmd_list_sources(_: argparse.Namespace) -> int:
    for s in load_sources():
        flag = "on " if s.enabled else "off"
        print(f"[{flag}] {s.id:24} {s.region:8} {s.fetch.type:8} {s.name}")
    return 0


def _run_one(source, dry_run: bool) -> None:
    result = run_source(source, dry_run=dry_run)
    print(
        f"{result.source_id}: fetched={result.fetched} "
        f"normalized={result.normalized} deduped={result.deduped} "
        f"stored={result.stored}"
    )


def cmd_run_source(args: argparse.Namespace) -> int:
    source = get_source(args.source_id)
    _run_one(source, args.dry_run)
    return 0


def cmd_run_all(args: argparse.Namespace) -> int:
    sources = [s for s in load_sources() if s.enabled]
    if not sources:
        print("no enabled sources; edit sources.yaml (enabled: true)", file=sys.stderr)
        return 1
    for source in sources:
        try:
            _run_one(source, args.dry_run)
        except Exception as exc:  # keep going on per-source failure
            print(f"{source.id}: ERROR {exc}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eventscraper")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-sources", help="list configured sources").set_defaults(
        func=cmd_list_sources
    )

    p_run = sub.add_parser("run-source", help="run the pipeline for one source")
    p_run.add_argument("source_id")
    p_run.add_argument("--dry-run", action="store_true", help="do not write to the DB")
    p_run.set_defaults(func=cmd_run_source)

    p_all = sub.add_parser("run-all", help="run all enabled sources")
    p_all.add_argument("--dry-run", action="store_true")
    p_all.set_defaults(func=cmd_run_all)

    return parser


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
