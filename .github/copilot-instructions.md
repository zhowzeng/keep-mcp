# Copilot instructions for keep-mcp

This repo implements a local MCP Memory server with a clear layering and a small CLI. Follow these rules to be productive and consistent with the codebase.

## Architecture and boundaries
- Layers under `src/keep_mcp/`:
  - `adapters/` expose MCP tools and schemas; translate inputs/outputs and map exceptions to AdapterError codes.
  - `services/` contain domain logic (add/recall/manage/export, ranking, duplicate detection, audit).
  - `storage/` contains SQLite repositories and idempotent migrations; no business logic here.
  - `utils/` holds small helpers (time, identifiers, etc.).
- Application wiring lives in `main.py` (build_application) and `fastmcp_server.py` (FastMCP stdio tools). CLI entry is `cli.py`.
- Data flow example: FastMCP tool -> adapter `adapters/tools/*` -> `CardService`/`ExportService` -> repositories -> SQLite.
- Keep storage access inside repositories and surface typed models like `MemoryCard`.

## Developer workflows
- Environment: Python 3.12 with uv.
  - Install deps: `uv sync`
  - Migrate DB: `uv run keep-mcp migrate --db-path data/cards.db`
  - Run FastMCP server (stdio): `uv run keep-mcp serve --db-path data/cards.db` or `uv run python -m keep_mcp.fastmcp_server`
  - Smoke stdio client: `uv run python scripts/smoke_stdio_client.py`
  - Tests: `uv run pytest` (see markers in `pytest.ini`); heavier perf tests marked with `@pytest.mark.perf`.
  - Exports/audit/debug/seed: see `README.md` for command variants (`keep-mcp export|audit|debug|seed`).

## Tool contracts and schemas
- Each MCP tool under `adapters/tools/` defines:
  - `TOOL_NAME`, `REQUEST_SCHEMA`, `RESPONSE_SCHEMA`, and optional `ERROR_SCHEMA`.
  - An async `execute(service, request)` that validates/normalizes and calls into services.
  - Map validation faults to `ValidationError`; unexpected failures to `StorageFailure` (or specific codes).
- FastMCP (`fastmcp_server.py`) declares Pydantic models mirroring the schemas and wraps adapter errors into `McpError`.

## Services behavior highlights
- `CardService.add_card` performs duplicate merge within a recency window using `DuplicateDetectionService` (TF‑IDF cosine, char_wb n‑grams). On merge, tags are unioned with slug-based de‑dupe and a MERGE revision recorded.
- `CardService.recall` ranks via `RankingService` (semantic TF‑IDF, recency, recall penalty), updates recall counters, and writes audit logs. Tag filtering is by slug via `TagRepository.find_cards_with_tags`.
- `CardService.manage_card` supports UPDATE/ARCHIVE/DELETE with revision snaps and audits; DELETE clears dependent rows in repo.
- `ExportService.export` streams all cards + revisions to NDJSON and records an audit entry.

## Storage and migrations
- Migrations are idempotent (`storage/migrations.py`) using `sqlite-utils`; FTS5 tables and triggers keep `memory_card_search` in sync.
- Repositories (`storage/repository.py`, `revision_repository.py`, `tag_repository.py`, `audit_repository.py`) are the only place that talk to SQLite. Keep business rules out of this layer.

## Conventions and logging
- PEP 8 style with type hints; dataclasses for value objects (e.g., `RankedCard`, `DuplicateMatch`).
- Use `telemetry.get_logger()` for structured logs; avoid print. Bind context via `telemetry.bind_context` when helpful.
- Keep user‑facing schemas next to adapters; cap string lengths as in services and schemas (title 120, summary 500, body 4000, tag 60, excerpt 280).
- Respect limits: recall `limit` 1..25; tags unique with max 5 for recall, 20 for card payloads.
- Services offload repository and CPU/IO work via `asyncio.to_thread(...)` to keep the event loop responsive—preserve this pattern.
- Identifiers are ULIDs (`identifiers.new_ulid()`); keep them as strings end-to-end.

## When adding a new tool
- Define schema + `execute` under `adapters/tools/*` and add a FastMCP wrapper returning a Pydantic model.
- Route to a service method; add repository methods only if storage shape requires it.
- Update tests under `tests/{unit,integration}`; migrate schema in `storage/migrations.py` if new tables/indexes are needed.

## Examples
- Recall adapter pattern: see `adapters/tools/recall.py` for request/response shapes, validation, and error mapping.
- Ranking signals: `services/ranking.py` combines semantic similarity, recency decay, and recall penalty.
- Duplicate detection: `services/duplicate.py` with threshold 0.85 and a lightweight word‑level guard.

### Tool cheat‑sheet
- memory.add_card → `adapters/tools/add_card.py`
  - required: title (<=120), summary (<=500)
  - optional: body (<=4000), tags (<=20), originConversationId, originMessageExcerpt (<=280)
- memory.recall → `adapters/tools/recall.py`
  - optional: query (<=200), tags (<=5 unique), limit 1..25, includeArchived
- memory.manage → `adapters/tools/manage.py`
  - required: cardId, operation in [UPDATE, ARCHIVE, DELETE]
  - UPDATE payload: title/summary/body/tags (<=20)
- memory.export → `adapters/tools/export.py`
  - optional: destinationPath (absolute)

```try-it
# One-liners using console script
uv run keep-mcp migrate --db-path data/cards.db
uv run keep-mcp serve --db-path data/cards.db
uv run keep-mcp export --db-path data/cards.db --destination data/export.ndjson
uv run keep-mcp audit --db-path data/cards.db --limit 20
uv run keep-mcp debug --db-path data/cards.db --query "search terms" --top 5
uv run keep-mcp seed --db-path data/cards.db --count 1000 --tags demo perf

# Alternative entry points (optional)
uv run python -m keep_mcp.fastmcp_server
uv run python scripts/smoke_stdio_client.py
```