from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# Prefer the SDK's shared exception type if available; fall back to RuntimeError-compatible shim.
try:  # pragma: no cover
    from mcp.shared.exceptions import McpError as ToolError  # type: ignore[assignment]
except Exception:  # pragma: no cover
    class ToolError(RuntimeError):
        def __init__(self, code: str, message: str) -> None:
            super().__init__(f"{code}: {message}")
            self.code = code
            self.message = message

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


# Keep only application wiring in this module; FastMCP server lives in fastmcp_server.py
