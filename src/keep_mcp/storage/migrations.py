from __future__ import annotations

from sqlite3 import Connection
from typing import Any, cast

import sqlite_utils

SCHEMA_VERSION = 1


def apply_migrations(conn: Connection) -> None:
    """Apply idempotent schema migrations for the memory store."""
    conn.execute("PRAGMA foreign_keys = ON")
    db = sqlite_utils.Database(conn)

    with conn:
        _ensure_memory_card_table(db)
        _ensure_memory_card_revision_table(db)
        _ensure_tag_table(db)
        _ensure_memory_card_tag_table(db)
        _ensure_audit_log_table(db)
        _ensure_fts_tables(conn)

    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _ensure_memory_card_table(db: sqlite_utils.Database) -> None:
    if "memory_card" not in db.table_names():
        cast(Any, db["memory_card"]).create(
            {
                "card_id": str,
                "title": str,
                "summary": str,
                "body": str,
                "origin_conversation_id": str,
                "origin_message_excerpt": str,
                "created_at": str,
                "updated_at": str,
                "last_recalled_at": str,
                "recall_count": int,
                "duplicate_of_id": str,
                "archived": int,
            },
            pk="card_id",
            not_null={
                "title",
                "summary",
                "created_at",
                "updated_at",
                "recall_count",
                "archived",
            },
            defaults={"recall_count": 0, "archived": 0},
            foreign_keys=[("duplicate_of_id", "memory_card", "card_id")],
        )
    else:
        table = cast(Any, db["memory_card"])  # typing: sqlite_utils Table
        if "archived" not in table.columns_dict:
            table.add_column("archived", int, not_null=True, default=0)
    cast(Any, db["memory_card"]).create_index(
        ["updated_at"],
        if_not_exists=True,
        index_name="idx_memory_card_updated_at",
    )
    cast(Any, db["memory_card"]).create_index(
        ["recall_count"],
        if_not_exists=True,
        index_name="idx_memory_card_recall_count",
    )


def _ensure_memory_card_revision_table(db: sqlite_utils.Database) -> None:
    if "memory_card_revision" not in db.table_names():
        cast(Any, db["memory_card_revision"]).create(
            {
                "revision_id": str,
                "card_id": str,
                "snapshot_json": str,
                "change_type": str,
                "changed_at": str,
            },
            pk="revision_id",
            not_null={"card_id", "snapshot_json", "change_type", "changed_at"},
            foreign_keys=[("card_id", "memory_card", "card_id")],
        )
    cast(Any, db["memory_card_revision"]).create_index(
        ["card_id", "changed_at"],
        if_not_exists=True,
        index_name="idx_revision_card_changed_at",
    )


def _ensure_tag_table(db: sqlite_utils.Database) -> None:
    if "tag" not in db.table_names():
        cast(Any, db["tag"]).create(
            {
                "tag_id": str,
                "slug": str,
                "label": str,
            },
            pk="tag_id",
            not_null={"slug", "label"},
        )

    cast(Any, db["tag"]).create_index(
        ["slug"],
        unique=True,
        if_not_exists=True,
        index_name="idx_tag_slug_unique",
    )


def _ensure_memory_card_tag_table(db: sqlite_utils.Database) -> None:
    if "memory_card_tag" not in db.table_names():
        cast(Any, db["memory_card_tag"]).create(
            {
                "card_id": str,
                "tag_id": str,
                "added_at": str,
            },
            pk=("card_id", "tag_id"),
            not_null={"card_id", "tag_id", "added_at"},
            foreign_keys=[
                ("card_id", "memory_card", "card_id"),
                ("tag_id", "tag", "tag_id"),
            ],
        )


def _ensure_audit_log_table(db: sqlite_utils.Database) -> None:
    if "audit_log" not in db.table_names():
        cast(Any, db["audit_log"]).create(
            {
                "audit_id": str,
                "card_id": str,
                "action": str,
                "payload_json": str,
                "happened_at": str,
            },
            pk="audit_id",
            not_null={"action", "payload_json", "happened_at"},
            foreign_keys=[("card_id", "memory_card", "card_id")],
        )
    cast(Any, db["audit_log"]).create_index(
        ["card_id", "happened_at"],
        if_not_exists=True,
        index_name="idx_audit_card",
    )


def _ensure_fts_tables(conn: Connection) -> None:
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_card_search USING fts5(
            card_id UNINDEXED,
            title,
            summary,
            body
        )
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_memory_card_ai AFTER INSERT ON memory_card
        BEGIN
            INSERT INTO memory_card_search(rowid, card_id, title, summary, body)
            VALUES (new.rowid, new.card_id, new.title, new.summary, COALESCE(new.body, ''));
        END;
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_memory_card_au AFTER UPDATE ON memory_card
        BEGIN
            UPDATE memory_card_search
            SET title = new.title,
                summary = new.summary,
                body = COALESCE(new.body, '')
            WHERE card_id = new.card_id;
        END;
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_memory_card_ad AFTER DELETE ON memory_card
        BEGIN
            DELETE FROM memory_card_search WHERE card_id = old.card_id;
        END;
        """
    )
