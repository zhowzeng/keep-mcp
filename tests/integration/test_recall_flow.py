from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ranked_recall_flow(tmp_path):
    """Recall should return ranked cards sorted by score and enriched metadata."""
    from keep_mcp.services.audit import AuditService
    from keep_mcp.services.cards import CardService
    from keep_mcp.services.duplicate import DuplicateDetectionService
    from keep_mcp.services.ranking import RankingService
    from keep_mcp.storage.audit_repository import AuditLogRepository
    from keep_mcp.storage.connection import create_connection
    from keep_mcp.storage.migrations import apply_migrations
    from keep_mcp.storage.repository import CardRepository
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

    card_service = CardService(
        card_repository=card_repo,
        revision_repository=revision_repo,
        tag_repository=tag_repo,
        duplicate_service=duplicate_service,
        ranking_service=ranking_service,
        audit_service=audit_service,
    )

    await card_service.add_card(
        {
            "title": "Async Python gather tips",
            "summary": "Use asyncio.gather to fan out IO-bound work.",
            "tags": ["python", "asyncio"],
        }
    )
    await card_service.add_card(
        {
            "title": "Task orchestration patterns",
            "summary": "Compare async gather with task groups for concurrency management.",
            "tags": ["python", "concurrency"],
        }
    )

    results = await card_service.recall(
        query="async python gather",
        tags=["python"],
        limit=5,
        include_archived=False,
    )

    cards = results["cards"]
    assert len(cards) == 2
    scores = [card["rankScore"] for card in cards]
    assert scores == sorted(scores, reverse=True)
    for card in cards:
        assert {"cardId", "title", "summary", "rankScore", "updatedAt", "recallCount"}.issubset(card)
        assert card["recallCount"] >= 0
