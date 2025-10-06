from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MemoryCardRevision:
    revision_id: str
    card_id: str
    snapshot_json: str
    change_type: str
    changed_at: str

    @classmethod
    def from_row(cls, row: dict) -> "MemoryCardRevision":
        return cls(
            revision_id=row["revision_id"],
            card_id=row["card_id"],
            snapshot_json=row["snapshot_json"],
            change_type=row["change_type"],
            changed_at=row["changed_at"],
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "revision_id": self.revision_id,
            "card_id": self.card_id,
            "snapshot_json": self.snapshot_json,
            "change_type": self.change_type,
            "changed_at": self.changed_at,
        }
