from __future__ import annotations

from typing import Any

from keep_mcp.adapters.errors import StorageFailure, ValidationError
from keep_mcp.models import RecallError, RecallRequest, RecallResponse
from keep_mcp.services.card_lifecycle import CardLifecycleService
from pydantic import ValidationError as PydanticValidationError

TOOL_NAME = "memory.recall"

_REQUEST_SCHEMA = RecallRequest.model_json_schema()
_REQUEST_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_REQUEST_SCHEMA["title"] = TOOL_NAME
REQUEST_SCHEMA: dict[str, Any] = _REQUEST_SCHEMA

_RESPONSE_SCHEMA = RecallResponse.model_json_schema()
_RESPONSE_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_RESPONSE_SCHEMA["title"] = f"{TOOL_NAME}.response"
RESPONSE_SCHEMA: dict[str, Any] = _RESPONSE_SCHEMA

_ERROR_SCHEMA = RecallError.model_json_schema()
_ERROR_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_ERROR_SCHEMA["title"] = f"{TOOL_NAME}.error"
ERROR_SCHEMA: dict[str, Any] = _ERROR_SCHEMA


async def execute(card_service: CardLifecycleService, request: dict[str, Any]) -> dict[str, Any]:
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
