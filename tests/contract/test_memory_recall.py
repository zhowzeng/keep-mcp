from __future__ import annotations

import json
from pathlib import Path

import pytest

FEATURE_DIR = Path(__file__).resolve().parents[3] / "specs/002-google-keep-mcp"
CONTRACT_PATH = FEATURE_DIR / "contracts/memory.recall.json"


@pytest.mark.contract
def test_recall_contract_alignment():
    """Recall tool adapter must mirror the published request/response contract."""
    import keep_mcp.adapters.tools.recall as recall

    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        spec = json.load(handle)

    assert recall.REQUEST_SCHEMA == {
        key: spec[key]
        for key in ("$schema", "title", "type", "properties", "additionalProperties")
    }
    assert recall.RESPONSE_SCHEMA == spec["response"]
    assert recall.ERROR_SCHEMA == spec["error"]
    assert recall.TOOL_NAME == "memory.recall"
