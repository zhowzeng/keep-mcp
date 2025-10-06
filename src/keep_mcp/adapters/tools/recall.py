from __future__ import annotations

from typing import Any

from keep_mcp.adapters.errors import StorageFailure, ValidationError
from keep_mcp.services.cards import CardService

TOOL_NAME = "memory.recall"

REQUEST_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": TOOL_NAME,
    "type": "object",
    "properties": {
        "query": {"type": "string", "maxLength": 200},
        "tags": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 60},
            "maxItems": 5,
            "uniqueItems": True,
        },
        "limit": {"type": "integer", "minimum": 1, "maximum": 25},
        "includeArchived": {"type": "boolean", "default": False},
    },
    "additionalProperties": False,
}

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["cards"],
    "properties": {
        "cards": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "cardId",
                    "title",
                    "summary",
                    "rankScore",
                    "updatedAt",
                    "recallCount",
                ],
                "properties": {
                    "cardId": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "body": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "rankScore": {"type": "number"},
                    "updatedAt": {"type": "string", "format": "date-time"},
                    "lastRecalledAt": {"type": "string", "format": "date-time"},
                    "recallCount": {"type": "integer"},
                },
                "additionalProperties": False,
            },
        },
        "message": {
            "type": "string",
            "description": "Friendly message when cards array is empty",
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
        limit = int(request.get("limit", 10)) if request.get("limit") is not None else 10
        include_archived = bool(request.get("includeArchived", False))
        tags = request.get("tags") or []
        if not isinstance(tags, list):
            raise ValidationError("tags must be an array of strings")
        result = await card_service.recall(
            query=request.get("query"),
            tags=tags,
            limit=limit,
            include_archived=include_archived,
        )
        if result.get("message") is None:
            result.pop("message", None)
        return result
    except ValidationError:
        raise
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - mapped to STORAGE_FAILURE
        raise StorageFailure("Failed to recall memory cards") from exc
