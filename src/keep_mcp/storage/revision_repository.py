from __future__ import annotations

import json
from sqlite3 import Connection
from typing import Any, Iterable, List

from keep_mcp.identifiers import new_ulid
from keep_mcp.storage.models.memory_card_revision import MemoryCardRevision


class RevisionRepository:
    """Capture immutable revision snapshots for memory cards."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def add_revision(self, card_id: str, snapshot: dict[str, Any], change_type: str, changed_at: str) -> MemoryCardRevision:
        revision = MemoryCardRevision(
            revision_id=new_ulid(),
            card_id=card_id,
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            change_type=change_type,
            changed_at=changed_at,
        )
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO memory_card_revision
                (revision_id, card_id, snapshot_json, change_type, changed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    revision.revision_id,
                    revision.card_id,
                    revision.snapshot_json,
                    revision.change_type,
                    revision.changed_at,
                ),
            )
        return revision

    def list_revisions(self, card_id: str) -> List[MemoryCardRevision]:
        rows = self._conn.execute(
            "SELECT * FROM memory_card_revision WHERE card_id = ? ORDER BY changed_at DESC",
            (card_id,),
        ).fetchall()
        return [MemoryCardRevision.from_row(dict(row)) for row in rows]

    def delete_revisions(self, card_id: str) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM memory_card_revision WHERE card_id = ?",
                (card_id,),
            )

    def fetch_all(self) -> Iterable[MemoryCardRevision]:
        rows = self._conn.execute("SELECT * FROM memory_card_revision").fetchall()
        for row in rows:
            yield MemoryCardRevision.from_row(dict(row))
