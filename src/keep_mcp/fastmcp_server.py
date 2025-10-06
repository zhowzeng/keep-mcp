from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Optional, Annotated, Literal, TypeAlias

from keep_mcp.adapters.errors import AdapterError
from keep_mcp.adapters.tools import add_card, export, manage, recall
from keep_mcp.main import Application, build_application
from keep_mcp.telemetry import get_logger

LOGGER = get_logger(__name__)

# FastMCP server
try:  # pragma: no cover
    from mcp.server.fastmcp import Context, FastMCP  # type: ignore
    from mcp.server.session import ServerSession  # type: ignore
    from mcp.shared.exceptions import McpError as ToolError  # type: ignore
except Exception as exc:  # pragma: no cover
    raise RuntimeError("The 'mcp' package is required to run the FastMCP server.") from exc

# --- Pydantic models (module scope for FastMCP annotation resolution) ---
from pydantic import BaseModel, Field

Tag: TypeAlias = Annotated[str, Field(min_length=1, max_length=60)]

class AddCardInput(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=120)]
    summary: Annotated[str, Field(min_length=1, max_length=500)]
    body: Optional[Annotated[str, Field(max_length=4000)]] = None
    tags: Optional[list[Tag]] = Field(default=None, max_items=20)
    originConversationId: Optional[str] = None
    originMessageExcerpt: Optional[Annotated[str, Field(max_length=280)]] = None

class AddCardOutput(BaseModel):
    cardId: str = Field(description="ULID")
    createdAt: str = Field(description="ISO 8601 date-time")
    merged: bool
    canonicalCardId: Optional[str] = None

class RecallInput(BaseModel):
    query: Optional[Annotated[str, Field(max_length=200)]] = None
    tags: Optional[list[Tag]] = Field(default=None, max_items=5)
    limit: int = Field(default=10, ge=1, le=25)
    includeArchived: bool = False

class RecallCard(BaseModel):
    cardId: str
    title: str
    summary: str
    body: Optional[str] = None
    tags: list[str] = []
    rankScore: float
    updatedAt: str
    lastRecalledAt: Optional[str] = None
    recallCount: int

class RecallOutput(BaseModel):
    cards: list[RecallCard]
    message: Optional[str] = None

class ManagePayload(BaseModel):
    title: Optional[Annotated[str, Field(max_length=120)]] = None
    summary: Optional[Annotated[str, Field(max_length=500)]] = None
    body: Optional[Annotated[str, Field(max_length=4000)]] = None
    tags: Optional[list[Tag]] = Field(default=None, max_items=20)

class ManageInput(BaseModel):
    cardId: str
    operation: Literal["UPDATE", "ARCHIVE", "DELETE"]
    payload: Optional[ManagePayload] = None

class ManageOutput(BaseModel):
    cardId: str
    status: Literal["UPDATED", "ARCHIVED", "DELETED"]
    updatedAt: Optional[str] = None

class ExportInput(BaseModel):
    destinationPath: Optional[str] = None

class ExportOutput(BaseModel):
    filePath: str
    exportedCount: int


@dataclass
class _Config:
    db_path: Path | str | None


def create_fastmcp(db_path: Path | str | None = None):
    """Create and return a FastMCP server instance.

    Exposed at module level for `mcp dev` / `mcp run` to import.
    """
    cfg = _Config(db_path=db_path)

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[Application]:  # type: ignore[name-defined]
        app = build_application(cfg.db_path)
        try:
            yield app
        finally:
            app.connection_close()

    mcp_server = FastMCP(name="mcp-memory", lifespan=lifespan)  # type: ignore[name-defined]

    async def tool_wrapper(func, *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return await func(*args, **kwargs)
        except AdapterError as exc:
            LOGGER.warning("tool.error", code=exc.code, message=exc.message)
            raise ToolError(exc.code, exc.message)  # type: ignore[name-defined]

    @mcp_server.tool()
    async def memory_add_card(
        payload: AddCardInput,
        ctx: Context[ServerSession, Application] | None = None,  # type: ignore[name-defined]
    ) -> AddCardOutput:
        app = ctx.request_context.lifespan_context if ctx else build_application(cfg.db_path)
        try:
            result = await tool_wrapper(add_card.execute, app.card_service, payload.model_dump(exclude_none=True))
            return AddCardOutput(**result)
        finally:
            if not ctx:
                app.connection_close()

    @mcp_server.tool()
    async def memory_recall(
        payload: RecallInput,
        ctx: Context[ServerSession, Application] | None = None,  # type: ignore[name-defined]
    ) -> RecallOutput:
        app = ctx.request_context.lifespan_context if ctx else build_application(cfg.db_path)
        try:
            result = await tool_wrapper(recall.execute, app.card_service, payload.model_dump(exclude_none=True))
            return RecallOutput(**result)
        finally:
            if not ctx:
                app.connection_close()

    @mcp_server.tool()
    async def memory_manage(
        payload: ManageInput,
        ctx: Context[ServerSession, Application] | None = None,  # type: ignore[name-defined]
    ) -> ManageOutput:
        app = ctx.request_context.lifespan_context if ctx else build_application(cfg.db_path)
        try:
            result = await tool_wrapper(manage.execute, app.card_service, payload.model_dump(exclude_none=True))
            return ManageOutput(**result)
        finally:
            if not ctx:
                app.connection_close()

    @mcp_server.tool()
    async def memory_export(
        payload: ExportInput,
        ctx: Context[ServerSession, Application] | None = None,  # type: ignore[name-defined]
    ) -> ExportOutput:
        app = ctx.request_context.lifespan_context if ctx else build_application(cfg.db_path)
        try:
            result = await tool_wrapper(export.execute, app.export_service, payload.model_dump(exclude_none=True))
            return ExportOutput(**result)
        finally:
            if not ctx:
                app.connection_close()

    return mcp_server


# Expose a module-level FastMCP instance for `mcp dev`
# The DB path will be resolved via keep_mcp.storage.connection.resolve_db_path,
# allowing override with the MCP_MEMORY_DB_PATH environment variable.
mcp = create_fastmcp()


def run_fastmcp_server(db_path: Path | str | None = None) -> None:
    """Run the FastMCP server over stdio (CLI entrypoint)."""
    server = create_fastmcp(db_path)
    server.run()


if __name__ == "__main__":  # pragma: no cover
    run_fastmcp_server()
