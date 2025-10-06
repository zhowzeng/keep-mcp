from __future__ import annotations

from typing import Any

from keep_mcp.adapters.errors import StorageFailure, ValidationError
from keep_mcp.services.cards import CardService

TOOL_NAME = "memory.add_card"

REQUEST_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": TOOL_NAME,
    "type": "object",
    "required": ["title", "summary"],
    "properties": {
        "title": {"type": "string", "minLength": 1, "maxLength": 120},
        "summary": {"type": "string", "minLength": 1, "maxLength": 500},
        "body": {"type": "string", "maxLength": 4000},
        "tags": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 60},
            "maxItems": 20,
            "uniqueItems": True,
        },
        "originConversationId": {"type": "string"},
        "originMessageExcerpt": {"type": "string", "maxLength": 280},
    },
    "additionalProperties": False,
}

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["cardId", "createdAt", "merged"],
    "properties": {
        "cardId": {"type": "string", "description": "ULID"},
        "createdAt": {"type": "string", "format": "date-time"},
        "merged": {"type": "boolean", "description": "True if the payload merged with an existing card"},
        "canonicalCardId": {
            "type": "string",
            "description": "Present when merged, pointing to surviving card",
        },
    },
    "additionalProperties": False,
}

ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["code", "message"],
    "properties": {
        "code": {"type": "string", "enum": ["VALIDATION_ERROR", "STORAGE_FAILURE"]},
        "message": {"type": "string"},
    },
}


async def execute(card_service: CardService, request: dict[str, Any]) -> dict[str, Any]:
    try:
        return await card_service.add_card(request)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - mapped to STORAGE_FAILURE
        raise StorageFailure("Failed to store memory card") from exc
