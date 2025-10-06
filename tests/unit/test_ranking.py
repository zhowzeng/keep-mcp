from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from keep_mcp.services.ranking import RankingService
from keep_mcp.storage.models.memory_card import MemoryCard

pytestmark = pytest.mark.unit


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _card(
    card_id: str,
    *,
    title: str,
    summary: str,
    updated_at: str,
    created_at: str,
    recall_count: int,
    body: str | None = None,
) -> MemoryCard:
    return MemoryCard(
        card_id=card_id,
        title=title,
        summary=summary,
        body=body,
        origin_conversation_id=None,
        origin_message_excerpt=None,
        created_at=created_at,
        updated_at=updated_at,
        last_recalled_at=None,
        recall_count=recall_count,
        duplicate_of_id=None,
        archived=False,
        tags=(),
    )


def test_rank_prioritizes_semantic_match(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    now_str = _iso(now)
    monkeypatch.setattr("keep_mcp.services.ranking.utc_now_str", lambda: now_str)

    ranking = RankingService()

    cards = [
        _card(
            "match",
            title="Async gather patterns",
            summary="Use asyncio.gather for concurrency fan out",
            body="Practical patterns for async IO",
            created_at=now_str,
            updated_at=now_str,
            recall_count=1,
        ),
        _card(
            "off_topic",
            title="Soil composition notes",
            summary="Loamy soil retains moisture",
            body="Garden rotations and soil testing guidance",
            created_at=now_str,
            updated_at=now_str,
            recall_count=1,
        ),
    ]

    ranked = ranking.rank(cards, query="async concurrency guidance")

    assert [item.card.card_id for item in ranked] == ["match", "off_topic"]
    assert ranked[0].score > ranked[1].score


def test_rank_combines_recency_and_penalty(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2025, 2, 1, tzinfo=timezone.utc)
    now_str = _iso(now)
    monkeypatch.setattr("keep_mcp.services.ranking.utc_now_str", lambda: now_str)

    ranking = RankingService()
    older = _iso(now - timedelta(days=21))

    cards = [
        _card(
            "recent_low_recall",
            title="Concurrency orchestration",
            summary="Compare async gather with task groups",
            created_at=now_str,
            updated_at=now_str,
            recall_count=2,
        ),
        _card(
            "recent_high_recall",
            title="Concurrency orchestration",
            summary="Compare async gather with task groups",
            created_at=now_str,
            updated_at=now_str,
            recall_count=20,
        ),
        _card(
            "older_low_recall",
            title="Concurrency orchestration",
            summary="Compare async gather with task groups",
            created_at=older,
            updated_at=older,
            recall_count=2,
        ),
    ]

    ranked = ranking.rank(cards, query=None)

    ordered_ids = [item.card.card_id for item in ranked]
    assert ordered_ids == ["recent_low_recall", "recent_high_recall", "older_low_recall"]
    assert ranked[0].score > ranked[1].score > ranked[2].score
