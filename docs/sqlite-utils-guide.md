# 使用 sqlite-utils 檢視資料庫

本指南整理常用的 `sqlite-utils` 指令，協助開發者與除錯流程快速檢視 `keep-mcp` 所使用的 SQLite 資料庫內容。所有指令皆可針對預設路徑 `data/cards.db` 或自訂的 `--db-path` 執行。

## 安裝方式

- 建議透過 `uv` 安裝成工具：`uv tool install sqlite-utils`
- 或使用 `uvx` 直接執行一次性指令：`uvx sqlite-utils --help`
- 若偏好 `pipx`，可執行：`pipx install sqlite-utils`

> **注意**：在 Codex CLI 或其他沙箱環境中執行 `sqlite-utils` 時，可能需要提升權限以存取本機快取；請記得啟用 `with_escalated_permissions=true`。

## 基本資訊查詢

- 列出所有資料表與簡要統計：

  ```bash
  uvx sqlite-utils tables data/cards.db
  ```

- 檢視資料表結構（欄位、索引、觸發器）：

  ```bash
  uvx sqlite-utils schema data/cards.db memory_card
  ```

- 顯示資料表前幾筆資料，快速確認欄位內容：

  ```bash
  uvx sqlite-utils rows data/cards.db memory_card --limit 5
  ```

## 常見除錯範例

- 查詢具有特定標籤的卡片：

  ```bash
  uvx sqlite-utils query data/cards.db \
    "SELECT mc.title, mt.slug
     FROM memory_card mc
     JOIN memory_card_tag mct ON mc.id = mct.card_id
     JOIN memory_tag mt ON mt.id = mct.tag_id
     WHERE mt.slug = 'demo'
     ORDER BY mc.created_at DESC
     LIMIT 10;"
  ```

- 確認全文索引觸發器是否同步：

  ```bash
  uvx sqlite-utils query data/cards.db \
    "SELECT name, sql FROM sqlite_master
     WHERE type = 'trigger' AND name LIKE 'memory_card_search_%';"
  ```

- 檢視最新的稽核紀錄：

  ```bash
  uvx sqlite-utils query data/cards.db \
    "SELECT action, card_id, created_at, payload
     FROM audit_log
     ORDER BY created_at DESC
     LIMIT 20;"
  ```

## 建立測試資料後再檢視

若需要立即可用的測試資料，可先建立資料庫並匯入示範資料，再透過 `sqlite-utils` 驗證：

```bash
uv run keep-mcp migrate --db-path data/cards.db
uv run keep-mcp seed --db-path data/cards.db --count 10 --tags demo tutorial
uvx sqlite-utils tables data/cards.db
```

透過上述流程即可快速確認資料表與示範資料是否正確寫入，也能搭配自訂查詢檢視特定卡片、修訂與稽核內容。
