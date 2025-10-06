from __future__ import annotations

import json
from pathlib import Path

import pytest

FEATURE_DIR = Path(__file__).resolve().parents[3] / "specs/002-google-keep-mcp"
CONTRACT_PATH = FEATURE_DIR / "contracts/memory.manage.json"


@pytest.mark.contract
def test_manage_contract_alignment():
    """Manage tool adapter must publish request, response, and error schemas."""
    import keep_mcp.adapters.tools.manage as manage

    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        spec = json.load(handle)

    assert manage.REQUEST_SCHEMA == {
        key: spec[key]
        for key in ("$schema", "title", "type", "required", "properties", "additionalProperties", "allOf")
    }
    assert manage.RESPONSE_SCHEMA == spec["response"]
    assert manage.ERROR_SCHEMA == spec["error"]
    assert manage.TOOL_NAME == "memory.manage"
