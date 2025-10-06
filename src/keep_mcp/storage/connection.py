from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB_NAME = "cards.db"
DEFAULT_DIR = Path.cwd() / "data"


def resolve_db_path(explicit: Optional[str | Path] = None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    env_path = os.getenv("MCP_MEMORY_DB_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (DEFAULT_DIR / DEFAULT_DB_NAME).resolve()


def create_connection(path: Optional[str | Path] = None) -> sqlite3.Connection:
    db_path = resolve_db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        db_path,
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection
