from __future__ import annotations

from pathlib import Path
from typing import Any

from keep_mcp.adapters.errors import ExportFailed
from keep_mcp.services.export import ExportService

TOOL_NAME = "memory.export"

REQUEST_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": TOOL_NAME,
    "type": "object",
    "properties": {
        "destinationPath": {
            "type": "string",
            "description": "Optional absolute path override for export file",
        }
    },
    "additionalProperties": False,
}

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["filePath", "exportedCount"],
    "properties": {
        "filePath": {"type": "string"},
        "exportedCount": {"type": "integer", "minimum": 0},
    },
    "additionalProperties": False,
}

ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["code", "message"],
    "properties": {
        "code": {"type": "string", "enum": ["EXPORT_FAILED"]},
        "message": {"type": "string"},
    },
}


async def execute(export_service: ExportService, request: dict[str, Any]) -> dict[str, Any]:
    destination = request.get("destinationPath")
    if destination is not None and not Path(destination).is_absolute():
        raise ExportFailed("destinationPath must be absolute if provided")
    try:
        return await export_service.export(destination)
    except ExportFailed:
        raise
    except Exception as exc:  # pragma: no cover - export failures
        raise ExportFailed("Failed to export memory cards") from exc
