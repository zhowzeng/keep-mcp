"""Unit tests for adapter tool modules."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from keep_mcp.adapters.errors import ValidationError
from keep_mcp.adapters.tools import add_card, export, manage, recall


class TestAddCardTool:
    """Test add_card adapter tool."""

    @pytest.fixture
    def mock_service(self):
        service = MagicMock()
        service.add_card = AsyncMock()
        return service

    async def test_execute_calls_service_with_request(self, mock_service):
        request = {
            "title": "Test Card",
            "summary": "Test summary",
            "body": "Test body",
            "tags": ["test", "demo"],
            "noteType": "PERMANENT",
        }
        expected_response = {
            "cardId": "01234567890123456789012345",
            "createdAt": "2025-10-06T08:00:00Z",
            "merged": False,
            "noteType": "PERMANENT",
            "sourceReference": None,
        }
        mock_service.add_card.return_value = expected_response

        result = await add_card.execute(mock_service, request)

        assert result == expected_response
        mock_service.add_card.assert_called_once_with(request)

    async def test_execute_raises_validation_error_on_value_error(self, mock_service):
        request = {"title": "Test", "summary": "Test", "noteType": "PERMANENT"}
        mock_service.add_card.side_effect = ValueError("Invalid title length")

        with pytest.raises(ValidationError) as exc_info:
            await add_card.execute(mock_service, request)

        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "Invalid title length" in exc_info.value.message

    def test_tool_name_defined(self):
        assert add_card.TOOL_NAME == "memory.add_card"

    def test_request_schema_has_required_fields(self):
        schema = add_card.REQUEST_SCHEMA
        assert set(schema["required"]) == {"title", "summary", "noteType"}
        assert "title" in schema["properties"]
        assert "summary" in schema["properties"]
        assert "noteType" in schema["properties"]
        assert schema["properties"]["title"]["maxLength"] == 120
        assert schema["properties"]["summary"]["maxLength"] == 500

    def test_response_schema_defines_structure(self):
        schema = add_card.RESPONSE_SCHEMA
        assert "cardId" in schema["required"]
        assert "createdAt" in schema["required"]
        assert "merged" in schema["required"]
        assert "noteType" in schema["required"]


class TestRecallTool:
    """Test recall adapter tool."""

    @pytest.fixture
    def mock_service(self):
        service = MagicMock()
        service.recall = AsyncMock()
        return service

    async def test_execute_calls_service_with_defaults(self, mock_service):
        request = {}
        expected_response = {"cards": [], "message": "No cards found"}
        mock_service.recall.return_value = expected_response

        result = await recall.execute(mock_service, request)

        mock_service.recall.assert_called_once_with(
            query=None, tags=[], limit=10, include_archived=False
        )
        # Message should be preserved when cards are empty
        assert "message" in result

    async def test_execute_calls_service_with_query_and_tags(self, mock_service):
        request = {
            "query": "test query",
            "tags": ["tag1", "tag2"],
            "limit": 5,
            "includeArchived": True,
        }
        expected_response = {
            "cards": [
                {
                    "cardId": "01234567890123456789012345",
                    "title": "Test",
                    "summary": "Summary",
                    "rankScore": 0.95,
                    "updatedAt": "2025-10-06T08:00:00Z",
                    "recallCount": 3,
                }
            ]
        }
        mock_service.recall.return_value = expected_response

        result = await recall.execute(mock_service, request)

        mock_service.recall.assert_called_once_with(
            query="test query", tags=["tag1", "tag2"], limit=5, include_archived=True
        )
        assert result == expected_response

    async def test_execute_raises_validation_error_on_invalid_tags(self, mock_service):
        request = {"tags": "not-a-list"}

        with pytest.raises(ValidationError) as exc_info:
            await recall.execute(mock_service, request)

        assert "valid list" in exc_info.value.message

    async def test_execute_raises_validation_error_on_service_value_error(
        self, mock_service
    ):
        request = {"limit": 5}
        mock_service.recall.side_effect = ValueError("Limit too high")

        with pytest.raises(ValidationError) as exc_info:
            await recall.execute(mock_service, request)

        assert "Limit too high" in exc_info.value.message

    async def test_execute_removes_none_message(self, mock_service):
        request = {"query": "test"}
        response_with_none_message = {
            "cards": [
                {
                    "cardId": "01234567890123456789012345",
                    "title": "Test",
                    "summary": "Summary",
                    "rankScore": 0.95,
                    "updatedAt": "2025-10-06T08:00:00Z",
                    "recallCount": 1,
                }
            ],
            "message": None,
        }
        mock_service.recall.return_value = response_with_none_message

        result = await recall.execute(mock_service, request)

        assert "message" not in result

    def test_tool_name_defined(self):
        assert recall.TOOL_NAME == "memory.recall"

    def test_request_schema_defines_optional_params(self):
        schema = recall.REQUEST_SCHEMA
        assert "required" not in schema or schema.get("required") == []
        assert "query" in schema["properties"]
        assert "tags" in schema["properties"]
        assert "limit" in schema["properties"]
        assert schema["properties"]["limit"]["maximum"] == 25
        response_schema = recall.RESPONSE_SCHEMA
        card_schema = response_schema["$defs"]["RecallCard"]
        card_properties = card_schema["properties"]
        assert "noteType" in card_properties


class TestManageTool:
    """Test manage adapter tool."""

    @pytest.fixture
    def mock_service(self):
        service = MagicMock()
        service.manage_card = AsyncMock()
        return service

    async def test_execute_calls_service_with_update_operation(self, mock_service):
        request = {
            "cardId": "01234567890123456789012345",
            "operation": "UPDATE",
            "payload": {"title": "Updated Title"},
        }
        expected_response = {
            "cardId": "01234567890123456789012345",
            "status": "UPDATED",
            "updatedAt": "2025-10-06T08:00:00Z",
        }
        mock_service.manage_card.return_value = expected_response

        result = await manage.execute(mock_service, request)

        assert result == expected_response
        mock_service.manage_card.assert_called_once_with(
            "01234567890123456789012345", "UPDATE", {"title": "Updated Title"}
        )

    async def test_execute_calls_service_with_archive_operation(self, mock_service):
        request = {"cardId": "01234567890123456789012345", "operation": "ARCHIVE"}
        expected_response = {
            "cardId": "01234567890123456789012345",
            "status": "ARCHIVED",
            "updatedAt": "2025-10-06T08:00:00Z",
        }
        mock_service.manage_card.return_value = expected_response

        result = await manage.execute(mock_service, request)

        mock_service.manage_card.assert_called_once_with(
            "01234567890123456789012345", "ARCHIVE", None
        )

    async def test_execute_calls_service_with_delete_operation(self, mock_service):
        request = {"cardId": "01234567890123456789012345", "operation": "DELETE"}
        expected_response = {
            "cardId": "01234567890123456789012345",
            "status": "DELETED",
        }
        mock_service.manage_card.return_value = expected_response

        result = await manage.execute(mock_service, request)

        mock_service.manage_card.assert_called_once_with(
            "01234567890123456789012345", "DELETE", None
        )

    async def test_execute_raises_validation_error_on_empty_card_id(
        self, mock_service
    ):
        request = {"cardId": "", "operation": "DELETE"}

        with pytest.raises(ValidationError) as exc_info:
            await manage.execute(mock_service, request)

        assert "at least 1 character" in exc_info.value.message

    async def test_execute_raises_validation_error_on_missing_card_id(
        self, mock_service
    ):
        request = {"operation": "DELETE"}

        with pytest.raises(ValidationError) as exc_info:
            await manage.execute(mock_service, request)

        assert exc_info.value.message == "Field required"

    async def test_execute_raises_validation_error_on_invalid_operation(
        self, mock_service
    ):
        request = {"cardId": "01234567890123456789012345", "operation": "INVALID"}

        with pytest.raises(ValidationError) as exc_info:
            await manage.execute(mock_service, request)

        assert "Input should be" in exc_info.value.message

    async def test_execute_raises_not_found_on_card_not_found(self, mock_service):
        from keep_mcp.adapters.errors import NotFoundError

        request = {"cardId": "01234567890123456789012345", "operation": "DELETE"}
        mock_service.manage_card.side_effect = ValueError("Card not found")

        with pytest.raises(NotFoundError) as exc_info:
            await manage.execute(mock_service, request)

        assert "Card not found" in exc_info.value.message

    async def test_execute_raises_validation_error_on_other_value_error(
        self, mock_service
    ):
        request = {
            "cardId": "01234567890123456789012345",
            "operation": "UPDATE",
            "payload": {"title": "Existing"},
        }
        mock_service.manage_card.side_effect = ValueError("Invalid title")

        with pytest.raises(ValidationError) as exc_info:
            await manage.execute(mock_service, request)

        assert "Invalid title" in exc_info.value.message

    def test_tool_name_defined(self):
        assert manage.TOOL_NAME == "memory.manage"

    def test_request_schema_requires_card_id_and_operation(self):
        schema = manage.REQUEST_SCHEMA
        assert "cardId" in schema["required"]
        assert "operation" in schema["required"]


class TestExportTool:
    """Test export adapter tool."""

    @pytest.fixture
    def mock_service(self):
        service = MagicMock()
        service.export = AsyncMock()
        return service

    async def test_execute_calls_service_with_absolute_path(self, mock_service):
        request = {"destinationPath": "/tmp/export.ndjson"}
        expected_response = {
            "filePath": "/tmp/export.ndjson",
            "exportedCount": 42,
        }
        mock_service.export.return_value = expected_response

        result = await export.execute(mock_service, request)

        assert result == expected_response
        mock_service.export.assert_called_once_with("/tmp/export.ndjson")

    async def test_execute_calls_service_without_path(self, mock_service):
        request = {}
        expected_response = {
            "filePath": "/home/user/.config/keep-mcp/export.ndjson",
            "exportedCount": 10,
        }
        mock_service.export.return_value = expected_response

        result = await export.execute(mock_service, request)

        assert result == expected_response
        mock_service.export.assert_called_once_with(None)

    async def test_execute_raises_export_failed_on_relative_path(self, mock_service):
        from keep_mcp.adapters.errors import ExportFailed

        request = {"destinationPath": "relative/path.ndjson"}

        with pytest.raises(ExportFailed) as exc_info:
            await export.execute(mock_service, request)

        assert "must be absolute" in exc_info.value.message

    async def test_execute_re_raises_export_failed_from_service(self, mock_service):
        from keep_mcp.adapters.errors import ExportFailed

        request = {"destinationPath": "/tmp/export.ndjson"}
        mock_service.export.side_effect = ExportFailed("Cannot write to file")

        with pytest.raises(ExportFailed) as exc_info:
            await export.execute(mock_service, request)

        assert "Cannot write to file" in exc_info.value.message

    def test_tool_name_defined(self):
        assert export.TOOL_NAME == "memory.export"

    def test_request_schema_defines_destination_path(self):
        schema = export.REQUEST_SCHEMA
        assert "destinationPath" in schema["properties"]
