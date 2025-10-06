# Memory Server Operational Overview

This document summarises the developer-facing commands and scripts that keep the
memory server healthy during local development.

## Database Lifecycle
- `uv run python scripts/migrate.py` – apply schema migrations against the
  configured SQLite database (defaults to `~/.mcp-memory/cards.db`). Run after
  pulling schema changes or before first boot.
- `uv run python scripts/seed_cards.py --count 1000` – populate synthetic cards
  for performance and integration testing. The count flag is optional and
  defaults to 1000.

## Inspection & Debugging
- `uv run python scripts/view_audit.py --tail 20` – view the most recent audit
  log entries to verify tool usage and payloads.
- `uv run python scripts/debug_query.py --query "async"` – inspect ranked recall
  calculations, including similarity scores, to debug search behaviour.

## Export & Backup
- `uv run python scripts/export.py --out ~/Downloads/memory-export-$(date +%Y%m%d).jsonl`
  – stream an NDJSON export of all cards, revisions, and tags. Use the
  `--out` flag to override the destination path.

## Test Suites
- `uv run pytest tests/contract -q` – contract alignment checks for MCP tools.
- `uv run pytest tests/integration -q` – end-to-end stdio flow verification.
- `uv run pytest tests/unit -q` – service and repository unit coverage,
  including duplicate detection and ranking.
- `uv run pytest tests/perf -q` – performance guardrails that monitor write and
  recall latency against specification targets.
