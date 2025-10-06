from __future__ import annotations

import ulid


def new_ulid() -> str:
    """Return a sortable ULID string."""
    # ulid-py exposes a factory: ulid.new() -> ULID object
    return str(ulid.new())
