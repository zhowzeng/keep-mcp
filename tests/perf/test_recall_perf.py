from __future__ import annotations

import math
import time

import pytest

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

pytestmark = pytest.mark.perf


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(pct * len(ordered)))
    return ordered[rank - 1]


@pytest.mark.asyncio
async def test_recall_and_write_latency(tmp_path) -> None:
    db_path = tmp_path / "perf_cards.db"
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

    write_latencies: list[float] = []
    for index in range(20):
        payload = {
            "title": f"Async pattern {index}",
            "summary": "Use asyncio.gather for concurrency fan out",
            "tags": ["python", "async"],
        }
        start = time.perf_counter()
        await card_service.add_card(payload)
        write_latencies.append(time.perf_counter() - start)

    recall_latencies: list[float] = []
    for _ in range(10):
        start = time.perf_counter()
        result = await card_service.recall(
            query="async concurrency", tags=[], limit=10, include_archived=False
        )
        recall_latencies.append(time.perf_counter() - start)
        assert result["cards"]  # ensure recall returns data

    write_p95 = _percentile(write_latencies, 0.95)
    recall_p95 = _percentile(recall_latencies, 0.95)

    assert write_p95 <= 0.08, f"write p95 exceeded 80ms: {write_p95:.4f}s"
    assert recall_p95 <= 0.2, f"recall p95 exceeded 200ms: {recall_p95:.4f}s"
