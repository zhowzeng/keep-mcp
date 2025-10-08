from __future__ import annotations

import re
from typing import Iterable

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def slugify(label: str) -> str:
    """Normalize label to lowercase slug comprised of a-z0-9 and dashes."""
    base = _SLUG_PATTERN.sub("-", label.strip().lower()).strip("-")
    return base or "tag"


def normalize_labels(labels: Iterable[str], limit: int = 20) -> list[str]:
    """Return trimmed, de-duplicated labels up to the provided limit."""
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
        if len(result) == limit:
            break
    return result
