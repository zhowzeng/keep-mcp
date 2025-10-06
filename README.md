# MCP Memory Server

Local MCP server for managing user memory cards. Implementation in progress.

## Quickstart

- Install deps (Python 3.12):

	uv sync

- Initialize the SQLite schema (creates a DB under `data/memory.db` by default):

	uv run cli migrate --db-path data/memory.db

- Run the MCP stdio server:

	uv run cli serve --db-path data/memory.db

The server uses the MCP Python SDK (low-level server) and speaks stdio. You can connect using MCP Inspector or a compatible client.

### FastMCP 版本（方便使用 `uv run mcp dev`）

- 直接啟動 FastMCP 伺服器（stdio）：

	uv run cli serve-fastmcp --db-path data/memory.db

- 你也可以在專案根目錄直接執行 FastMCP 的 entry：

	uv run python -m keep_mcp.fastmcp_server

### Smoke 測試（內建最小 stdio 客戶端）

- 啟動一個子行程跑 stdio 伺服器並連線，列出工具、做一次 recall 呼叫：

	uv run python scripts/smoke_stdio_client.py

## Other CLI commands

- Export cards to NDJSON:

	uv run cli export --db-path data/memory.db --destination data/export.ndjson

- View recent audit log entries:

	uv run cli audit --db-path data/memory.db --limit 20

- Debug ranking / duplicates:

	uv run cli debug --db-path data/memory.db --query "search terms" --top 5

- Seed sample cards (perf/local testing):

	uv run cli seed --db-path data/memory.db --count 1000 --tags demo perf

## Tests

Run tests:

	uv run pytest

Contract tests 已移除。
