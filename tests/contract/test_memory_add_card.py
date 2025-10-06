from __future__ import annotations

import json
from pathlib import Path

import pytest

FEATURE_DIR = Path(__file__).resolve().parents[3] / "specs/002-google-keep-mcp"
CONTRACT_PATH = FEATURE_DIR / "contracts/memory.add_card.json"


@pytest.mark.contract
def test_add_card_contract_alignment():
    """Adapters must expose schemas identical to the published contract."""
    import keep_mcp.adapters.tools.add_card as add_card

    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        spec = json.load(handle)

    assert add_card.REQUEST_SCHEMA == {
        key: spec[key]
        for key in ("$schema", "title", "type", "required", "properties", "additionalProperties")
    }
    assert add_card.RESPONSE_SCHEMA == spec["response"]
    assert add_card.ERROR_SCHEMA == spec["error"]
    assert add_card.TOOL_NAME == "memory.add_card"
