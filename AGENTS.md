# Repository Guidelines

## Project Structure & Module Organization
Core server code lives in `src/keep_mcp`, split into `adapters` (MCP tool contracts), `services` (domain logic), `storage` (SQLite repositories + migrations), and `utils`. CLI entry points are in `src/keep_mcp/cli.py` and the stdio server wiring in `src/keep_mcp/main.py`. Tests mirror the layers inside `tests/{unit,integration,contract,perf}`, while reusable fixtures sit in `tests/conftest.py`. Utility scripts for manual workflows reside under `scripts/`, and conceptual notes are in `docs/`.

## Build, Test, and Development Commands
Install dependencies with `uv sync` (Python 3.12 per `.python-version`). Use `uv run python -m keep_mcp.cli migrate` to initialise the SQLite schema before interacting with data. Run the MCP server locally via `uv run python -m keep_mcp.cli serve --db-path data/memory.db`. Execute tests with `uv run pytest`; target suites with selectors such as `uv run pytest tests/unit` or `uv run pytest -m contract`.

## Coding Style & Naming Conventions
Python code follows PEP 8: four-space indentation, `snake_case` for functions and variables, and `PascalCase` for classes and dataclasses. Keep modules type-hinted, matching the existing service constructors and async tool wrappers. Use descriptive structured logging through `telemetry.configure_logging()` and `get_logger()` instead of raw `print`. Place user-facing schemas next to their adapters, and keep storage access inside repository classes to preserve layering.

## Testing Guidelines
Pytest is configured in `pytest.ini` with markers for `unit`, `integration`, `contract`, and `perf`. Name test files `test_<feature>.py` and prefer descriptive function names such as `test_manage_card_updates_tags`. Contract and integration suites expect an initialised database; call the migration command in test setup or reuse fixtures from `tests/conftest.py`. Tag heavier scenarios with `@pytest.mark.perf` so they can be skipped by default runners.

## Commit & Pull Request Guidelines
The repository has not established a commit history yet; adopt Conventional Commits (`feat:`, `fix:`, `chore:`) so tooling can group changes cleanly once history accumulates. Keep subject lines under 72 characters and include context in the body when touching multiple layers. Pull requests should link the motivating issue, summarise behaviour changes, highlight new commands or scripts, and attach CLI output or screenshots when altering user-facing flows.

## Environment & Data Safety
Database paths default to the user's config directory; pass `--db-path` to isolate test databases and avoid polluting real data. Never commit generated SQLite files or NDJSON exports—add them to `.gitignore` if new artefacts appear. When working with telemetry, ensure no secrets or personal data are logged before merging.
