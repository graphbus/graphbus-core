"""
Unit tests for CLI output utilities
"""

import pytest
from graphbus_cli.utils.output import format_json, format_duration


class TestOutputUtilities:
    """Tests for output utility functions"""

    def test_format_json(self):
        """Test JSON formatting"""
        data = {"key": "value", "number": 42}
        result = format_json(data)

        assert '"key": "value"' in result
        assert '"number": 42' in result

    def test_format_duration_milliseconds(self):
        """Test duration formatting for milliseconds"""
        assert format_duration(0.1) == "100ms"

    def test_format_duration_seconds(self):
        """Test duration formatting for seconds"""
        assert format_duration(1.0) == "1.0s"

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes"""
        assert format_duration(60) == "1m 0s"
