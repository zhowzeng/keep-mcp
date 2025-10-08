from __future__ import annotations

from pathlib import Path
from typing import Any

from keep_mcp.adapters.errors import ExportFailed
from keep_mcp.services.export import ExportService
from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticValidationError

TOOL_NAME = "memory.export"

class ExportRequest(BaseModel):
    """Payload schema for export tool."""

    model_config = ConfigDict(extra="forbid")

    destinationPath: str | None = Field(
        default=None,
        description="Optional absolute path override for export file",
    )


_REQUEST_SCHEMA = ExportRequest.model_json_schema()
_REQUEST_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_REQUEST_SCHEMA["title"] = TOOL_NAME
REQUEST_SCHEMA: dict[str, Any] = _REQUEST_SCHEMA

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
    try:
        payload = ExportRequest.model_validate(request)
    except PydanticValidationError as exc:
        raise ExportFailed(exc.errors()[0]["msg"] if exc.errors() else str(exc)) from exc

    destination = payload.destinationPath
    if destination is not None and not Path(destination).is_absolute():
        raise ExportFailed("destinationPath must be absolute if provided")
    try:
        return await export_service.export(destination)
    except ExportFailed:
        raise
    except Exception as exc:  # pragma: no cover - export failures
        raise ExportFailed("Failed to export memory cards") from exc
