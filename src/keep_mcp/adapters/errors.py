from __future__ import annotations


class AdapterError(Exception):
    """Base error raised by tool adapters to surface contract-aligned codes."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class ValidationError(AdapterError):
    def __init__(self, message: str) -> None:
        super().__init__("VALIDATION_ERROR", message)


class NotFoundError(AdapterError):
    def __init__(self, message: str) -> None:
        super().__init__("NOT_FOUND", message)


class StorageFailure(AdapterError):
    def __init__(self, message: str) -> None:
        super().__init__("STORAGE_FAILURE", message)


class ExportFailed(AdapterError):
    def __init__(self, message: str) -> None:
        super().__init__("EXPORT_FAILED", message)
