from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AuditLogEntry:
    audit_id: str
    card_id: str | None
    action: str
    payload_json: str
    happened_at: str

    @classmethod
    def from_row(cls, row: dict) -> "AuditLogEntry":
        return cls(
            audit_id=row["audit_id"],
            card_id=row.get("card_id"),
            action=row["action"],
            payload_json=row["payload_json"],
            happened_at=row["happened_at"],
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "audit_id": self.audit_id,
            "card_id": self.card_id,
            "action": self.action,
            "payload_json": self.payload_json,
            "happened_at": self.happened_at,
        }
