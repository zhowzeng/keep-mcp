from __future__ import annotations

from typing import Any, Annotated

from keep_mcp.adapters.errors import StorageFailure, ValidationError
from keep_mcp.services.card_lifecycle import CardLifecycleService
from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticValidationError, field_validator


TagLabel = Annotated[str, Field(min_length=1, max_length=60)]


class AddCardRequest(BaseModel):
    """Payload schema for creating a new memory card."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=500)
    body: str | None = Field(default=None, max_length=4000)
    tags: list[TagLabel] | None = Field(default=None, max_length=20)
    originConversationId: str | None = None
    originMessageExcerpt: str | None = Field(default=None, max_length=280)

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if any(not tag for tag in value):
            raise ValueError("Tags must not be empty")
        if any(len(tag) > 60 for tag in value):
            raise ValueError("Tags must be 60 characters or fewer")
        if len({tag for tag in value}) != len(value):
            raise ValueError("Tags must be unique")
        return value

TOOL_NAME = "memory.add_card"

_REQUEST_SCHEMA = AddCardRequest.model_json_schema()
_REQUEST_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_REQUEST_SCHEMA["title"] = TOOL_NAME
REQUEST_SCHEMA: dict[str, Any] = _REQUEST_SCHEMA

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


async def execute(card_service: CardLifecycleService, request: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = AddCardRequest.model_validate(request)
        return await card_service.add_card(payload.model_dump(exclude_none=True))
    except PydanticValidationError as exc:
        raise ValidationError(exc.errors()[0]["msg"] if exc.errors() else str(exc)) from exc
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - mapped to STORAGE_FAILURE
        raise StorageFailure("Failed to store memory card") from exc
