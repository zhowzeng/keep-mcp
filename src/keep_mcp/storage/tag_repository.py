from __future__ import annotations

from sqlite3 import Connection
from typing import Iterable, Sequence

from keep_mcp.identifiers import new_ulid
from keep_mcp.storage.models.tag import Tag, slugify


class TagRepository:
    """Manage tag records and card/tag associations."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def normalize_labels(self, labels: Sequence[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for label in labels:
            clean = label.strip()
            if not clean:
                continue
            slug = slugify(clean)
            if slug in seen:
                continue
            seen.add(slug)
            result.append(clean)
            if len(result) == 20:
                break
        return result

    def get_or_create_tags(self, labels: Sequence[str]) -> list[Tag]:
        normalized = self.normalize_labels(labels)
        if not normalized:
            return []

        tags: list[Tag] = []
        with self._conn:
            for label in normalized:
                slug = slugify(label)
                row = self._conn.execute(
                    "SELECT tag_id, slug, label FROM tag WHERE slug = ?",
                    (slug,),
                ).fetchone()
                if row is None:
                    tag = Tag.from_label(new_ulid(), label)
                    self._conn.execute(
                        "INSERT INTO tag (tag_id, slug, label) VALUES (?, ?, ?)",
                        (tag.tag_id, tag.slug, tag.label),
                    )
                else:
                    data = dict(row)
                    tag = Tag.from_row(data)
                    if data["label"] != label:
                        self._conn.execute(
                            "UPDATE tag SET label = ? WHERE tag_id = ?",
                            (label, tag.tag_id),
                        )
                        tag = Tag(tag_id=tag.tag_id, slug=tag.slug, label=label)
                tags.append(tag)
        return tags

    def replace_card_tags(self, card_id: str, tags: Sequence[Tag], added_at: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM memory_card_tag WHERE card_id = ?", (card_id,))
            for tag in tags:
                self._conn.execute(
                    "INSERT INTO memory_card_tag (card_id, tag_id, added_at) VALUES (?, ?, ?)",
                    (card_id, tag.tag_id, added_at),
                )

    def list_card_tags(self, card_id: str) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT t.label
            FROM tag t
            INNER JOIN memory_card_tag mct ON mct.tag_id = t.tag_id
            WHERE mct.card_id = ?
            ORDER BY t.label
            """,
            (card_id,),
        ).fetchall()
        return [dict(row)["label"] for row in rows]

    def find_cards_with_tags(self, slugs: Iterable[str]) -> set[str]:
        slug_list = [slug for slug in slugs if slug]
        if not slug_list:
            return set()
        placeholders = ",".join("?" for _ in slug_list)
        rows = self._conn.execute(
            f"""
            SELECT mct.card_id
            FROM tag t
            INNER JOIN memory_card_tag mct ON mct.tag_id = t.tag_id
            WHERE t.slug IN ({placeholders})
            GROUP BY mct.card_id
            HAVING COUNT(DISTINCT t.slug) = ?
            """,
            (*slug_list, len(slug_list)),
        ).fetchall()
        return {dict(row)["card_id"] for row in rows}
