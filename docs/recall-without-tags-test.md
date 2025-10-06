# Recall 功能測試結果

## 概述

根據測試結果，`memory.recall` 工具**已經完全支援**沒有 tags 的情況。tags 參數是完全可選的。

## 測試場景

### 1. 空 tags 列表
```python
await card_service.recall(
    query="test card",
    tags=[],
    limit=5,
    include_archived=False,
)
```
✅ **通過** - 正常返回結果

### 2. 沒有 query 和空 tags
```python
await card_service.recall(
    query=None,
    tags=[],
    limit=5,
    include_archived=False,
)
```
✅ **通過** - 返回所有卡片（按排名排序）

### 3. 只有 query，沒有 tags
```python
await card_service.recall(
    query="test",
    tags=[],
    limit=5,
    include_archived=False,
)
```
✅ **通過** - 基於語義相似度返回結果

## 實作細節

### 在 `services/cards.py` 中：
```python
async def recall(
    self,
    query: str | None,
    tags: Iterable[str],
    limit: int,
    include_archived: bool,
) -> dict[str, Any]:
    # ...
    tags_list = list(tags)
    candidates = await asyncio.to_thread(self._cards.list_canonical_cards, include_archived)

    if tags_list:  # 只有當 tags 非空時才進行過濾
        tag_slugs = [*{self._slug_from_label(label) for label in tags_list if label.strip()}]
        matching_ids = await asyncio.to_thread(self._tags.find_cards_with_tags, tag_slugs)
        candidates = [card for card in candidates if card.card_id in matching_ids]
    # ...
```

### 在 `adapters/tools/recall.py` 中：
```python
REQUEST_SCHEMA: dict[str, Any] = {
    # ...
    "properties": {
        "query": {"type": "string", "maxLength": 200},
        "tags": {  # 沒有 "required" 標記
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 60},
            "maxItems": 5,
            "uniqueItems": True,
        },
        # ...
    },
    "additionalProperties": False,
}
```

### 在 `fastmcp_server.py` 中：
```python
async def memory_recall(
    query: Optional[Annotated[str, Field(max_length=200)]] = None,
    tags: Optional[list[Tag]] = Field(default=None, max_items=5),  # Optional with default=None
    limit: int = Field(default=10, ge=1, le=25),
    includeArchived: bool = False,
    ctx: Context[ServerSession, Application] | None = None,
) -> RecallOutput:
```

## 行為說明

1. **當 tags 為空或未提供時**：
   - 不進行 tag 過濾
   - 返回所有候選卡片（根據 `include_archived` 設定）

2. **排名機制**：
   - 語義相似度（50%）：基於 TF-IDF 和 query 的相似度
   - 時間衰減（30%）：較新的卡片排名更高
   - 回憶懲罰（20%）：頻繁被回憶的卡片排名略降

3. **無 query 和無 tags 的情況**：
   - 返回所有卡片，按時間排序（最新的優先）
   - 適合瀏覽整個知識庫

## 文件說明

在 `docs/tool-descriptions.md` 和 `fastmcp_server.py` 中的工具描述都明確標示：

- `tags` (optional, ≤5 unique): Filter by tags (ALL must match)
- `query` (optional, ≤200 chars): Natural language search text

## 測試覆蓋

- ✅ `tests/integration/test_recall_no_tags.py` - 專門測試無 tags 場景
- ✅ `tests/integration/test_recall_flow.py` - 測試有 tags 的場景
- ✅ `tests/integration/test_manage_card.py` - 測試多種 recall 組合
- ✅ `scripts/test_recall_no_tags.py` - 實際應用層面的測試

## 結論

`memory.recall` 工具已經**完全支援沒有 tags** 的使用場景。tags 參數是可選的，可以：

- 傳入空列表 `[]`
- 傳入 `None`（在 FastMCP 層級）
- 完全不提供（使用預設值）

所有這些情況都能正常工作，並會返回合適的結果。
