from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manage_card_update_archive_delete(tmp_path):
    """Manage handler should update, archive, and delete cards with audit trace."""
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

    created = await card_service.add_card(
        {
            "title": "MCP memory hygiene",
            "summary": "Keep audit log clean and archive stale cards weekly.",
            "tags": ["hygiene", "process"],
            "noteType": "PERMANENT",
        }
    )

    card_id = created["cardId"]

    updated = await card_service.manage_card(
        card_id=card_id,
        operation="UPDATE",
        payload={
            "summary": "Keep audit log concise; archive stale cards each Friday.",
            "tags": ["hygiene", "ops"],
            "noteType": "FLEETING",
        },
    )
    assert updated["status"] == "UPDATED"

    recall_after_update = await card_service.recall(query="audit log", tags=[], limit=5, include_archived=False)
    assert recall_after_update["cards"][0]["summary"].startswith("Keep audit log concise")
    assert recall_after_update["cards"][0]["noteType"] == "FLEETING"

    archived = await card_service.manage_card(card_id=card_id, operation="ARCHIVE", payload=None)
    assert archived["status"] == "ARCHIVED"

    recall_without_archived = await card_service.recall(query=None, tags=[], limit=5, include_archived=False)
    assert recall_without_archived["cards"] == []

    recall_with_archived = await card_service.recall(query=None, tags=[], limit=5, include_archived=True)
    assert recall_with_archived["cards"][0]["cardId"] == card_id

    deleted = await card_service.manage_card(card_id=card_id, operation="DELETE", payload=None)
    assert deleted["status"] == "DELETED"

    recall_after_delete = await card_service.recall(query=None, tags=[], limit=5, include_archived=True)
    assert recall_after_delete["cards"] == []
