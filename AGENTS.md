# Repository Guidelines

This document merges the repository guidelines and Copilot instructions into one deduplicated guide for contributors and AI agents.

## Architecture and boundaries
- Layers under `src/keep_mcp/`:
	- `adapters/` expose MCP tools and schemas; translate inputs/outputs and map exceptions to AdapterError codes.
	- `services/` contain domain logic (add/recall/manage/export, ranking, duplicate detection, audit).
	- `storage/` contains SQLite repositories and idempotent migrations; no business logic here.
	- `utils/` holds small helpers (time, identifiers, etc.).
- Application wiring lives in `main.py` (build_application) and `fastmcp_server.py` (FastMCP stdio tools). CLI entry is `cli.py`.
- Data flow: FastMCP tool → adapter `adapters/tools/*` → `CardService`/`ExportService` → repositories → SQLite.
- Keep storage access inside repositories and surface typed models like `MemoryCard`.
- Tests mirror the layers in `tests/{unit,integration,contract,perf}`; shared fixtures live in `tests/conftest.py`.

## Developer workflows
- Environment: Python 3.12 with uv.
	- Install deps: `uv sync`
	- Migrate DB: `uv run keep-mcp migrate --db-path data/cards.db`
	- Run FastMCP server (stdio): `uv run keep-mcp serve --db-path data/cards.db` or `uv run python -m keep_mcp.fastmcp_server`
	- Smoke stdio client: `uv run python scripts/smoke_stdio_client.py`
	- Tests: `uv run pytest` (see markers in `pytest.ini`); heavier perf tests marked with `@pytest.mark.perf`.
	- Exports/audit/debug/seed: see `README.md` for command variants (`keep-mcp export|audit|debug|seed`).
- Target suites: `uv run pytest tests/unit`, `uv run pytest tests/integration`, or `uv run pytest -m contract`.

## Tool contracts and schemas
- Each MCP tool under `adapters/tools/` defines:
	- `TOOL_NAME`, `REQUEST_SCHEMA`, `RESPONSE_SCHEMA`, and optional `ERROR_SCHEMA`.
	- An async `execute(service, request)` that validates/normalizes and calls into services.
	- Map validation faults to `ValidationError`; unexpected failures to `StorageFailure` (or specific codes).
- FastMCP (`fastmcp_server.py`) exposes tools with individual top‑level parameters (no nested payload input). It assembles a request dict to call the adapters and wraps adapter errors into `McpError`. Output types remain Pydantic models for clear schemas.

## Services behavior highlights
- `CardService.add_card` performs duplicate merge within a recency window using `DuplicateDetectionService` (TF‑IDF cosine, char_wb n‑grams). On merge, tags are unioned with slug-based de‑dupe and a MERGE revision recorded.
- `CardService.recall` ranks via `RankingService` (semantic TF‑IDF, recency, recall penalty), updates recall counters, and writes audit logs. Tag filtering is by slug via `TagRepository.find_cards_with_tags`.
- `CardService.manage_card` supports UPDATE/ARCHIVE/DELETE with revision snaps and audits; DELETE clears dependent rows in repo.
- `ExportService.export` streams all cards + revisions to NDJSON and records an audit entry.

## Storage and migrations
- Migrations are idempotent (`storage/migrations.py`) using `sqlite-utils`; FTS5 tables and triggers keep `memory_card_search` in sync.
- Repositories (`storage/repository.py`, `revision_repository.py`, `tag_repository.py`, `audit_repository.py`) are the only place that talk to SQLite. Keep business rules out of this layer.

## Conventions, style, and logging
- PEP 8 style with type hints; dataclasses for value objects (e.g., `RankedCard`, `DuplicateMatch`).
- Naming: `snake_case` for functions/variables, `PascalCase` for classes and dataclasses.
- Use `telemetry.get_logger()` for structured logs; avoid `print`. Bind context with `telemetry.bind_context` when helpful.
- Keep user-facing schemas next to adapters; cap string lengths as in services and schemas (title 120, summary 500, body 4000, tag 60, excerpt 280).
- Respect limits: recall `limit` 1..25; tags unique with max 5 for recall, 20 for card payloads.
- Services offload repository and CPU/IO work via `asyncio.to_thread(...)` to keep the event loop responsive—preserve this pattern.
- Identifiers are ULIDs (`identifiers.new_ulid()`); keep them as strings end-to-end.

## Testing guidelines
- Pytest markers: `unit`, `integration`, `contract`, `perf` (perf scenarios are heavier and skipped by default).
- Name tests `test_<feature>.py`; prefer descriptive function names like `test_manage_card_updates_tags`.
- Contract/integration suites expect an initialised database; call the migration command in setup or reuse fixtures in `tests/conftest.py`.

## Commit & Pull Request guidelines
- Use Conventional Commits (`feat:`, `fix:`, `chore:`). Keep subject lines under 72 characters.
- In PRs, link the motivating issue, summarise behavior changes, highlight new commands/scripts, and attach CLI output or screenshots for user-facing changes.

## Environment & data safety
- Database paths default to the user's config directory; pass `--db-path` to isolate test databases and avoid polluting real data.
- Never commit generated SQLite files or NDJSON exports—ensure they are ignored by `.gitignore`.
- Ensure telemetry contains no secrets or personal data before merging.

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

Examples (FastMCP param style):

- memory.add_card(title, summary, body?, tags?, originConversationId?, originMessageExcerpt?)
- memory.recall(query?, tags?, limit?, includeArchived?)
- memory.manage(cardId, operation, title?, summary?, body?, tags?)
- memory.export(destinationPath?)

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

## Notes
- The legacy `cli` console script alias has been removed. Use `keep-mcp` for all commands.
