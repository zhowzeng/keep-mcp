from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio


@pytest.fixture(scope="session", autouse=True)
def project_root() -> Path:
    """Ensure src directory is importable during tests."""
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    os.environ.setdefault("MCP_MEMORY_DB_PATH", str(Path.home() / ".mcp-memory" / "cards.db"))
    return root


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for asyncio tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
