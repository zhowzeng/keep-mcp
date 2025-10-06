"""Unit tests for adapter error classes."""

import pytest

from keep_mcp.adapters.errors import (
    AdapterError,
    ExportFailed,
    NotFoundError,
    StorageFailure,
    ValidationError,
)


class TestAdapterError:
    """Test the base AdapterError class."""

    def test_init_stores_code_and_message(self):
        error = AdapterError("TEST_CODE", "Test message")
        assert error.code == "TEST_CODE"
        assert error.message == "Test message"
        assert str(error) == "Test message"

    def test_to_dict_returns_code_and_message(self):
        error = AdapterError("TEST_CODE", "Test message")
        result = error.to_dict()
        assert result == {"code": "TEST_CODE", "message": "Test message"}


class TestValidationError:
    """Test ValidationError with VALIDATION_ERROR code."""

    def test_sets_validation_error_code(self):
        error = ValidationError("Invalid input")
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid input"

    def test_to_dict_includes_validation_code(self):
        error = ValidationError("Invalid input")
        result = error.to_dict()
        assert result == {"code": "VALIDATION_ERROR", "message": "Invalid input"}


class TestNotFoundError:
    """Test NotFoundError with NOT_FOUND code."""

    def test_sets_not_found_code(self):
        error = NotFoundError("Resource not found")
        assert error.code == "NOT_FOUND"
        assert error.message == "Resource not found"

    def test_to_dict_includes_not_found_code(self):
        error = NotFoundError("Card not found")
        result = error.to_dict()
        assert result == {"code": "NOT_FOUND", "message": "Card not found"}


class TestStorageFailure:
    """Test StorageFailure with STORAGE_FAILURE code."""

    def test_sets_storage_failure_code(self):
        error = StorageFailure("Database error")
        assert error.code == "STORAGE_FAILURE"
        assert error.message == "Database error"

    def test_to_dict_includes_storage_failure_code(self):
        error = StorageFailure("Connection failed")
        result = error.to_dict()
        assert result == {"code": "STORAGE_FAILURE", "message": "Connection failed"}


class TestExportFailed:
    """Test ExportFailed with EXPORT_FAILED code."""

    def test_sets_export_failed_code(self):
        error = ExportFailed("Export operation failed")
        assert error.code == "EXPORT_FAILED"
        assert error.message == "Export operation failed"

    def test_to_dict_includes_export_failed_code(self):
        error = ExportFailed("Cannot write to file")
        result = error.to_dict()
        assert result == {"code": "EXPORT_FAILED", "message": "Cannot write to file"}


class TestErrorInheritance:
    """Test that all errors are proper Exception subclasses."""

    def test_all_errors_are_exceptions(self):
        errors = [
            AdapterError("CODE", "msg"),
            ValidationError("msg"),
            NotFoundError("msg"),
            StorageFailure("msg"),
            ExportFailed("msg"),
        ]
        for error in errors:
            assert isinstance(error, Exception)
            assert isinstance(error, AdapterError)
