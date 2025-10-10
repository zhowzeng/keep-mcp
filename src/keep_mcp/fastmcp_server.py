from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, AsyncIterator, Literal

from keep_mcp.adapters.errors import AdapterError
from keep_mcp.adapters.tools import add_card, export, manage, recall
from keep_mcp.models import AddCardRequest, AddCardResponse, ExportResponse, ManageResponse, RecallResponse
from keep_mcp.application import Application, build_application
from keep_mcp.telemetry import get_logger

LOGGER = get_logger(__name__)
ADD_CARD_REQUEST_FIELDS = AddCardRequest.model_fields
RECALL_REQUEST_FIELDS = recall.RecallRequest.model_fields
MANAGE_REQUEST_FIELDS = manage.ManageRequest.model_fields
MANAGE_PAYLOAD_FIELDS = manage.ManagePayload.model_fields
EXPORT_REQUEST_FIELDS = export.ExportRequest.model_fields
AddCardOutput = AddCardResponse
RecallOutput = RecallResponse
ManageOutput = ManageResponse
ExportOutput = ExportResponse

# FastMCP server
try:  # pragma: no cover
    from mcp.server.fastmcp import Context, FastMCP  # type: ignore
    from mcp.server.session import ServerSession  # type: ignore
    from mcp.shared.exceptions import McpError as ToolError  # type: ignore
except Exception as exc:  # pragma: no cover
    raise RuntimeError("The 'mcp' package is required to run the FastMCP server.") from exc

@dataclass
class _Config:
    db_path: Path | str | None
    host: str
    port: int


def create_fastmcp(
    db_path: Path | str | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
):
    """Create and return a FastMCP server instance.

    Exposed at module level for `mcp dev` / `mcp run` to import.
    """
    cfg = _Config(db_path=db_path, host=host, port=port)

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[Application]:  # type: ignore[name-defined]
        app = build_application(cfg.db_path)
        try:
            yield app
        finally:
            app.connection_close()

    mcp_server = FastMCP(  # type: ignore[name-defined]
        name="mcp-memory",
        lifespan=lifespan,
        host=cfg.host,
        port=cfg.port,
    )

    async def tool_wrapper(func, *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return await func(*args, **kwargs)
        except AdapterError as exc:
            LOGGER.warning("tool.error", code=exc.code, message=exc.message)
            raise ToolError(exc.code, exc.message)  # type: ignore[name-defined]

    @mcp_server.tool(description="""Add a new memory card to the knowledge base.

Use this tool to store important information, facts, decisions, or context that should be remembered for future conversations. The system automatically detects and merges duplicates within a recent time window (7 days, 0.85 similarity threshold).

When to use:
- Storing key facts, decisions, or important context from conversations
- Capturing user preferences, project details, or domain knowledge
- Recording information that will be useful to recall later
- Building a persistent knowledge base across conversations

Parameters:
- title (required, ≤120 chars): Short, descriptive headline for the memory
- summary (required, ≤500 chars): Concise overview of the key information
- noteType (required, enum: FLEETING, LITERATURE, PERMANENT, INDEX): Classify the note within the Zettelkasten workflow
- body (optional, ≤4000 chars): Detailed content with full context and nuances
- tags (optional, ≤20 unique tags, each ≤60 chars): Categorization labels for filtering during recall
- originConversationId (optional): ID linking this card to its source conversation
- originMessageExcerpt (optional, ≤280 chars): Brief excerpt from the original message
- sourceReference (optional, ≤2048 chars): Citation, URL, or provenance for literature notes

Behavior:
- Returns cardId (ULID), createdAt timestamp, merged flag, and noteType
- If merged=true, canonicalCardId points to the surviving duplicate card
- Tags are normalized to lowercase slugs and deduplicated
- Duplicate detection uses TF-IDF cosine similarity on title+summary+body
- When merging with a different noteType, warnings help operators decide next steps
""")
    async def memory_add_card(
        title: Annotated[str, ADD_CARD_REQUEST_FIELDS["title"]],
        summary: Annotated[str, ADD_CARD_REQUEST_FIELDS["summary"]],
        noteType: Annotated[str, ADD_CARD_REQUEST_FIELDS["noteType"]],
        body: Annotated[str | None, ADD_CARD_REQUEST_FIELDS["body"]] = None,
        tags: Annotated[list[str] | None, ADD_CARD_REQUEST_FIELDS["tags"]] = None,
        originConversationId: Annotated[
            str | None, ADD_CARD_REQUEST_FIELDS["originConversationId"]
        ] = None,
        originMessageExcerpt: Annotated[
            str | None, ADD_CARD_REQUEST_FIELDS["originMessageExcerpt"]
        ] = None,
        sourceReference: Annotated[
            str | None, ADD_CARD_REQUEST_FIELDS["sourceReference"]
        ] = None,
        ctx: Context[ServerSession, Application] | None = None,  # type: ignore[name-defined]
    ) -> AddCardOutput:
        app = ctx.request_context.lifespan_context if ctx else build_application(cfg.db_path)
        try:
            request: dict[str, Any] = {
                "title": title,
                "summary": summary,
                "noteType": noteType,
            }
            if body is not None:
                request["body"] = body
            if tags is not None:
                request["tags"] = tags
            if originConversationId is not None:
                request["originConversationId"] = originConversationId
            if originMessageExcerpt is not None:
                request["originMessageExcerpt"] = originMessageExcerpt
            if sourceReference is not None:
                request["sourceReference"] = sourceReference
            result = await tool_wrapper(add_card.execute, app.card_service, request)
            return AddCardOutput(**result)
        finally:
            if not ctx:
                app.connection_close()

    @mcp_server.tool(description="""Retrieve relevant memory cards from the knowledge base.

Use this tool to search and recall stored information based on semantic similarity, tags, or recency. The ranking algorithm combines TF-IDF semantic matching, recency decay, and recall frequency penalty to surface the most relevant cards.

When to use:
- Looking up previously stored facts or context
- Finding information related to a specific topic or query
- Retrieving cards with specific tags or categories
- Checking what information is already known before adding duplicates
- Building context for continuing previous discussions

Parameters:
- query (optional, ≤200 chars): Natural language search text for semantic matching. If omitted, returns most recent cards.
- tags (optional, ≤5 unique tags): Filter to cards matching ALL specified tags (AND logic). Tags are matched by normalized slugs.
- limit (optional, 1-25, default=10): Maximum number of cards to return
- includeArchived (optional, default=false): Whether to include archived cards in results

Behavior:
- Returns cards sorted by rank score (higher = more relevant)
- Each recall increments the card's recallCount and updates lastRecalledAt
- Empty results return a friendly message field
- Ranking factors: semantic similarity (50%), recency (30%), recall penalty (20%)
- Full-text search uses FTS5 when query is provided
- Always logs audit entries for recall operations
""")
    async def memory_recall(
        query: Annotated[str | None, RECALL_REQUEST_FIELDS["query"]] = None,
        tags: Annotated[list[str] | None, RECALL_REQUEST_FIELDS["tags"]] = None,
        limit: Annotated[int, RECALL_REQUEST_FIELDS["limit"]] = 10,
        includeArchived: Annotated[bool, RECALL_REQUEST_FIELDS["includeArchived"]] = False,
        ctx: Context[ServerSession, Application] | None = None,  # type: ignore[name-defined]
    ) -> RecallOutput:
        app = ctx.request_context.lifespan_context if ctx else build_application(cfg.db_path)
        try:
            request: dict[str, Any] = {}
            if query is not None:
                request["query"] = query
            if tags is not None:
                request["tags"] = tags
            if limit is not None:
                request["limit"] = limit
            request["includeArchived"] = includeArchived
            result = await tool_wrapper(recall.execute, app.card_service, request)
            return RecallOutput(**result)
        finally:
            if not ctx:
                app.connection_close()

    @mcp_server.tool(description="""Update, archive, or delete an existing memory card.

Use this tool to modify or remove memory cards from the knowledge base. All operations create revision snapshots and audit logs for full traceability.

When to use:
- UPDATE: Modify card content (title, summary, body, tags) while preserving history
- ARCHIVE: Soft-delete a card (hidden from normal recall unless includeArchived=true)
- DELETE: Permanently remove a card and all its revisions (irreversible)

Parameters:
- cardId (required): ULID of the card to manage
- operation (required): One of UPDATE, ARCHIVE, DELETE
- title (UPDATE only, ≤120 chars): New title
- summary (UPDATE only, ≤500 chars): New summary
- body (UPDATE only, ≤4000 chars): New body content
- tags (UPDATE only, ≤20 unique tags): New tag set (replaces existing tags)
- noteType (UPDATE only): Change the note classification (FLEETING/LITERATURE/PERMANENT/INDEX)
- sourceReference (UPDATE only, ≤2048 chars): Update or clear the provenance reference

Behavior:
- UPDATE requires at least one field to modify; creates a REVISION snapshot before changes
- ARCHIVE sets isArchived=true; card remains in database but hidden from default recall
- DELETE removes the card and cascades to dependent rows (tags, revisions, audit logs)
- Returns status (UPDATED/ARCHIVED/DELETED) and updatedAt timestamp
- All operations are audited with operation type and actor tracking
- Raises NOT_FOUND if cardId doesn't exist

Best practices:
- Prefer ARCHIVE over DELETE to maintain history
- Use UPDATE to refine or expand existing cards rather than creating duplicates
- Check recall results before adding similar content
""")
    async def memory_manage(
        cardId: Annotated[str, MANAGE_REQUEST_FIELDS["cardId"]],
        operation: Annotated[str, MANAGE_REQUEST_FIELDS["operation"]],
        title: Annotated[str | None, MANAGE_PAYLOAD_FIELDS["title"]] = None,
        summary: Annotated[str | None, MANAGE_PAYLOAD_FIELDS["summary"]] = None,
        body: Annotated[str | None, MANAGE_PAYLOAD_FIELDS["body"]] = None,
        tags: Annotated[list[str] | None, MANAGE_PAYLOAD_FIELDS["tags"]] = None,
        noteType: Annotated[str | None, MANAGE_PAYLOAD_FIELDS["noteType"]] = None,
        sourceReference: Annotated[
            str | None, MANAGE_PAYLOAD_FIELDS["sourceReference"]
        ] = None,
        ctx: Context[ServerSession, Application] | None = None,  # type: ignore[name-defined]
    ) -> ManageOutput:
        app = ctx.request_context.lifespan_context if ctx else build_application(cfg.db_path)
        try:
            request: dict[str, Any] = {
                "cardId": cardId,
                "operation": operation,
            }
            # Only include payload for UPDATE
            payload_dict: dict[str, Any] = {}
            if title is not None:
                payload_dict["title"] = title
            if summary is not None:
                payload_dict["summary"] = summary
            if body is not None:
                payload_dict["body"] = body
            if tags is not None:
                payload_dict["tags"] = tags
            if noteType is not None:
                payload_dict["noteType"] = noteType
            if sourceReference is not None:
                payload_dict["sourceReference"] = sourceReference
            if payload_dict:
                request["payload"] = payload_dict
            result = await tool_wrapper(manage.execute, app.card_service, request)
            return ManageOutput(**result)
        finally:
            if not ctx:
                app.connection_close()

    @mcp_server.tool(description="""Export all memory cards to an NDJSON file.

Use this tool to create a complete backup of the knowledge base in newline-delimited JSON format. Each line contains one card with all its revisions.

When to use:
- Creating backups before major changes
- Migrating data to another system
- Analyzing the knowledge base with external tools
- Archiving historical snapshots for compliance
- Debugging or auditing the complete card collection

Parameters:
- destinationPath (optional): Absolute file path for the export. If omitted, generates a timestamped filename in the user's home directory (e.g., memory-export-20251006123045.jsonl)

Behavior:
- Exports all cards regardless of archived status
- Each line is a complete JSON object with card metadata and all revisions
- Includes: cardId, title, summary, body, tags, timestamps, recallCount, isArchived
- Also includes full revision history for each card
- Creates an audit log entry for the export operation
- Returns filePath and exportedCount

Output format (NDJSON):
- One JSON object per line
- Human-readable with standard formatting
- Compatible with jq, stream processing, and log analysis tools

Error handling:
- Raises EXPORT_FAILED if destinationPath is relative (must be absolute)
- Raises EXPORT_FAILED if file write fails
""")
    async def memory_export(
        destinationPath: Annotated[
            str | None, EXPORT_REQUEST_FIELDS["destinationPath"]
        ] = None,
        ctx: Context[ServerSession, Application] | None = None,  # type: ignore[name-defined]
    ) -> ExportOutput:
        app = ctx.request_context.lifespan_context if ctx else build_application(cfg.db_path)
        try:
            request: dict[str, Any] = {}
            if destinationPath is not None:
                request["destinationPath"] = destinationPath
            result = await tool_wrapper(export.execute, app.export_service, request)
            return ExportOutput(**result)
        finally:
            if not ctx:
                app.connection_close()

    return mcp_server


# Expose a module-level FastMCP instance for `mcp dev`
# The DB path will be resolved via keep_mcp.storage.connection.resolve_db_path,
# allowing override with the MCP_MEMORY_DB_PATH environment variable.
mcp = create_fastmcp()


def run_fastmcp_server(
    db_path: Path | str | None = None,
    *,
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    mount_path: str | None = None,
) -> None:
    """Run the FastMCP server using the requested transport (CLI entrypoint)."""
    server = create_fastmcp(db_path, host=host, port=port)
    if transport == "sse":
        server.run(transport=transport, mount_path=mount_path)
        return
    server.run(transport=transport)


if __name__ == "__main__":  # pragma: no cover
    run_fastmcp_server()
