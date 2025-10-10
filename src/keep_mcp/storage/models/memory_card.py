from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class MemoryCard:
    card_id: str
    title: str
    summary: str
    body: Optional[str]
    note_type: str
    source_reference: Optional[str]
    origin_conversation_id: Optional[str]
    origin_message_excerpt: Optional[str]
    created_at: str
    updated_at: str
    last_recalled_at: Optional[str]
    recall_count: int
    duplicate_of_id: Optional[str]
    archived: bool
    tags: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_row(cls, row: dict) -> "MemoryCard":
        return cls(
            card_id=row["card_id"],
            title=row["title"],
            summary=row["summary"],
            body=row.get("body"),
            note_type=(row.get("note_type") or "PERMANENT").upper(),
            source_reference=row.get("source_reference"),
            origin_conversation_id=row.get("origin_conversation_id"),
            origin_message_excerpt=row.get("origin_message_excerpt"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_recalled_at=row.get("last_recalled_at"),
            recall_count=row.get("recall_count", 0),
            duplicate_of_id=row.get("duplicate_of_id"),
            archived=bool(row.get("archived", 0)),
            tags=tuple(row.get("tags", ()) or ()),
        )

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "card_id": self.card_id,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "note_type": self.note_type,
            "source_reference": self.source_reference,
            "origin_conversation_id": self.origin_conversation_id,
            "origin_message_excerpt": self.origin_message_excerpt,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_recalled_at": self.last_recalled_at,
            "recall_count": self.recall_count,
            "duplicate_of_id": self.duplicate_of_id,
            "archived": 1 if self.archived else 0,
        }
        if self.tags:
            data["tags"] = list(self.tags)
        return data
