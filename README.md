# MCP Memory Server

Local MCP server for managing user memory cards. Implementation in progress.

## Quickstart

- Install deps (Python 3.12):

	uv sync

- Initialize the SQLite schema (creates a DB under `data/cards.db` by default):

	uv run keep-mcp migrate --db-path data/cards.db

- Run the MCP stdio server:

	uv run keep-mcp serve --db-path data/cards.db

Note: The legacy `cli` console script alias has been removed. Use `keep-mcp` for all commands.

The server uses the MCP Python SDK (low-level server) and speaks stdio. You can connect using MCP Inspector or a compatible client.

### FastMCP 版本（方便使用 `uv run mcp dev`）

- 直接啟動 FastMCP 伺服器（stdio）：

	uv run keep-mcp serve --db-path data/cards.db

- 你也可以在專案根目錄直接執行 FastMCP 的 entry：

	uv run python -m keep_mcp.fastmcp_server

- 使用 MCP Inspector（建議在開發／除錯時）：

	uv run mcp dev src/keep_mcp/fastmcp_server.py --with-editable .

	說明：
	- `mcp dev` 會透過 Node MCP Inspector 啟動一個視覺化用戶端並執行此 FastMCP 伺服器。
	- 上述指令使用 `--with-editable .` 以便 Inspector 啟動時能載入本專案的原始碼變更。
	- 資料庫路徑預設來自 `keep_mcp.storage.connection.resolve_db_path()`，可用環境變數覆寫：

	  MCP_MEMORY_DB_PATH=/absolute/path/to/cards.db uv run mcp dev src/keep_mcp/fastmcp_server.py --with-editable .

### Smoke 測試（內建最小 stdio 客戶端）

- 啟動一個子行程跑 stdio 伺服器並連線，列出工具、做一次 recall 呼叫：

	uv run python scripts/smoke_stdio_client.py

## Other CLI commands

- Export cards to NDJSON:

	uv run keep-mcp export --db-path data/cards.db --destination data/export.ndjson

- View recent audit log entries:

	uv run keep-mcp audit --db-path data/cards.db --limit 20

- Debug ranking / duplicates:

	uv run keep-mcp debug --db-path data/cards.db --query "search terms" --top 5

- Seed sample cards (perf/local testing):

	uv run keep-mcp seed --db-path data/cards.db --count 1000 --tags demo perf

## MCP Tools

This server provides four MCP tools with comprehensive descriptions to help LLMs understand and use them effectively:

- **memory.add_card**: Store important information with automatic duplicate detection
- **memory.recall**: Search and retrieve relevant memory cards using semantic ranking
- **memory.manage**: Update, archive, or delete existing memory cards
- **memory.export**: Export all cards to NDJSON format for backup or analysis

Each tool includes detailed descriptions covering:
- Purpose and use cases
- Parameter constraints and descriptions
- Behavioral characteristics
- Best practices
- Error handling

For complete documentation, see [`docs/tool-descriptions.md`](docs/tool-descriptions.md).

## Tests

Run tests:

	uv run pytest

Contract tests 已移除。
