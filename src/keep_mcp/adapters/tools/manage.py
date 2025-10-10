from __future__ import annotations

from typing import Any

from keep_mcp.adapters.errors import NotFoundError, StorageFailure, ValidationError
from keep_mcp.models import ManageError, ManagePayload, ManageRequest, ManageResponse
from keep_mcp.services.card_lifecycle import CardLifecycleService
from pydantic import ValidationError as PydanticValidationError

TOOL_NAME = "memory.manage"

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

_RESPONSE_SCHEMA = ManageResponse.model_json_schema()
_RESPONSE_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_RESPONSE_SCHEMA["title"] = f"{TOOL_NAME}.response"
RESPONSE_SCHEMA: dict[str, Any] = _RESPONSE_SCHEMA

_ERROR_SCHEMA = ManageError.model_json_schema()
_ERROR_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_ERROR_SCHEMA["title"] = f"{TOOL_NAME}.error"
ERROR_SCHEMA: dict[str, Any] = _ERROR_SCHEMA


async def execute(card_service: CardLifecycleService, request: dict[str, Any]) -> dict[str, Any]:
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
