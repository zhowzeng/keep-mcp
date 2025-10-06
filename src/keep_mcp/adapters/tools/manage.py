from __future__ import annotations

from typing import Any

from keep_mcp.adapters.errors import NotFoundError, StorageFailure, ValidationError
from keep_mcp.services.cards import CardService

TOOL_NAME = "memory.manage"

REQUEST_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": TOOL_NAME,
    "type": "object",
    "required": ["cardId", "operation"],
    "properties": {
        "cardId": {"type": "string"},
        "operation": {"type": "string", "enum": ["UPDATE", "ARCHIVE", "DELETE"]},
        "payload": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "maxLength": 120},
                "summary": {"type": "string", "maxLength": 500},
                "body": {"type": "string", "maxLength": 4000},
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1, "maxLength": 60},
                    "maxItems": 20,
                    "uniqueItems": True,
                },
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
    "allOf": [
        {
            "if": {"properties": {"operation": {"const": "UPDATE"}}},
            "then": {"required": ["payload"]},
        }
    ],
}

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["cardId", "status"],
    "properties": {
        "cardId": {"type": "string"},
        "status": {"type": "string", "enum": ["UPDATED", "ARCHIVED", "DELETED"]},
        "updatedAt": {"type": "string", "format": "date-time"},
    },
    "additionalProperties": False,
}

ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["code", "message"],
    "properties": {
        "code": {
            "type": "string",
            "enum": ["NOT_FOUND", "VALIDATION_ERROR", "STORAGE_FAILURE"],
        },
        "message": {"type": "string"},
    },
}


async def execute(card_service: CardService, request: dict[str, Any]) -> dict[str, Any]:
    try:
        card_id = request.get("cardId")
        operation = request.get("operation")
        if not isinstance(card_id, str) or not card_id.strip():
            raise ValidationError("cardId is required")
        if operation not in {"UPDATE", "ARCHIVE", "DELETE"}:
            raise ValidationError("operation must be UPDATE, ARCHIVE, or DELETE")
        payload = request.get("payload") if isinstance(request.get("payload"), dict) else None
        return await card_service.manage_card(card_id, operation, payload)
    except ValidationError:
        raise
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise NotFoundError(message) from exc
        raise ValidationError(message) from exc
    except Exception as exc:  # pragma: no cover - mapped to STORAGE_FAILURE
        raise StorageFailure("Failed to manage memory card") from exc
