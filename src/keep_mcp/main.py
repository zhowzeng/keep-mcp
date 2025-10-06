from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:  # type checking only
    from mcp.server import Server as _Server
    from mcp.server.stdio import stdio_server as _stdio_server
    ServerT = _Server
else:  # runtime: avoid hard import requirement for type checker
    ServerT = Any
    _stdio_server = None  # type: ignore[assignment]

try:  # pragma: no cover - import guard for optional runtime dependency
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:  # pragma: no cover
    Server = None  # type: ignore[assignment]
    stdio_server = None  # type: ignore[assignment]

# Prefer the SDK's shared exception type if available; fall back to RuntimeError-compatible shim.
try:  # pragma: no cover
    from mcp.shared.exceptions import McpError as ToolError  # type: ignore[assignment]
except Exception:  # pragma: no cover
    class ToolError(RuntimeError):
        def __init__(self, code: str, message: str) -> None:
            super().__init__(f"{code}: {message}")
            self.code = code
            self.message = message

from keep_mcp.adapters.errors import AdapterError
from keep_mcp.adapters.tools import add_card, export, manage, recall
from keep_mcp.services import (
    AuditService,
    CardService,
    DuplicateDetectionService,
    ExportService,
    RankingService,
)
from keep_mcp.storage.audit_repository import AuditLogRepository
from keep_mcp.storage.connection import create_connection, resolve_db_path
from keep_mcp.storage.migrations import apply_migrations
from keep_mcp.storage.repository import CardRepository
from keep_mcp.storage.revision_repository import RevisionRepository
from keep_mcp.storage.tag_repository import TagRepository
from keep_mcp.telemetry import configure_logging, get_logger

LOGGER = get_logger(__name__)


@dataclass(slots=True)
class Application:
    card_service: CardService
    export_service: ExportService
    card_repository: CardRepository
    revision_repository: RevisionRepository
    tag_repository: TagRepository
    audit_service: AuditService
    duplicate_service: DuplicateDetectionService
    ranking_service: RankingService
    connection_close: Callable[[], None]
    db_path: Path


def build_application(db_path: str | Path | None = None) -> Application:
    resolved_path = resolve_db_path(db_path)
    connection = create_connection(resolved_path)
    apply_migrations(connection)

    card_repository = CardRepository(connection)
    revision_repository = RevisionRepository(connection)
    tag_repository = TagRepository(connection)
    audit_repository = AuditLogRepository(connection)

    audit_service = AuditService(audit_repository)
    duplicate_service = DuplicateDetectionService()
    ranking_service = RankingService()
    card_service = CardService(
        card_repository=card_repository,
        revision_repository=revision_repository,
        tag_repository=tag_repository,
        duplicate_service=duplicate_service,
        ranking_service=ranking_service,
        audit_service=audit_service,
    )
    export_service = ExportService(card_repository, revision_repository, audit_service)

    def close_connection() -> None:
        with contextlib.suppress(Exception):
            connection.close()

    LOGGER.debug("application.initialised", db_path=str(resolved_path))
    return Application(
        card_service=card_service,
        export_service=export_service,
        card_repository=card_repository,
        revision_repository=revision_repository,
        tag_repository=tag_repository,
        audit_service=audit_service,
        duplicate_service=duplicate_service,
        ranking_service=ranking_service,
        connection_close=close_connection,
        db_path=resolved_path,
    )


async def register_tools(server: ServerT, app: Application) -> None:
    async def tool_wrapper(func: Callable[..., Awaitable[dict[str, Any]]], *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return await func(*args, **kwargs)
        except AdapterError as exc:
            LOGGER.warning("tool.error", code=exc.code, message=exc.message)
            raise ToolError(exc.code, exc.message) from exc

    @server.tool(  # type: ignore[attr-defined]
        add_card.TOOL_NAME,
        add_card.REQUEST_SCHEMA,
        add_card.RESPONSE_SCHEMA,
        add_card.ERROR_SCHEMA,
    )
    async def memory_add_card(request: dict[str, Any]) -> dict[str, Any]:
        return await tool_wrapper(add_card.execute, app.card_service, request)

    @server.tool(  # type: ignore[attr-defined]
        recall.TOOL_NAME,
        recall.REQUEST_SCHEMA,
        recall.RESPONSE_SCHEMA,
        recall.ERROR_SCHEMA,
    )
    async def memory_recall(request: dict[str, Any]) -> dict[str, Any]:
        return await tool_wrapper(recall.execute, app.card_service, request)

    @server.tool(  # type: ignore[attr-defined]
        manage.TOOL_NAME,
        manage.REQUEST_SCHEMA,
        manage.RESPONSE_SCHEMA,
        manage.ERROR_SCHEMA,
    )
    async def memory_manage(request: dict[str, Any]) -> dict[str, Any]:
        return await tool_wrapper(manage.execute, app.card_service, request)

    @server.tool(  # type: ignore[attr-defined]
        export.TOOL_NAME,
        export.REQUEST_SCHEMA,
        export.RESPONSE_SCHEMA,
        export.ERROR_SCHEMA,
    )
    async def memory_export(request: dict[str, Any]) -> dict[str, Any]:
        return await tool_wrapper(export.execute, app.export_service, request)


async def run_stdio_server(db_path: str | Path | None = None) -> None:
    if Server is None or stdio_server is None:
        raise RuntimeError("The 'mcp' package is required to run the memory server.")

    server = Server("mcp-memory")  # type: ignore[call-arg]
    app = build_application(db_path)
    try:
        await register_tools(server, app)
        # pyright: ignore[reportGeneralTypeIssues]
        await stdio_server(server)  # type: ignore[misc]
    finally:
        app.connection_close()


def main() -> None:
    configure_logging()
    asyncio.run(run_stdio_server())


if __name__ == "__main__":
    main()
