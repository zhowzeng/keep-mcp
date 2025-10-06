from __future__ import annotations

from typing import Any, Iterable, List

from keep_mcp.storage.audit_repository import AuditLogRepository
from keep_mcp.storage.models.audit_log_entry import AuditLogEntry
from keep_mcp.utils.time import utc_now_str


class AuditService:
    """High-level helpers for emitting audit log entries."""

    def __init__(self, repository: AuditLogRepository) -> None:
        self._repository = repository

    def add_card(self, card_id: str, payload: dict[str, Any]) -> AuditLogEntry:
        return self._repository.append("ADD_CARD", payload, utc_now_str(), card_id=card_id)

    def update_card(self, card_id: str, payload: dict[str, Any]) -> AuditLogEntry:
        return self._repository.append("UPDATE_CARD", payload, utc_now_str(), card_id=card_id)

    def archive_card(self, card_id: str) -> AuditLogEntry:
        return self._repository.append(
            "UPDATE_CARD", {"status": "ARCHIVED"}, utc_now_str(), card_id=card_id
        )

    def delete_card(self, card_id: str) -> AuditLogEntry:
        return self._repository.append("DELETE", {}, utc_now_str(), card_id=card_id)

    def recall(self, payload: dict[str, Any]) -> AuditLogEntry:
        return self._repository.append("RECALL", payload, utc_now_str(), card_id=None)

    def merge_duplicate(self, canonical_card_id: str, payload: dict[str, Any]) -> AuditLogEntry:
        return self._repository.append("MERGE_DUPLICATE", payload, utc_now_str(), card_id=canonical_card_id)

    def export(self, payload: dict[str, Any]) -> AuditLogEntry:
        return self._repository.append("EXPORT", payload, utc_now_str(), card_id=None)

    def list_recent(self, limit: int = 50) -> List[AuditLogEntry]:
        return self._repository.list_recent(limit)

    def entries_for_card(self, card_id: str) -> Iterable[AuditLogEntry]:
        return self._repository.entries_for_card(card_id)
