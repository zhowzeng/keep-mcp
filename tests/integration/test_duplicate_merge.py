from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_detection_merges_recent_cards(tmp_path):
    """Cards with high semantic overlap within threshold should merge into a canonical card."""
    from keep_mcp.services.audit import AuditService
    from keep_mcp.services.card_lifecycle import CardLifecycleService
    from keep_mcp.services.duplicate import DuplicateDetectionService
    from keep_mcp.services.ranking import RankingService
    from keep_mcp.storage.audit_repository import AuditLogRepository
    from keep_mcp.storage.connection import create_connection
    from keep_mcp.storage.migrations import apply_migrations
    from keep_mcp.storage.card_repository import CardRepository
    from keep_mcp.storage.revision_repository import RevisionRepository
    from keep_mcp.storage.tag_repository import TagRepository

    db_path = tmp_path / "cards.db"
    conn = create_connection(db_path)
    apply_migrations(conn)

    card_repo = CardRepository(conn)
    revision_repo = RevisionRepository(conn)
    tag_repo = TagRepository(conn)
    audit_repo = AuditLogRepository(conn)

    duplicate_service = DuplicateDetectionService(threshold=0.85)
    ranking_service = RankingService()
    audit_service = AuditService(audit_repo)

    card_service = CardLifecycleService(
        card_repository=card_repo,
        revision_repository=revision_repo,
        tag_repository=tag_repo,
        duplicate_service=duplicate_service,
        ranking_service=ranking_service,
        audit_service=audit_service,
    )

    canonical = await card_service.add_card(
        {
            "title": "Configure async HTTP clients",
            "summary": "Capture the checklist for aiohttp session reuse and retries.",
            "tags": ["python", "http"],
        }
    )
    duplicate = await card_service.add_card(
        {
            "title": "Async HTTP checklist",
            "summary": "Remember aiohttp session reuse, retries, and timeout defaults.",
            "tags": ["python", "http"],
        }
    )

    assert duplicate["merged"] is True
    assert duplicate["canonicalCardId"] == canonical["cardId"]

    recall = await card_service.recall(query="aiohttp session reuse", tags=[], limit=5, include_archived=False)
    cards = recall["cards"]
    assert len(cards) == 1
    assert cards[0]["cardId"] == canonical["cardId"]
