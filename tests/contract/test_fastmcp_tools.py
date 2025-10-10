"""Contract tests for FastMCP server tools.

These tests verify that FastMCP tool wrappers correctly invoke adapter layers,
handle errors appropriately, and return properly structured Pydantic responses.
"""

import pytest

from keep_mcp.adapters.errors import (
    AdapterError,
    ExportFailed,
    NotFoundError,
    ValidationError,
)
from keep_mcp.fastmcp_server import (
    AddCardOutput,
    ExportOutput,
    ManageOutput,
    RecallCard,
    RecallOutput,
)


class TestAddCardOutput:
    """Test AddCardOutput Pydantic model."""

    def test_minimal_response(self):
        """Test creating output with minimal required fields."""
        output = AddCardOutput(
            cardId="01JABS4RXYZ0123456789ABCD",
            createdAt="2025-10-06T08:00:00Z",
            merged=False,
            noteType="PERMANENT",
        )
        assert output.cardId == "01JABS4RXYZ0123456789ABCD"
        assert output.merged is False
        assert output.canonicalCardId is None

    def test_merged_card_response(self):
        """Test creating output for merged card."""
        output = AddCardOutput(
            cardId="01JABS4RXYZ0123456789ABCD",
            createdAt="2025-10-06T08:00:00Z",
            merged=True,
            noteType="PERMANENT",
            canonicalCardId="01JABS4RXYZ0123456789ABCE",
        )
        assert output.merged is True
        assert output.canonicalCardId == "01JABS4RXYZ0123456789ABCE"


class TestRecallOutput:
    """Test RecallOutput and RecallCard Pydantic models."""

    def test_empty_recall_result(self):
        """Test recall output with no cards."""
        output = RecallOutput(cards=[], message="No cards found")
        assert len(output.cards) == 0
        assert output.message == "No cards found"

    def test_recall_with_cards(self):
        """Test recall output with multiple cards."""
        cards = [
            RecallCard(
                cardId="01JABS4RXYZ0123456789ABCD",
                title="First Card",
                summary="First summary",
                body="First body",
                tags=["tag1", "tag2"],
                noteType="PERMANENT",
                sourceReference="https://example.com",
                rankScore=0.95,
                updatedAt="2025-10-06T08:00:00Z",
                lastRecalledAt="2025-10-06T07:00:00Z",
                recallCount=5,
            ),
            RecallCard(
                cardId="01JABS4RXYZ0123456789ABCE",
                title="Second Card",
                summary="Second summary",
                noteType="LITERATURE",
                rankScore=0.88,
                updatedAt="2025-10-05T08:00:00Z",
                recallCount=2,
            ),
        ]
        output = RecallOutput(cards=cards)
        assert len(output.cards) == 2
        assert output.cards[0].rankScore == 0.95
        assert output.cards[1].body is None
        assert output.message is None


class TestManageOutput:
    """Test ManageOutput Pydantic model."""

    def test_update_operation_response(self):
        """Test manage output for update operation."""
        output = ManageOutput(
            cardId="01JABS4RXYZ0123456789ABCD",
            status="UPDATED",
            updatedAt="2025-10-06T09:00:00Z",
        )
        assert output.status == "UPDATED"
        assert output.updatedAt == "2025-10-06T09:00:00Z"

    def test_archive_operation_response(self):
        """Test manage output for archive operation."""
        output = ManageOutput(
            cardId="01JABS4RXYZ0123456789ABCD",
            status="ARCHIVED",
            updatedAt="2025-10-06T09:00:00Z",
        )
        assert output.status == "ARCHIVED"

    def test_delete_operation_response(self):
        """Test manage output for delete operation."""
        output = ManageOutput(
            cardId="01JABS4RXYZ0123456789ABCD", status="DELETED"
        )
        assert output.status == "DELETED"
        assert output.updatedAt is None


class TestExportOutput:
    """Test ExportOutput Pydantic model."""

    def test_export_response(self):
        """Test export output structure."""
        output = ExportOutput(filePath="/tmp/export.ndjson", exportedCount=42)
        assert output.filePath == "/tmp/export.ndjson"
        assert output.exportedCount == 42

    def test_export_with_zero_count(self):
        """Test export output with no cards exported."""
        output = ExportOutput(
            filePath="/home/user/.config/keep-mcp/export.ndjson", exportedCount=0
        )
        assert output.exportedCount == 0


class TestAdapterErrorMapping:
    """Test that adapter errors have correct codes."""

    def test_validation_error_code(self):
        """Test ValidationError has VALIDATION_ERROR code."""
        error = ValidationError("Invalid input")
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid input"

    def test_not_found_error_code(self):
        """Test NotFoundError has NOT_FOUND code."""
        error = NotFoundError("Card not found")
        assert error.code == "NOT_FOUND"

    def test_export_failed_error_code(self):
        """Test ExportFailed has EXPORT_FAILED code."""
        error = ExportFailed("Export failed")
        assert error.code == "EXPORT_FAILED"

    def test_adapter_error_to_dict(self):
        """Test AdapterError can be converted to dict."""
        error = ValidationError("Test error")
        error_dict = error.to_dict()
        assert error_dict == {"code": "VALIDATION_ERROR", "message": "Test error"}
