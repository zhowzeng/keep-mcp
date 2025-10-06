from __future__ import annotations

import json
from pathlib import Path

import pytest

FEATURE_DIR = Path(__file__).resolve().parents[3] / "specs/002-google-keep-mcp"
CONTRACT_PATH = FEATURE_DIR / "contracts/memory.export.json"


@pytest.mark.contract
def test_export_contract_alignment():
    """Export tool adapter must reflect the published contract JSON."""
    import keep_mcp.adapters.tools.export as export

    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        spec = json.load(handle)

    assert export.REQUEST_SCHEMA == {
        key: spec[key]
        for key in ("$schema", "title", "type", "properties", "additionalProperties")
    }
    assert export.RESPONSE_SCHEMA == spec["response"]
    assert export.ERROR_SCHEMA == spec["error"]
    assert export.TOOL_NAME == "memory.export"
