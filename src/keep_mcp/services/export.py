from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Iterable

from keep_mcp.services.audit import AuditService
from keep_mcp.storage.models.memory_card import MemoryCard
from keep_mcp.storage.repository import CardRepository
from keep_mcp.storage.revision_repository import RevisionRepository
from keep_mcp.utils.time import utc_now_str


class ExportService:
    """Stream all cards and revisions to an NDJSON export file."""

    def __init__(
        self,
        card_repository: CardRepository,
        revision_repository: RevisionRepository,
        audit_service: AuditService,
    ) -> None:
        self._cards = card_repository
        self._revisions = revision_repository
        self._audit = audit_service

    async def export(self, destination_path: str | Path | None = None) -> dict[str, Any]:
        export_path = self._resolve_path(destination_path)
        payload = await asyncio.to_thread(self._build_payload)
        await asyncio.to_thread(self._write_ndjson, export_path, payload)
        self._audit.export({"filePath": str(export_path), "exportedCount": len(payload)})
        return {"filePath": str(export_path), "exportedCount": len(payload)}

    def _build_payload(self) -> list[dict[str, Any]]:
        cards = self._cards.list_all_cards()
        result: list[dict[str, Any]] = []
        for card in cards:
            result.append(
                {
                    "card": self._serialize_card(card),
                    "revisions": [self._serialize_revision(rev) for rev in self._revisions.list_revisions(card.card_id)],
                }
            )
        return result

    def _write_ndjson(self, path: Path, payload: Iterable[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for entry in payload:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _serialize_card(self, card: MemoryCard) -> dict[str, Any]:
        data = card.to_dict()
        data["archived"] = bool(data["archived"])
        data["tags"] = list(card.tags)
        return data

    def _serialize_revision(self, revision) -> dict[str, Any]:
        mapping = revision.to_dict() if hasattr(revision, "to_dict") else {
            "revision_id": revision.revision_id,
            "card_id": revision.card_id,
            "snapshot_json": revision.snapshot_json,
            "change_type": revision.change_type,
            "changed_at": revision.changed_at,
        }
        try:
            snapshot = json.loads(mapping.pop("snapshot_json"))
        except json.JSONDecodeError:
            snapshot = mapping.pop("snapshot_json")
        mapping["snapshot"] = snapshot
        return mapping

    def _resolve_path(self, destination_path: str | Path | None) -> Path:
        if destination_path is not None:
            return Path(destination_path).expanduser().resolve()
        timestamp = (
            utc_now_str()
            .replace("-", "")
            .replace(":", "")
            .replace("T", "")
            .split(".", 1)[0]
        )
        return Path.home() / f"memory-export-{timestamp}.jsonl"
