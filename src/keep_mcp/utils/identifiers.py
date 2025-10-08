from __future__ import annotations

import ulid


def new_ulid() -> str:
    """Return a sortable ULID string."""
    return str(ulid.new())
