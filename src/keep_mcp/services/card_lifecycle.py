from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, Iterable

from keep_mcp.services.audit import AuditService
from keep_mcp.services.duplicate import DuplicateDetectionService
from keep_mcp.services.ranking import RankingService
from keep_mcp.storage.models.memory_card import MemoryCard
from keep_mcp.storage.card_repository import CardRepository
from keep_mcp.storage.revision_repository import RevisionRepository
from keep_mcp.storage.tag_repository import TagRepository
from keep_mcp.utils.identifiers import new_ulid
from keep_mcp.utils.tags import normalize_labels, slugify
from keep_mcp.utils.time import parse_utc, utc_now_str


ALLOWED_NOTE_TYPES = {"FLEETING", "LITERATURE", "PERMANENT", "INDEX"}


class CardLifecycleService:
    """Coordinate memory card lifecycle operations."""

    def __init__(
        self,
        card_repository: CardRepository,
        revision_repository: RevisionRepository,
        tag_repository: TagRepository,
        duplicate_service: DuplicateDetectionService,
        ranking_service: RankingService,
        audit_service: AuditService,
    ) -> None:
        self._cards = card_repository
        self._revisions = revision_repository
        self._tags = tag_repository
        self._duplicates = duplicate_service
        self._ranking = ranking_service
        self._audit = audit_service

    async def add_card(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._validate_payload(payload, require_title=True, require_note_type=True)
        now = utc_now_str()
        candidate_text = f"{data['title']}\n{data['summary']}"

        existing_cards = await asyncio.to_thread(self._cards.list_canonical_cards, False)
        recent_cards = self._filter_recent(existing_cards, hours=24)
        corpus = [(card.card_id, f"{card.title}\n{card.summary}") for card in recent_cards]
        match = self._duplicates.find_duplicate(candidate_text, corpus)

        normalized_tags = normalize_labels(data.get("tags", []))
        incoming_note_type = data["noteType"]
        incoming_source_reference = data.get("sourceReference")
        warnings: list[str] = []
        if match:
            canonical = await asyncio.to_thread(self._cards.get_card, match.card_id)
            if canonical is None:
                return await self._create_new_card(data, normalized_tags, now)
            merged_tags = self._merge_tags(canonical.tags, normalized_tags)
            tag_models = await asyncio.to_thread(self._tags.get_or_create_tags, merged_tags)
            await asyncio.to_thread(self._tags.replace_card_tags, canonical.card_id, tag_models, now)
            canonical.tags = tuple(merged_tags)
            if canonical.note_type != incoming_note_type:
                warnings.append(
                    f"Merged with existing card ({canonical.card_id}) of type {canonical.note_type}; submitted type {incoming_note_type} was not applied."
                )
            fields: dict[str, Any] = {}
            source_forwarded = False
            if incoming_source_reference and not canonical.source_reference:
                source_forwarded = True
                canonical.source_reference = incoming_source_reference
                fields["source_reference"] = incoming_source_reference
            if fields:
                fields["updated_at"] = now
                await asyncio.to_thread(self._cards.update_card, canonical.card_id, fields)
            snapshot = self._build_revision_snapshot(canonical, canonical.tags)
            await asyncio.to_thread(
                self._revisions.add_revision,
                canonical.card_id,
                snapshot,
                "MERGE_DUPLICATE",
                now,
            )
            await asyncio.to_thread(
                self._audit.merge_duplicate,
                canonical.card_id,
                {
                    "score": match.score,
                    "title": data["title"],
                    "summary": data["summary"],
                    "submittedNoteType": incoming_note_type,
                    "canonicalNoteType": canonical.note_type,
                    "sourceReferenceForwarded": source_forwarded,
                },
            )
            response: dict[str, Any] = {
                "cardId": canonical.card_id,
                "createdAt": canonical.created_at,
                "merged": True,
                "canonicalCardId": canonical.card_id,
                "noteType": canonical.note_type,
                "sourceReference": canonical.source_reference,
            }
            if warnings:
                response["warnings"] = warnings
            return response

        return await self._create_new_card(data, normalized_tags, now)

    async def recall(
        self,
        query: str | None,
        tags: Iterable[str],
        limit: int,
        include_archived: bool,
    ) -> dict[str, Any]:
        limit = max(1, min(limit or 10, 25))
        tags_list = list(tags)
        candidates = await asyncio.to_thread(self._cards.list_canonical_cards, include_archived)

        if tags_list:
            tag_slugs = [*{self._slug_from_label(label) for label in tags_list if label.strip()}]
            matching_ids = await asyncio.to_thread(self._tags.find_cards_with_tags, tag_slugs)
            candidates = [card for card in candidates if card.card_id in matching_ids]

        ranked = await asyncio.to_thread(self._ranking.rank, candidates, query)
        top_ranked = ranked[:limit]

        now = utc_now_str()
        response_cards: list[dict[str, Any]] = []
        for ranked_card in top_ranked:
            card = ranked_card.card
            await asyncio.to_thread(self._cards.record_recall, card.card_id, now)
            card.recall_count += 1
            card.last_recalled_at = now
            card.updated_at = now
            response_cards.append(self._serialize_card(card, ranked_card.score))

        if response_cards:
            await asyncio.to_thread(
                self._audit.recall,
                {
                    "query": query,
                    "tags": tags_list,
                    "limit": limit,
                    "returned": len(response_cards),
                },
            )
        message = None
        if not response_cards:
            message = "No memory cards matched your query."

        return {"cards": response_cards, "message": message}

    async def manage_card(
        self,
        card_id: str,
        operation: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        card = await asyncio.to_thread(self._cards.get_card, card_id)
        if card is None:
            raise ValueError("Card not found")

        now = utc_now_str()
        op = operation.upper()
        if op == "UPDATE":
            if payload is None:
                raise ValueError("Update payload is required")
            update = self._validate_payload(payload, require_title=False, require_note_type=False)
            fields: dict[str, Any] = {}
            if "title" in update:
                card.title = update["title"]
                fields["title"] = update["title"]
            if "summary" in update:
                card.summary = update["summary"]
                fields["summary"] = update["summary"]
            if "body" in update:
                card.body = update["body"]
                fields["body"] = update["body"]
            if "noteType" in update:
                card.note_type = update["noteType"]
                fields["note_type"] = update["noteType"]
            if "sourceReference" in update:
                card.source_reference = update["sourceReference"]
                fields["source_reference"] = update["sourceReference"]
            if update.get("tags") is not None:
                normalized = normalize_labels(update["tags"])
                tag_models = await asyncio.to_thread(self._tags.get_or_create_tags, normalized)
                await asyncio.to_thread(self._tags.replace_card_tags, card.card_id, tag_models, now)
                card.tags = tuple(normalized)
            fields["updated_at"] = now
            await asyncio.to_thread(self._cards.update_card, card.card_id, fields)
            snapshot = self._build_revision_snapshot(card, card.tags)
            await asyncio.to_thread(
                self._revisions.add_revision,
                card.card_id,
                snapshot,
                "UPDATE",
                now,
            )
            await asyncio.to_thread(
                self._audit.update_card,
                card.card_id,
                {
                    key: update[key]
                    for key in ("title", "summary", "tags", "noteType", "sourceReference")
                    if key in update
                },
            )
            return {"cardId": card.card_id, "status": "UPDATED", "updatedAt": now}

        if op == "ARCHIVE":
            card.archived = True
            await asyncio.to_thread(self._cards.set_archived, card.card_id, True, now)
            snapshot = self._build_revision_snapshot(card, card.tags)
            await asyncio.to_thread(
                self._revisions.add_revision,
                card.card_id,
                snapshot,
                "UPDATE",
                now,
            )
            await asyncio.to_thread(self._audit.archive_card, card.card_id)
            return {"cardId": card.card_id, "status": "ARCHIVED", "updatedAt": now}

        if op == "DELETE":
            snapshot = self._build_revision_snapshot(card, card.tags)
            await asyncio.to_thread(
                self._revisions.add_revision,
                card.card_id,
                snapshot,
                "DELETE",
                now,
            )
            # Append audit BEFORE deleting the row to satisfy FK constraints.
            await asyncio.to_thread(self._audit.delete_card, card.card_id)
            await asyncio.to_thread(self._cards.delete_card, card.card_id)
            return {"cardId": card.card_id, "status": "DELETED", "updatedAt": now}

        raise ValueError(f"Unsupported operation: {operation}")

    async def _create_new_card(self, data: dict[str, Any], tags: list[str], now: str) -> dict[str, Any]:
        card_id = new_ulid()
        card_record = {
            "card_id": card_id,
            "title": data["title"],
            "summary": data["summary"],
            "body": data.get("body"),
            "note_type": data["noteType"],
            "source_reference": data.get("sourceReference"),
            "origin_conversation_id": data.get("originConversationId"),
            "origin_message_excerpt": data.get("originMessageExcerpt"),
            "created_at": now,
            "updated_at": now,
            "last_recalled_at": None,
            "recall_count": 0,
            "duplicate_of_id": None,
            "archived": 0,
        }
        await asyncio.to_thread(self._cards.insert_card, card_record)
        tag_models = await asyncio.to_thread(self._tags.get_or_create_tags, tags)
        await asyncio.to_thread(self._tags.replace_card_tags, card_id, tag_models, now)
        card = await asyncio.to_thread(self._cards.get_card, card_id)
        if card is None:
            raise RuntimeError("created card not found")
        snapshot = self._build_revision_snapshot(card, card.tags)
        await asyncio.to_thread(self._revisions.add_revision, card_id, snapshot, "CREATE", now)
        await asyncio.to_thread(
            self._audit.add_card,
            card_id,
            {
                "title": data["title"],
                "summary": data["summary"],
                "tags": list(card.tags),
                "noteType": data["noteType"],
                "sourceReference": data.get("sourceReference"),
            },
        )
        response = {
            "cardId": card_id,
            "createdAt": now,
            "merged": False,
            "noteType": data["noteType"],
            "sourceReference": data.get("sourceReference"),
        }
        return response

    def _serialize_card(self, card: MemoryCard, score: float) -> dict[str, Any]:
        return {
            "cardId": card.card_id,
            "title": card.title,
            "summary": card.summary,
            "body": card.body,
            "tags": list(card.tags),
            "noteType": card.note_type,
            "sourceReference": card.source_reference,
            "rankScore": round(score, 6),
            "updatedAt": card.updated_at,
            "lastRecalledAt": card.last_recalled_at,
            "recallCount": card.recall_count,
        }

    def _build_revision_snapshot(self, card: MemoryCard, tags: Iterable[str]) -> dict[str, Any]:
        return {
            "cardId": card.card_id,
            "title": card.title,
            "summary": card.summary,
            "body": card.body,
            "noteType": card.note_type,
            "sourceReference": card.source_reference,
            "tags": list(tags),
            "duplicateOfId": card.duplicate_of_id,
            "archived": card.archived,
        }
    def _validate_payload(
        self,
        payload: dict[str, Any],
        *,
        require_title: bool,
        require_note_type: bool,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        title = payload.get("title")
        summary = payload.get("summary")
        if require_title and (title is None or not title.strip()):
            raise ValueError("title is required")
        if require_title and (summary is None or not summary.strip()):
            raise ValueError("summary is required")
        if title is not None:
            clean = title.strip()
            if not clean:
                raise ValueError("title cannot be empty")
            result["title"] = clean[:120]
        if summary is not None:
            clean_summary = summary.strip()
            if not clean_summary:
                raise ValueError("summary cannot be empty")
            result["summary"] = clean_summary[:500]
        if "body" in payload:
            body_value = payload.get("body")
            if body_value is None:
                result["body"] = None
            else:
                result["body"] = str(body_value).strip()[:4000]
        if "tags" in payload:
            tags = payload.get("tags") or []
            if not isinstance(tags, list):
                raise ValueError("tags must be a list")
            result["tags"] = [str(tag) for tag in tags]
        if "originConversationId" in payload:
            oci = payload.get("originConversationId")
            if oci is not None:
                result["originConversationId"] = str(oci).strip()
            else:
                result["originConversationId"] = None
        if "originMessageExcerpt" in payload:
            excerpt = payload.get("originMessageExcerpt")
            if excerpt is not None:
                result["originMessageExcerpt"] = str(excerpt)[:280]
            else:
                result["originMessageExcerpt"] = None
        if "noteType" in payload:
            note_type = payload.get("noteType")
            if note_type is None:
                if require_note_type:
                    raise ValueError("noteType is required")
            else:
                normalized_note_type = str(note_type).strip().upper()
                if normalized_note_type not in ALLOWED_NOTE_TYPES:
                    allowed = ", ".join(sorted(ALLOWED_NOTE_TYPES))
                    raise ValueError(f"noteType must be one of: {allowed}")
                result["noteType"] = normalized_note_type
        elif require_note_type:
            raise ValueError("noteType is required")
        if "sourceReference" in payload:
            source_reference = payload.get("sourceReference")
            if source_reference is None:
                result["sourceReference"] = None
            else:
                clean_reference = str(source_reference).strip()
                if len(clean_reference) > 2048:
                    clean_reference = clean_reference[:2048]
                result["sourceReference"] = clean_reference or None
        return result

    def _filter_recent(self, cards: Iterable[MemoryCard], hours: int) -> list[MemoryCard]:
        if hours <= 0:
            return list(cards)
        threshold = parse_utc(utc_now_str()) - timedelta(hours=hours)
        recent: list[MemoryCard] = []
        for card in cards:
            try:
                created = parse_utc(card.created_at)
            except ValueError:
                recent.append(card)
                continue
            if created >= threshold:
                recent.append(card)
        return recent

    def _merge_tags(self, existing: Iterable[str], new_tags: Iterable[str]) -> list[str]:
        merged: dict[str, str] = {}
        for label in existing:
            slug = slugify(label)
            merged[slug] = label
        for label in new_tags:
            slug = slugify(label)
            merged.setdefault(slug, label)
        return list(merged.values())[:20]

    def _slug_from_label(self, label: str) -> str:
        return slugify(label)
