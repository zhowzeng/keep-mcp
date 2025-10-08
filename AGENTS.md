# 儲存庫指南

本文整合儲存庫指南與 Copilot 指引，提供貢獻者與 AI 代理的一套去重後說明。

## 架構與邊界
- `src/keep_mcp/` 下的層級：
  - `adapters/` 對外暴露 MCP 工具與結構；負責轉換輸入輸出並將例外對應到 AdapterError 代碼。
  - `services/` 包含網域邏輯（新增/擷取/管理/匯出、排序、重複偵測、稽核）。
  - `storage/` 提供 SQLite repository 與具冪等的遷移程式；此層不放商業邏輯。
  - `utils/` 放置小型輔助工具（時間、識別碼等）。
- 應用程式的組線定義在 `application.py` (`build_application`) 與 `fastmcp_server.py`（FastMCP stdio 工具）。CLI 進入點為 `cli.py`。
- 資料流：FastMCP tool → adapter `adapters/tools/*` → `CardService`/`ExportService` → repositories → SQLite。
- 儲存層的存取維持在各 repository 內，對外提供型別化模型（例如 `MemoryCard`）。
- 測試結構與層級對應 `tests/{unit,integration,contract,perf}`；共用 fixture 位於 `tests/conftest.py`。

## 開發流程
- 環境：Python 3.12 搭配 uv。
  - 安裝依賴：`uv sync`
  - 執行資料庫遷移：`uv run keep-mcp migrate --db-path data/cards.db`
  - 啟動 FastMCP 伺服器（stdio）：`uv run keep-mcp serve --db-path data/cards.db` 或 `uv run python -m keep_mcp.fastmcp_server`
  - 煙霧測試 stdio client：`uv run python scripts/smoke_stdio_client.py`
  - 執行測試：`uv run pytest`（請參考 `pytest.ini` 中的標記）；較重的效能測試使用 `@pytest.mark.perf`。
  - 匯出/稽核/偵錯/種子資料請參考 `README.md` 的指令變化（`keep-mcp export|audit|debug|seed`）。
- 推薦測試組合：`uv run pytest tests/unit`、`uv run pytest tests/integration` 或 `uv run pytest -m contract`。
- Codex CLI 注意：在沙箱環境下執行 `uv run …` 需要讀取全域快取，請使用 `with_escalated_permissions=true` 參數提交命令，以免觸發 `Permission denied`。

## 工具契約與結構
- 每個 MCP 工具位於 `adapters/tools/`，需定義：
  - `TOOL_NAME`、`REQUEST_SCHEMA`、`RESPONSE_SCHEMA`，以及選用的 `ERROR_SCHEMA`。
  - 非同步 `execute(service, request)`，負責驗證/正規化並呼叫服務層。
  - 驗證失敗對應 `ValidationError`；預期外的錯誤對應 `StorageFailure`（或更特化的代碼）。
- FastMCP（`fastmcp_server.py`）以個別頂層參數暴露工具（無巢狀 payload）。它會組成請求 dict 呼叫 adapter，並將 adapter 例外包裝成 `McpError`。輸出維持 Pydantic 模型確保清楚結構。
- 每個工具在 `@mcp_server.tool(description=...)` 裡提供完整描述，協助 LLM 理解：
  - 工具用途與適用情境
  - 詳細參數說明與限制
  - 行為特性與副作用
  - 最佳實務與常見範例
  - 可能的錯誤情境與處理方式

## 服務層行為重點
- `CardService.add_card` 使用 `DuplicateDetectionService`（TF-IDF cosine、char_wb N-grams）在最近時間窗內進行重複合併。若合併則以 slug 去重後合併標籤，並記錄 MERGE 修訂。
- `CardService.recall` 透過 `RankingService`（語意 TF-IDF、時間衰減、召回懲罰）排序，更新召回計數並寫入稽核紀錄。標籤篩選使用 `TagRepository.find_cards_with_tags` 依 slug 查詢。
- `CardService.manage_card` 支援 UPDATE/ARCHIVE/DELETE，伴隨快照修訂與稽核紀錄；DELETE 會清除 repository 中的相依資料列。
- `ExportService.export` 以 NDJSON 串流所有卡片與修訂，並記錄稽核事件。

## 儲存與遷移
- 遷移程式位於 `storage/migrations.py`，透過 `sqlite-utils` 實作冪等操作；FTS5 資料表與觸發器保持 `memory_card_search` 同步。
- Repository（`storage/repository.py`、`revision_repository.py`、`tag_repository.py`、`audit_repository.py`）是唯一與 SQLite 互動的位置；商業規則請勿放在此層。

## 命名、風格與日誌
- 遵循 PEP 8 並使用型別標註；值物件（例如 `RankedCard`、`DuplicateMatch`）採用 dataclass。
- 命名慣例：函式與變數用 `snake_case`，類別與 dataclass 用 `PascalCase`。
- 使用 `telemetry.get_logger()` 進行結構化日誌；避免使用 `print`。必要時可搭配 `telemetry.bind_context` 提供上下文。
- 將使用者可見的結構定義保留在 adapter 附近；字串長度限制需符合服務與結構（title 120、summary 500、body 4000、tag 60、excerpt 280）。
- 請遵守限制：recall `limit` 為 1..25；標籤唯一，召回最多 5 個、卡片 payload 最多 20 個。
- 服務層透過 `asyncio.to_thread(...)` 將 repository 與 CPU/IO 工作移出事件迴圈以維持回應性，請保留此模式。
- 識別碼為 ULID（`identifiers.new_ulid()`）；全程以字串處理。

## 測試指南
- Pytest 標記：`unit`、`integration`、`contract`、`perf`（效能場景預設略過）。
- 測試命名採 `test_<feature>.py`；函式名稱建議敘述性，如 `test_manage_card_updates_tags`。
- 契約/整合測試需使用初始化的資料庫；請在設定階段執行遷移命令或重用 `tests/conftest.py` 的 fixture。

## Commit 與 Pull Request 指南
- 採用 Conventional Commits（`feat:`、`fix:`、`chore:`）；標題限制 72 字元以內。
- PR 需連結驅動議題、摘要行為變更、凸顯新指令/腳本，並附上 CLI 輸出或介面截圖（如有使用者影響）。

## 環境與資料安全
- 資料庫路徑預設為使用者設定目錄；請傳入 `--db-path` 以隔離測試資料庫並避免污染實際資料。
- 請勿提交產生的 SQLite 檔或 NDJSON 匯出；`.gitignore` 已忽略這些檔案。
- 確保遙測資料不包含祕密或個人資訊再進行合併。

## 新增工具時
- 在 `adapters/tools/*` 定義結構與 `execute`，並新增 FastMCP 包裝器返回 Pydantic 模型。
- 連結至 service 方法；只有在儲存結構需要時才新增 repository 方法。
- 更新 `tests/{unit,integration}` 下的測試；若需要新資料表/索引，請於 `storage/migrations.py` 撰寫遷移。

## 範例
- 召回 adapter 範例：請參考 `adapters/tools/recall.py` 了解請求/回應結構、驗證與錯誤對應。
- 排序訊號：`services/ranking.py` 結合語意相似度、時間衰減與召回懲罰。
- 重複偵測：`services/duplicate.py` 使用 0.85 門檻與輕量的字詞層防護。

### 工具速查表
- memory.add_card → `adapters/tools/add_card.py`
  - 必填：title (<=120)、summary (<=500)
  - 選填：body (<=4000)、tags (<=20)、originConversationId、originMessageExcerpt (<=280)
- memory.recall → `adapters/tools/recall.py`
  - 選填：query (<=200)、tags (<=5 unique)、limit 1..25、includeArchived
- memory.manage → `adapters/tools/manage.py`
  - 必填：cardId，operation 需為 [UPDATE, ARCHIVE, DELETE]
  - UPDATE 載荷：title/summary/body/tags (<=20)
- memory.export → `adapters/tools/export.py`
  - 選填：destinationPath (absolute)

範例（FastMCP 參數風格）：

- memory.add_card(title, summary, body?, tags?, originConversationId?, originMessageExcerpt?)
- memory.recall(query?, tags?, limit?, includeArchived?)
- memory.manage(cardId, operation, title?, summary?, body?, tags?)
- memory.export(destinationPath?)

```try-it
# 常用單行指令
uv run keep-mcp migrate --db-path data/cards.db
uv run keep-mcp serve --db-path data/cards.db
uv run keep-mcp export --db-path data/cards.db --destination data/export.ndjson
uv run keep-mcp audit --db-path data/cards.db --limit 20
uv run keep-mcp debug --db-path data/cards.db --query "search terms" --top 5
uv run keep-mcp seed --db-path data/cards.db --count 1000 --tags demo perf

# 其他進入點（選用）
uv run python -m keep_mcp.fastmcp_server
uv run python scripts/smoke_stdio_client.py
```

## 備註
- 已移除舊有的 `cli` 指令別名，請改用 `keep-mcp`。
- 與此儲存庫互動的 AI 代理除專有名詞或程式碼外，應以繁體中文回應。
