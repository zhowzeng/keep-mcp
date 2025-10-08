from __future__ import annotations

from typing import Any, Annotated

from keep_mcp.adapters.errors import StorageFailure, ValidationError
from keep_mcp.services.cards import CardService
from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticValidationError, field_validator

TOOL_NAME = "memory.recall"

TagLabel = Annotated[str, Field(min_length=1, max_length=60)]


class RecallRequest(BaseModel):
    """Payload schema for recalling memory cards."""

    model_config = ConfigDict(extra="forbid")

    query: str | None = Field(default=None, max_length=200)
    tags: list[TagLabel] | None = Field(
        default=None,
        max_length=5,
        json_schema_extra={"uniqueItems": True},
    )
    limit: int = Field(default=10, ge=1, le=25)
    includeArchived: bool = Field(default=False)

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if len({tag for tag in value}) != len(value):
            raise ValueError("Tags must be unique")
        return value


_REQUEST_SCHEMA = RecallRequest.model_json_schema()
_REQUEST_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_REQUEST_SCHEMA["title"] = TOOL_NAME
REQUEST_SCHEMA: dict[str, Any] = _REQUEST_SCHEMA

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
        payload = RecallRequest.model_validate(request)
        result = await card_service.recall(
            query=payload.query,
            tags=payload.tags or [],
            limit=payload.limit,
            include_archived=payload.includeArchived,
        )
        if result.get("message") is None:
            result.pop("message", None)
        return result
    except PydanticValidationError as exc:
        raise ValidationError(exc.errors()[0]["msg"] if exc.errors() else str(exc)) from exc
    except ValidationError:
        raise
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - mapped to STORAGE_FAILURE
        raise StorageFailure("Failed to recall memory cards") from exc
