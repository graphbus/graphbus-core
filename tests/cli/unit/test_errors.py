"""
Unit tests for CLI error utilities
"""

import pytest

from graphbus_cli.utils.errors import (
    CLIError, BuildError, ValidationError, RuntimeError,
    format_exception, suggest_fix
)


class TestCLIErrors:
    """Tests for CLI error classes"""

    def test_cli_error_basic(self):
        """Test basic CLIError"""
        error = CLIError("Test error")
        assert str(error) == "Test error"
        assert error.exit_code == 1

    def test_cli_error_custom_exit_code(self):
        """Test CLIError with custom exit code"""
        error = CLIError("Test error", exit_code=42)
        assert error.exit_code == 42

    def test_build_error(self):
        """Test BuildError"""
        error = BuildError("Build failed")
        assert str(error) == "Build failed"
        assert error.exit_code == 4

    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert error.exit_code == 3

    def test_runtime_error(self):
        """Test RuntimeError"""
        error = RuntimeError("Runtime failed")
        assert str(error) == "Runtime failed"
        assert error.exit_code == 5


class TestExceptionFormatting:
    """Tests for exception formatting"""

    def test_format_exception_basic(self):
        """Test basic exception formatting"""
        exc = ValueError("Test error")
        result = format_exception(exc)

        assert "ValueError" in result
        assert "Test error" in result

    def test_format_exception_with_context(self):
        """Test exception formatting with context"""
        exc = ValueError("Test error")
        result = format_exception(exc, context="test_function")

        assert "test_function" in result
        assert "ValueError" in result
        assert "Test error" in result


class TestErrorSuggestions:
    """Tests for error suggestion system"""

    def test_suggest_fix_file_not_found(self):
        """Test suggestion for file not found errors"""
        exc = FileNotFoundError("No such file or directory")
        suggestion = suggest_fix(exc)

        assert suggestion is not None
        assert "path" in suggestion.lower()

    def test_suggest_fix_module_not_found(self):
        """Test suggestion for module import errors"""
        exc = ImportError("No module named 'test'")
        suggestion = suggest_fix(exc)

        assert suggestion is not None
        assert "dependencies" in suggestion.lower() or "install" in suggestion.lower()

    def test_suggest_fix_permission_denied(self):
        """Test suggestion for permission errors"""
        exc = PermissionError("Permission denied")
        suggestion = suggest_fix(exc)

        assert suggestion is not None
        assert "permission" in suggestion.lower()

    def test_suggest_fix_json_error(self):
        """Test suggestion for JSON errors"""
        exc = ValueError("Invalid JSON format")
        suggestion = suggest_fix(exc)

        assert suggestion is not None
        assert "json" in suggestion.lower() or "yaml" in suggestion.lower()

    def test_suggest_fix_attribute_error(self):
        """Test suggestion for attribute errors"""
        exc = AttributeError("has no attribute 'test'")
        suggestion = suggest_fix(exc)

        assert suggestion is not None
        assert "attribute" in suggestion.lower() or "method" in suggestion.lower()

    def test_suggest_fix_cycle_error(self):
        """Test suggestion for cycle errors"""
        exc = ValueError("Circular dependency detected")
        suggestion = suggest_fix(exc)

        assert suggestion is not None
        assert "circular" in suggestion.lower() or "cycle" in suggestion.lower()

    def test_suggest_fix_unknown_error(self):
        """Test suggestion for unknown errors"""
        exc = Exception("Unknown error")
        suggestion = suggest_fix(exc)

        # Should return None for unknown errors
        assert suggestion is None
