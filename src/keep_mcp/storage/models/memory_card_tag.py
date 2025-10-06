from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MemoryCardTag:
    card_id: str
    tag_id: str
    added_at: str

    @classmethod
    def from_row(cls, row: dict) -> "MemoryCardTag":
        return cls(card_id=row["card_id"], tag_id=row["tag_id"], added_at=row["added_at"])

    def to_dict(self) -> dict[str, str]:
        return {"card_id": self.card_id, "tag_id": self.tag_id, "added_at": self.added_at}
