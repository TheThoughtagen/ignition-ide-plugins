"""Tests for custom LSP method handlers in server.py.

Tests the handler functions directly without starting a full LSP server.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ignition_lsp.server import (
    find_scripts_handler,
    decode_script_handler,
    encode_script_handler,
    save_script_handler,
)

# Path to test fixtures
FIXTURES = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures"


@pytest.fixture
def mock_ls() -> MagicMock:
    """Mock IgnitionLanguageServer for testing handlers."""
    return MagicMock()


class TestDecodeScriptHandler:
    """Test ignition/decodeScript custom method."""

    def test_basic_decode(self, mock_ls: MagicMock) -> None:
        result = decode_script_handler(mock_ls, {"encoded": "line1\\nline2"})
        assert result["decoded"] == "line1\nline2"
        assert "indent" in result

    def test_unicode_decode(self, mock_ls: MagicMock) -> None:
        result = decode_script_handler(mock_ls, {"encoded": "x \\u003c 10"})
        assert result["decoded"] == "x < 10"

    def test_empty_string(self, mock_ls: MagicMock) -> None:
        result = decode_script_handler(mock_ls, {"encoded": ""})
        assert result["decoded"] == ""

    def test_missing_param(self, mock_ls: MagicMock) -> None:
        result = decode_script_handler(mock_ls, {})
        assert result["decoded"] == ""

    def test_dedent_strips_common_tabs(self, mock_ls: MagicMock) -> None:
        result = decode_script_handler(mock_ls, {"encoded": "\\tfrom x import y\\n\\treturn y"})
        assert result["decoded"] == "from x import y\nreturn y"
        assert result["indent"] == "\t"


class TestEncodeScriptHandler:
    """Test ignition/encodeScript custom method."""

    def test_basic_encode(self, mock_ls: MagicMock) -> None:
        result = encode_script_handler(mock_ls, {"decoded": "line1\nline2"})
        assert result == {"encoded": "line1\\nline2"}

    def test_unicode_encode(self, mock_ls: MagicMock) -> None:
        result = encode_script_handler(mock_ls, {"decoded": "x < 10"})
        assert result == {"encoded": "x \\u003c 10"}

    def test_round_trip(self, mock_ls: MagicMock) -> None:
        original = 'print("hello")\nif x < 10:\n\treturn True'
        encoded_result = encode_script_handler(mock_ls, {"decoded": original})
        decoded_result = decode_script_handler(
            mock_ls, {"encoded": encoded_result["encoded"]}
        )
        assert decoded_result["decoded"] == original

    def test_empty_string(self, mock_ls: MagicMock) -> None:
        result = encode_script_handler(mock_ls, {"decoded": ""})
        assert result == {"encoded": ""}


class TestFindScriptsHandler:
    """Test ignition/findScripts custom method."""

    def test_find_in_perspective_view(self, mock_ls: MagicMock) -> None:
        uri = (FIXTURES / "perspective-view-with-scripts.json").as_uri()
        result = find_scripts_handler(mock_ls, {"uri": uri})
        assert isinstance(result, list)
        assert len(result) >= 2
        # Each result should have the expected shape
        for item in result:
            assert "key" in item
            assert "line" in item
            assert "content" in item
            assert "context" in item
            assert "decodedPreview" in item

    def test_find_in_tags(self, mock_ls: MagicMock) -> None:
        uri = (FIXTURES / "ignition-project" / "tags.json").as_uri()
        result = find_scripts_handler(mock_ls, {"uri": uri})
        assert len(result) >= 1
        event_scripts = [r for r in result if r["key"] == "eventScript"]
        assert len(event_scripts) >= 1

    def test_nonexistent_file(self, mock_ls: MagicMock) -> None:
        result = find_scripts_handler(mock_ls, {"uri": "file:///nonexistent.json"})
        assert result == []

    def test_missing_uri(self, mock_ls: MagicMock) -> None:
        result = find_scripts_handler(mock_ls, {})
        assert result == []


class TestSaveScriptHandler:
    """Test ignition/saveScript custom method."""

    def test_save_script_round_trip(self, mock_ls: MagicMock) -> None:
        """Write a script, save modified content, verify the file changed correctly."""
        # Create a temp file with a known script
        content = {
            "events": {
                "onStartup": {
                    "script": "print(\\\"hello\\\")\\nprint(\\\"world\\\")"
                }
            }
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(content, f)
            temp_path = f.name

        try:
            uri = Path(temp_path).as_uri()

            # First find the script
            scripts = find_scripts_handler(mock_ls, {"uri": uri})
            assert len(scripts) >= 1
            script = scripts[0]

            # Save new content
            result = save_script_handler(
                mock_ls,
                {
                    "uri": uri,
                    "line": script["line"],
                    "key": script["key"],
                    "decodedContent": 'print("goodbye")\nprint("world")',
                },
            )
            assert result["success"] is True

            # Verify the file was modified
            new_text = Path(temp_path).read_text(encoding="utf-8")
            assert "goodbye" in new_text
            assert "hello" not in new_text
        finally:
            os.unlink(temp_path)

    def test_save_nonexistent_file(self, mock_ls: MagicMock) -> None:
        result = save_script_handler(
            mock_ls,
            {
                "uri": "file:///nonexistent.json",
                "line": 1,
                "key": "script",
                "decodedContent": "test",
            },
        )
        assert result["success"] is False
        assert "error" in result

    def test_save_wrong_line(self, mock_ls: MagicMock) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write('{"script": "test\\nvalue"}\n')
            temp_path = f.name

        try:
            result = save_script_handler(
                mock_ls,
                {
                    "uri": Path(temp_path).as_uri(),
                    "line": 999,
                    "key": "script",
                    "decodedContent": "new",
                },
            )
            assert result["success"] is False
        finally:
            os.unlink(temp_path)

    def test_save_wrong_key(self, mock_ls: MagicMock) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write('{"script": "test\\nvalue"}\n')
            temp_path = f.name

        try:
            result = save_script_handler(
                mock_ls,
                {
                    "uri": Path(temp_path).as_uri(),
                    "line": 1,
                    "key": "wrongKey",
                    "decodedContent": "new",
                },
            )
            assert result["success"] is False
        finally:
            os.unlink(temp_path)
