from __future__ import annotations

from typing import Any

from keep_mcp.adapters.errors import StorageFailure, ValidationError
from keep_mcp.models import AddCardError, AddCardRequest, AddCardResponse
from keep_mcp.services.card_lifecycle import CardLifecycleService
from pydantic import ValidationError as PydanticValidationError

TOOL_NAME = "memory.add_card"

_REQUEST_SCHEMA = AddCardRequest.model_json_schema()
_REQUEST_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_REQUEST_SCHEMA["title"] = TOOL_NAME
REQUEST_SCHEMA: dict[str, Any] = _REQUEST_SCHEMA

_RESPONSE_SCHEMA = AddCardResponse.model_json_schema()
_RESPONSE_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_RESPONSE_SCHEMA["title"] = f"{TOOL_NAME}.response"
RESPONSE_SCHEMA: dict[str, Any] = _RESPONSE_SCHEMA

_ERROR_SCHEMA = AddCardError.model_json_schema()
_ERROR_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_ERROR_SCHEMA["title"] = f"{TOOL_NAME}.error"
ERROR_SCHEMA: dict[str, Any] = _ERROR_SCHEMA


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
