from __future__ import annotations

from sqlite3 import Connection
from typing import Any, Iterable

from keep_mcp.storage.models.memory_card import MemoryCard


class CardRepository:
    """Persist and query memory cards from SQLite."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def insert_card(self, data: dict[str, Any]) -> None:
        columns = (
            "card_id",
            "title",
            "summary",
            "body",
            "origin_conversation_id",
            "origin_message_excerpt",
            "created_at",
            "updated_at",
            "last_recalled_at",
            "recall_count",
            "duplicate_of_id",
            "archived",
        )
        with self._conn:
            self._conn.execute(
                f"""
                INSERT INTO memory_card ({', '.join(columns)})
                VALUES ({', '.join('?' for _ in columns)})
                """,
                tuple(data.get(column) for column in columns),
            )

    def update_card(self, card_id: str, fields: dict[str, Any]) -> None:
        if not fields:
            return
        assignments = ", ".join(f"{column} = ?" for column in fields)
        params = list(fields.values()) + [card_id]
        with self._conn:
            self._conn.execute(
                f"UPDATE memory_card SET {assignments} WHERE card_id = ?",
                params,
            )

    def set_duplicate(self, card_id: str, canonical_card_id: str) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE memory_card SET duplicate_of_id = ? WHERE card_id = ?",
                (canonical_card_id, card_id),
            )

    def set_archived(self, card_id: str, archived: bool, updated_at: str) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE memory_card SET archived = ?, updated_at = ? WHERE card_id = ?",
                (1 if archived else 0, updated_at, card_id),
            )

    def delete_card(self, card_id: str) -> None:
        with self._conn:
            # Clear dependent rows to satisfy FK constraints
            self._conn.execute("DELETE FROM memory_card_revision WHERE card_id = ?", (card_id,))
            self._conn.execute("DELETE FROM audit_log WHERE card_id = ?", (card_id,))
            self._conn.execute("DELETE FROM memory_card_tag WHERE card_id = ?", (card_id,))
            self._conn.execute("DELETE FROM memory_card WHERE card_id = ?", (card_id,))

    def record_recall(self, card_id: str, recalled_at: str) -> None:
        with self._conn:
            self._conn.execute(
                """
                UPDATE memory_card
                SET recall_count = recall_count + 1,
                    last_recalled_at = ?,
                    updated_at = ?
                WHERE card_id = ?
                """,
                (recalled_at, recalled_at, card_id),
            )

    def get_card(self, card_id: str) -> MemoryCard | None:
        row = self._conn.execute(
            "SELECT * FROM memory_card WHERE card_id = ?",
            (card_id,),
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["tags"] = tuple(self._fetch_tags(card_id))
        return MemoryCard.from_row(data)

    def list_canonical_cards(self, include_archived: bool) -> list[MemoryCard]:
        query = "SELECT * FROM memory_card WHERE duplicate_of_id IS NULL"
        params: list[Any] = []
        if not include_archived:
            query += " AND archived = 0"
        rows = self._conn.execute(query, params).fetchall()
        cards = []
        for row in rows:
            data = dict(row)
            data["tags"] = tuple(self._fetch_tags(data["card_id"]))
            cards.append(MemoryCard.from_row(data))
        return cards

    def list_cards_by_ids(self, card_ids: Iterable[str]) -> list[MemoryCard]:
        ids = list(card_ids)
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"SELECT * FROM memory_card WHERE card_id IN ({placeholders})",
            tuple(ids),
        ).fetchall()
        cards = []
        for row in rows:
            data = dict(row)
            data["tags"] = tuple(self._fetch_tags(data["card_id"]))
            cards.append(MemoryCard.from_row(data))
        return cards

    def list_all_cards(self) -> list[MemoryCard]:
        rows = self._conn.execute("SELECT * FROM memory_card").fetchall()
        cards: list[MemoryCard] = []
        for row in rows:
            data = dict(row)
            data["tags"] = tuple(self._fetch_tags(data["card_id"]))
            cards.append(MemoryCard.from_row(data))
        return cards

    def _fetch_tags(self, card_id: str) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT t.label
            FROM tag t
            INNER JOIN memory_card_tag mct ON mct.tag_id = t.tag_id
            WHERE mct.card_id = ?
            ORDER BY t.label
            """,
            (card_id,),
        ).fetchall()
        return [dict(row)["label"] for row in rows]
