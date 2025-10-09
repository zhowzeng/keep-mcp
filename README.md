# keep-mcp 記憶體伺服器

本專案提供一個本機 MCP 記憶體伺服器，負責管理使用者的記憶卡片（Memory Cards），支援新增、召回、管理與匯出。系統採用 Python 3.12、FastMCP stdio 與 SQLite 儲存層，可搭配任何支援 MCP 協定的用戶端或工具鏈。

## 概觀

- CLI 進入點為 `keep-mcp`；所有指令皆透過此命令執行。
- 預設資料庫路徑為 `data/cards.db`，可使用 `--db-path` 或環境變數 `MCP_MEMORY_DB_PATH` 覆寫。
- 專案提供完整的工具描述與測試結構，方便新成員快速上手。

## 核心能力

- **memory.add_card**：新增或合併記憶卡片，具備重複偵測與修訂紀錄。
- **memory.recall**：依語意排序與時間衰減召回卡片，可加上標籤與數量限制。
- **memory.manage**：更新、封存或刪除卡片，同步維護稽核紀錄。
- **memory.export**：串流匯出所有卡片與修訂成 NDJSON，適用備份或分析。

完整工具契約與說明位於 `docs/tool-descriptions.md`。

## 快速起步

1. 安裝相依套件（Python 3.12）：

   ```bash
   uv sync
   ```

2. 初始化 SQLite 資料庫（預設建立 `data/cards.db`）：

   ```bash
   uv run keep-mcp migrate --db-path data/cards.db
   ```

3. 啟動 MCP stdio 伺服器：

   ```bash
   uv run keep-mcp serve --db-path data/cards.db
   ```

伺服器遵循 MCP Python SDK 的 stdio 介面，可直接搭配 MCP Inspector 或其他相容用戶端使用。

4.（選用）啟動 MCP SSE 伺服器：

   ```bash
   uv run keep-mcp serve --transport sse --host 0.0.0.0 --port 8000
   ```

   SSE 模式適用於需要長連線事件流的用戶端（例如 ChatGPT connector）。`--mount-path` 可覆寫預設的 `/` 以配合部署環境。

## 開發與除錯

- FastMCP 執行：`uv run keep-mcp serve --db-path data/cards.db`
- 直接啟動 FastMCP entry：`uv run python -m keep_mcp.fastmcp_server`
- MCP Inspector（建議在開發時使用）：

  ```bash
  MCP_MEMORY_DB_PATH=/absolute/path/to/cards.db \
  uv run mcp dev src/keep_mcp/fastmcp_server.py --with-editable .
  ```

- 內建 smoke 測試（最小 stdio 客戶端）：

  ```bash
  uv run python scripts/smoke_stdio_client.py
  ```

## 指令速查

- 匯出卡片：`uv run keep-mcp export --db-path data/cards.db --destination data/export.ndjson`
- 檢視稽核紀錄：`uv run keep-mcp audit --db-path data/cards.db --limit 20`
- 偵錯排名與重複：`uv run keep-mcp debug --db-path data/cards.db --query "search terms" --top 5`
- 建立示範資料：`uv run keep-mcp seed --db-path data/cards.db --count 1000 --tags demo perf`

## 架構導覽

- `src/keep_mcp/adapters/`：定義 MCP 工具與對應的輸入/輸出轉換。
- `src/keep_mcp/services/`：核心網域邏輯（新增、召回、管理、匯出、排序、重複偵測、稽核）。
- `src/keep_mcp/storage/`：SQLite repository 與遷移程式，負責資料存取與 FTS5 維護。
- `src/keep_mcp/utils/`：時間、識別碼等輔助工具。
- `application.py` / `fastmcp_server.py`：應用程式組線與 FastMCP stdio/SSE 入口。
- CLI 入口：`cli.py`（匯出為 `keep-mcp` 命令）。

## 測試

- 全量測試：`uv run pytest`
- 建議組合：`uv run pytest tests/unit`、`uv run pytest tests/integration`、`uv run pytest -m contract`
- 標記說明：`unit`、`integration`、`contract`、`perf`（預設略過 `perf`）
- 測試共用 fixture 位於 `tests/conftest.py`

## 其他資源

- 工具詳細說明：`docs/tool-descriptions.md`
- SQLite 除錯教學：`docs/sqlite-utils-guide.md`
- 匯出、稽核、偵錯與種子資料等情境指令請參考 `README.md` 中的指令示例或 `keep-mcp --help`
- 若需自訂資料庫路徑與環境設定，可參考 `keep_mcp.storage.connection.resolve_db_path`
