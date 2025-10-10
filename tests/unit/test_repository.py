from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from keep_mcp.storage.migrations import apply_migrations
from keep_mcp.storage.card_repository import CardRepository
from keep_mcp.storage.tag_repository import TagRepository

pytestmark = pytest.mark.unit


@pytest.fixture
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    apply_migrations(connection)
    yield connection
    connection.close()


def _iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def test_card_repository_crud_with_tags(conn: sqlite3.Connection) -> None:
    cards = CardRepository(conn)
    tags = TagRepository(conn)

    now = _iso(datetime(2025, 1, 5, tzinfo=timezone.utc))
    card_id = "card-001"

    cards.insert_card(
        {
            "card_id": card_id,
            "title": "Async gather patterns",
            "summary": "Use asyncio.gather for concurrency fan out",
            "body": None,
            "note_type": "PERMANENT",
            "source_reference": None,
            "origin_conversation_id": None,
            "origin_message_excerpt": None,
            "created_at": now,
            "updated_at": now,
            "last_recalled_at": None,
            "recall_count": 0,
            "duplicate_of_id": None,
            "archived": 0,
        }
    )

    tag_models = tags.get_or_create_tags(["python", "async"])  # ensures dedupe + slug creation
    tags.replace_card_tags(card_id, tag_models, now)

    card = cards.get_card(card_id)
    assert card is not None
    assert card.title == "Async gather patterns"
    assert card.tags == ("async", "python")
    assert card.note_type == "PERMANENT"
    assert card.source_reference is None

    cards.update_card(card_id, {"summary": "Updated summary", "body": "Body"})
    cards.record_recall(card_id, now)
    card_after_update = cards.get_card(card_id)
    assert card_after_update is not None
    assert card_after_update.summary == "Updated summary"
    assert card_after_update.body == "Body"
    assert card_after_update.recall_count == 1
    assert card_after_update.last_recalled_at == now

    active_cards = cards.list_canonical_cards(include_archived=False)
    assert [item.card_id for item in active_cards] == [card_id]

    cards.set_archived(card_id, True, now)
    archived_only = cards.list_canonical_cards(include_archived=False)
    assert archived_only == []
    archived_included = cards.list_canonical_cards(include_archived=True)
    assert [item.card_id for item in archived_included] == [card_id]

    tags_list = tags.list_card_tags(card_id)
    assert tags_list == ["async", "python"]

    cards.delete_card(card_id)
    assert cards.get_card(card_id) is None
    assert tags.list_card_tags(card_id) == []


def test_duplicate_cards_filtered_from_canonical_lists(conn: sqlite3.Connection) -> None:
    cards = CardRepository(conn)
    tags = TagRepository(conn)

    now = _iso(datetime(2025, 2, 10, tzinfo=timezone.utc))
    primary_id = "card-primary"
    duplicate_id = "card-duplicate"

    cards.insert_card(
        {
            "card_id": primary_id,
            "title": "Primary entry",
            "summary": "Original memory card",
            "body": None,
            "note_type": "PERMANENT",
            "source_reference": None,
            "origin_conversation_id": None,
            "origin_message_excerpt": None,
            "created_at": now,
            "updated_at": now,
            "last_recalled_at": None,
            "recall_count": 0,
            "duplicate_of_id": None,
            "archived": 0,
        }
    )
    cards.insert_card(
        {
            "card_id": duplicate_id,
            "title": "Secondary entry",
            "summary": "Similar to original",
            "body": None,
            "note_type": "PERMANENT",
            "source_reference": None,
            "origin_conversation_id": None,
            "origin_message_excerpt": None,
            "created_at": now,
            "updated_at": now,
            "last_recalled_at": None,
            "recall_count": 0,
            "duplicate_of_id": None,
            "archived": 0,
        }
    )

    tag_models = tags.get_or_create_tags(["python"])
    tags.replace_card_tags(primary_id, tag_models, now)
    tags.replace_card_tags(duplicate_id, tag_models, now)

    cards.set_duplicate(duplicate_id, primary_id)

    canonical = cards.list_canonical_cards(include_archived=False)
    assert [item.card_id for item in canonical] == [primary_id]

    duplicate_card = cards.get_card(duplicate_id)
    assert duplicate_card is not None
    assert duplicate_card.duplicate_of_id == primary_id

    fetched = cards.list_cards_by_ids([primary_id, duplicate_id])
    fetched_ids = {card.card_id for card in fetched}
    assert fetched_ids == {primary_id, duplicate_id}

    tag_matches = tags.find_cards_with_tags(["python"])
    assert tag_matches == {primary_id, duplicate_id}
