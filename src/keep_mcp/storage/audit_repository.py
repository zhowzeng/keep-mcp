from __future__ import annotations

import json
from sqlite3 import Connection
from typing import Any, Iterable

from keep_mcp.identifiers import new_ulid
from keep_mcp.storage.models.audit_log_entry import AuditLogEntry


class AuditLogRepository:
    """Persist transparent audit log entries for memory operations."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def append(self, action: str, payload: dict[str, Any], happened_at: str, card_id: str | None = None) -> AuditLogEntry:
        entry = AuditLogEntry(
            audit_id=new_ulid(),
            card_id=card_id,
            action=action,
            payload_json=json.dumps(payload, ensure_ascii=False),
            happened_at=happened_at,
        )
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO audit_log (audit_id, card_id, action, payload_json, happened_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entry.audit_id,
                    entry.card_id,
                    entry.action,
                    entry.payload_json,
                    entry.happened_at,
                ),
            )
        return entry

    def list_recent(self, limit: int = 50) -> list[AuditLogEntry]:
        rows = self._conn.execute(
            "SELECT * FROM audit_log ORDER BY happened_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [AuditLogEntry.from_row(dict(row)) for row in rows]

    def entries_for_card(self, card_id: str) -> Iterable[AuditLogEntry]:
        rows = self._conn.execute(
            "SELECT * FROM audit_log WHERE card_id = ? ORDER BY happened_at DESC",
            (card_id,),
        ).fetchall()
        for row in rows:
            yield AuditLogEntry.from_row(dict(row))
