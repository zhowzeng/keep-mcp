from __future__ import annotations

from typing import Any, Annotated, Literal

from keep_mcp.adapters.errors import NotFoundError, StorageFailure, ValidationError
from keep_mcp.services.cards import CardService
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError as PydanticValidationError,
    field_validator,
    model_validator,
)

TOOL_NAME = "memory.manage"

TagLabel = Annotated[str, Field(min_length=1, max_length=60)]


class ManagePayload(BaseModel):
    """Payload for update operations."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=120)
    summary: str | None = Field(default=None, max_length=500)
    body: str | None = Field(default=None, max_length=4000)
    tags: list[TagLabel] | None = Field(
        default=None,
        max_length=20,
        json_schema_extra={"uniqueItems": True},
    )

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if len({tag for tag in value}) != len(value):
            raise ValueError("Tags must be unique")
        return value


class ManageRequest(BaseModel):
    """Request schema for managing cards."""

    model_config = ConfigDict(extra="forbid")

    cardId: str = Field(min_length=1)
    operation: Literal["UPDATE", "ARCHIVE", "DELETE"]
    payload: ManagePayload | None = None

    @model_validator(mode="after")
    def _require_payload_for_update(self) -> "ManageRequest":
        if self.operation == "UPDATE" and self.payload is None:
            raise ValueError("payload is required when operation is UPDATE")
        return self


_REQUEST_SCHEMA = ManageRequest.model_json_schema()
_REQUEST_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_REQUEST_SCHEMA["title"] = TOOL_NAME
_REQUEST_SCHEMA.setdefault("allOf", []).append(
    {
        "if": {"properties": {"operation": {"const": "UPDATE"}}},
        "then": {"required": ["payload"]},
    }
)
REQUEST_SCHEMA: dict[str, Any] = _REQUEST_SCHEMA

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
        payload = ManageRequest.model_validate(request)
        update_payload = (
            payload.payload.model_dump(exclude_none=True) if payload.payload else None
        )
        return await card_service.manage_card(payload.cardId, payload.operation, update_payload)
    except PydanticValidationError as exc:
        raise ValidationError(exc.errors()[0]["msg"] if exc.errors() else str(exc)) from exc
    except ValidationError:
        raise
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise NotFoundError(message) from exc
        raise ValidationError(message) from exc
    except Exception as exc:  # pragma: no cover - mapped to STORAGE_FAILURE
        raise StorageFailure("Failed to manage memory card") from exc
