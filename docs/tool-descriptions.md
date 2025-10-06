# MCP Tool Descriptions

This document provides an overview of the detailed descriptions added to each MCP tool to help LLMs understand and use them effectively.

## Overview

Each MCP tool in `fastmcp_server.py` includes comprehensive descriptions that cover:

1. **Purpose**: What the tool does at a high level
2. **When to use**: Specific use cases and scenarios
3. **Parameters**: Detailed explanation of each parameter with constraints
4. **Behavior**: How the tool works internally, side effects, and guarantees
5. **Best practices**: Recommendations for optimal usage
6. **Error handling**: Common error conditions and how they're handled

## Tool Descriptions

### memory.add_card

**Purpose**: Store important information in the knowledge base

**Key Features**:
- Automatic duplicate detection and merging (7-day window, 0.85 similarity threshold)
- Tag normalization and deduplication
- Support for conversation origin tracking
- TF-IDF cosine similarity for duplicate detection

**When to use**:
- Storing key facts or decisions from conversations
- Capturing user preferences or project details
- Building a persistent knowledge base

**Parameters**:
- `title` (required, ≤120 chars): Short headline
- `summary` (required, ≤500 chars): Concise overview
- `body` (optional, ≤4000 chars): Detailed content
- `tags` (optional, ≤20 unique): Categorization labels
- `originConversationId` (optional): Source conversation ID
- `originMessageExcerpt` (optional, ≤280 chars): Original message excerpt

**Returns**:
- `cardId`: ULID identifier
- `createdAt`: ISO 8601 timestamp
- `merged`: Boolean indicating if merged with existing card
- `canonicalCardId`: Present when merged, points to surviving card

---

### memory.recall

**Purpose**: Search and retrieve relevant memory cards

**Key Features**:
- Semantic similarity ranking using TF-IDF
- Tag-based filtering (AND logic)
- Recency decay and recall penalty
- FTS5 full-text search
- Automatic audit logging

**When to use**:
- Looking up previously stored information
- Finding topic-related cards
- Checking for existing content before adding duplicates
- Building context for continuing discussions

**Parameters**:
- `query` (optional, ≤200 chars): Natural language search text
- `tags` (optional, ≤5 unique): Filter by tags (ALL must match)
- `limit` (optional, 1-25, default=10): Max results
- `includeArchived` (optional, default=false): Include archived cards

**Ranking Algorithm**:
- Semantic similarity: 50%
- Recency decay: 30%
- Recall penalty: 20%

**Returns**:
- `cards`: Array of ranked cards with metadata
- `message`: Friendly message when no results found

---

### memory.manage

**Purpose**: Update, archive, or delete existing memory cards

**Key Features**:
- Three operation modes: UPDATE, ARCHIVE, DELETE
- Revision snapshots for all changes
- Full audit trail
- Cascade deletion of dependent data

**When to use**:
- **UPDATE**: Modify card content while preserving history
- **ARCHIVE**: Soft-delete (hidden from normal recall)
- **DELETE**: Permanently remove card and revisions

**Parameters**:
- `cardId` (required): ULID of card to manage
- `operation` (required): UPDATE, ARCHIVE, or DELETE
- `title` (UPDATE only, ≤120 chars): New title
- `summary` (UPDATE only, ≤500 chars): New summary
- `body` (UPDATE only, ≤4000 chars): New body
- `tags` (UPDATE only, ≤20 unique): New tag set (replaces existing)

**Best Practices**:
- Prefer ARCHIVE over DELETE to maintain history
- Use UPDATE to refine cards instead of creating duplicates
- Check recall results before adding similar content

**Returns**:
- `cardId`: Card identifier
- `status`: UPDATED, ARCHIVED, or DELETED
- `updatedAt`: Timestamp (for UPDATE and ARCHIVE)

---

### memory.export

**Purpose**: Create a complete backup of the knowledge base

**Key Features**:
- NDJSON format (one JSON object per line)
- Includes all cards regardless of archived status
- Full revision history included
- Audit log entry created
- Compatible with jq and stream processing tools

**When to use**:
- Creating backups before major changes
- Migrating data to another system
- Analyzing the knowledge base with external tools
- Archiving historical snapshots

**Parameters**:
- `destinationPath` (optional): Absolute file path for export
  - If omitted, generates timestamped filename in home directory
  - Example: `memory-export-20251006123045.jsonl`

**Output Format**:
- One JSON object per line
- Includes: cardId, title, summary, body, tags, timestamps, recallCount, isArchived
- Full revision history for each card
- Human-readable formatting

**Returns**:
- `filePath`: Path to exported file
- `exportedCount`: Number of cards exported

**Error Handling**:
- Raises EXPORT_FAILED if destinationPath is relative
- Raises EXPORT_FAILED if file write fails

---

## Implementation Details

### Location
All tool descriptions are defined in `/src/keep_mcp/fastmcp_server.py` using the `@mcp_server.tool(description=...)` decorator.

### Format
Descriptions use multi-line strings with clear sections:
```python
@mcp_server.tool(description="""<Title>

<Purpose paragraph>

When to use:
- <Use case 1>
- <Use case 2>

Parameters:
- <param1>: <description with constraints>
- <param2>: <description with constraints>

Behavior:
- <Behavior detail 1>
- <Behavior detail 2>

Best practices (if applicable):
- <Practice 1>
- <Practice 2>
""")
async def tool_name(...):
    ...
```

### Benefits for LLMs
1. **Context understanding**: LLMs can better understand when and how to use each tool
2. **Parameter guidance**: Clear constraints help prevent validation errors
3. **Behavior awareness**: Understanding side effects leads to better usage patterns
4. **Best practices**: Built-in guidance for optimal tool usage
5. **Error prevention**: Awareness of error conditions helps avoid common mistakes

## Testing

To verify tool descriptions are properly exposed:
```bash
uv run python scripts/check_tool_descriptions.py
```

This script checks that all tools have comprehensive descriptions and displays previews.

## Maintenance

When adding or modifying tools:
1. Update the tool implementation in `adapters/tools/`
2. Update the FastMCP wrapper in `fastmcp_server.py`
3. Add or update the comprehensive description
4. Update this documentation
5. Run tests to ensure no regressions
