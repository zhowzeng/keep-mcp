from __future__ import annotations

from dataclasses import dataclass

from keep_mcp.utils.tags import slugify


@dataclass(slots=True)
class Tag:
    tag_id: str
    slug: str
    label: str

    @classmethod
    def from_label(cls, tag_id: str, label: str) -> "Tag":
        return cls(tag_id=tag_id, slug=slugify(label), label=label)

    @classmethod
    def from_row(cls, row: dict) -> "Tag":
        return cls(tag_id=row["tag_id"], slug=row["slug"], label=row["label"])

    def to_dict(self) -> dict[str, str]:
        return {"tag_id": self.tag_id, "slug": self.slug, "label": self.label}
