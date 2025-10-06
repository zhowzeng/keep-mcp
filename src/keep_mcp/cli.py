from __future__ import annotations

import argparse
import asyncio
import random
import string
from typing import Iterable, Sequence

from keep_mcp.main import build_application
from keep_mcp.fastmcp_server import run_fastmcp_server
from keep_mcp.storage.connection import create_connection, resolve_db_path
from keep_mcp.storage.migrations import apply_migrations
from keep_mcp.telemetry import configure_logging, get_logger

LOGGER = get_logger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP memory server CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the MCP memory FastMCP stdio server")
    serve.add_argument("--db-path", type=str, default=None, help="Path to SQLite database")

    migrate = subparsers.add_parser("migrate", help="Apply database migrations")
    migrate.add_argument("--db-path", type=str, default=None, help="Path to SQLite database")

    export = subparsers.add_parser("export", help="Export memory cards to NDJSON")
    export.add_argument("--db-path", type=str, default=None, help="Path to SQLite database")
    export.add_argument("--destination", type=str, default=None, help="Destination file path")

    audit = subparsers.add_parser("audit", help="View recent audit log entries")
    audit.add_argument("--db-path", type=str, default=None, help="Path to SQLite database")
    audit.add_argument("--limit", type=int, default=20, help="Number of entries to display")

    debug = subparsers.add_parser("debug", help="Debug recall ranking and duplicates")
    debug.add_argument("--db-path", type=str, default=None, help="Path to SQLite database")
    debug.add_argument("--query", type=str, default=None, help="Query string for ranking analysis")
    debug.add_argument(
        "--candidate",
        type=str,
        default=None,
        help="Candidate text (title + summary) for duplicate detection",
    )
    debug.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived cards in debug output",
    )
    debug.add_argument("--top", type=int, default=5, help="Number of ranked cards to show")

    seed = subparsers.add_parser("seed", help="Seed sample cards for perf testing")
    seed.add_argument("--db-path", type=str, default=None, help="Path to SQLite database")
    seed.add_argument("--count", type=int, default=1000, help="Number of cards to insert")
    seed.add_argument(
        "--tags",
        nargs="*",
        default=["demo", "perf"],
        help="Tags to use when seeding cards",
    )

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    configure_logging()
    args = parse_args(argv)

    if args.command == "serve":
        run_fastmcp_server(args.db_path)
        return

    if args.command == "migrate":
        _cmd_migrate(args.db_path)
        return

    if args.command == "export":
        asyncio.run(_cmd_export(args.db_path, args.destination))
        return

    if args.command == "audit":
        _cmd_audit(args.db_path, args.limit)
        return

    if args.command == "debug":
        asyncio.run(
            _cmd_debug(
                db_path=args.db_path,
                query=args.query,
                candidate=args.candidate,
                include_archived=args.include_archived,
                top=args.top,
            )
        )
        return

    if args.command == "seed":
        asyncio.run(_cmd_seed(args.db_path, args.count, args.tags))
        return

    raise RuntimeError(f"Unknown command: {args.command}")


def _cmd_migrate(db_path: str | None) -> None:
    resolved = resolve_db_path(db_path)
    connection = create_connection(resolved)
    try:
        apply_migrations(connection)
        LOGGER.info("database.migrated", db_path=str(resolved))
    finally:
        connection.close()


async def _cmd_export(db_path: str | None, destination: str | None) -> None:
    app = build_application(db_path)
    try:
        result = await app.export_service.export(destination)
        LOGGER.info("export.complete", file=result["filePath"], count=result["exportedCount"])
    finally:
        app.connection_close()


def _cmd_audit(db_path: str | None, limit: int) -> None:
    app = build_application(db_path)
    try:
        for entry in app.audit_service.list_recent(limit):
            LOGGER.info(
                "audit.entry",
                action=entry.action,
                card_id=entry.card_id,
                happened_at=entry.happened_at,
                payload=entry.payload_json,
            )
    finally:
        app.connection_close()


async def _cmd_debug(
    *,
    db_path: str | None,
    query: str | None,
    candidate: str | None,
    include_archived: bool,
    top: int,
) -> None:
    app = build_application(db_path)
    try:
        cards = app.card_repository.list_canonical_cards(include_archived)
        if query:
            ranked = app.ranking_service.rank(cards, query)
            for item in ranked[: max(1, top)]:
                LOGGER.info(
                    "debug.rank",
                    card_id=item.card.card_id,
                    score=item.score,
                    title=item.card.title,
                    summary=item.card.summary,
                    tags=list(item.card.tags),
                )
        if candidate:
            corpus = [(card.card_id, f"{card.title}\n{card.summary}") for card in cards]
            match = app.duplicate_service.find_duplicate(candidate, corpus)
            if match:
                LOGGER.info("debug.duplicate", card_id=match.card_id, score=match.score)
            else:
                LOGGER.info("debug.duplicate", card_id=None, score=0.0)
    finally:
        app.connection_close()


async def _cmd_seed(db_path: str | None, count: int, tags: Iterable[str]) -> None:
    app = build_application(db_path)
    try:
        for index in range(count):
            payload = {
                "title": f"Seed Card {index + 1}",
                "summary": _random_summary(index),
                "body": "Generated for performance testing.",
                "tags": list(tags),
            }
            await app.card_service.add_card(payload)
        LOGGER.info("seed.complete", inserted=count)
    finally:
        app.connection_close()


def _random_summary(index: int) -> str:
    random.seed(index)
    words = ["async", "python", "mcp", "memory", "card", "workflow", "note", "rank", "duplicate"]
    extras = "".join(random.choices(string.ascii_lowercase, k=8))
    return f"Perf seed #{index} {' '.join(random.sample(words, 5))} {extras}"


if __name__ == "__main__":  # pragma: no cover
    main()
