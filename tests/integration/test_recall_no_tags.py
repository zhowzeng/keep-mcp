from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recall_without_tags(tmp_path):
    """Recall should work when tags parameter is not provided or is empty."""
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

    # Add test cards
    await card_service.add_card(
        {
            "title": "Python async tips",
            "summary": "Use asyncio.gather for concurrent operations.",
            "tags": ["python", "async"],
            "noteType": "PERMANENT",
        }
    )
    await card_service.add_card(
        {
            "title": "Docker best practices",
            "summary": "Use multi-stage builds to reduce image size.",
            "tags": ["docker"],
            "noteType": "LITERATURE",
        }
    )
    await card_service.add_card(
        {
            "title": "Git workflow",
            "summary": "Use feature branches and pull requests for code review.",
            "noteType": "PERMANENT",
        }
    )

    # Test with empty tags list
    results = await card_service.recall(
        query="async",
        tags=[],
        limit=10,
        include_archived=False,
    )

    cards = results["cards"]
    assert len(cards) >= 1
    assert any("async" in card["title"].lower() or "async" in card["summary"].lower() for card in cards)

    # Test with query but no tags parameter at all (empty list)
    results2 = await card_service.recall(
        query="docker",
        tags=[],
        limit=10,
        include_archived=False,
    )

    cards2 = results2["cards"]
    assert len(cards2) >= 1
    assert any("docker" in card["title"].lower() or "docker" in card["summary"].lower() for card in cards2)

    # Test without query and without tags - should return all cards
    results3 = await card_service.recall(
        query=None,
        tags=[],
        limit=10,
        include_archived=False,
    )

    cards3 = results3["cards"]
    assert len(cards3) == 3  # All three cards should be returned
