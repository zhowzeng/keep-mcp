from __future__ import annotations

from datetime import datetime, timezone

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime(ISO_FORMAT)


def parse_utc(timestamp: str) -> datetime:
    try:
        return datetime.strptime(timestamp, ISO_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp format: {timestamp}") from exc
