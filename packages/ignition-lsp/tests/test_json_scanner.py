"""Tests for json_scanner.py — finding embedded scripts in Ignition JSON."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from ignition_lsp.json_scanner import (
    ScriptLocation,
    find_scripts,
    find_scripts_in_lines,
    replace_script_in_line,
    _extract_json_string_value,
)

# Path to test fixtures
FIXTURES = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures"


class TestFindScriptsInFixtures:
    """Test against the existing fixture JSON files."""

    def test_perspective_view_with_scripts(self) -> None:
        scripts = find_scripts(str(FIXTURES / "perspective-view-with-scripts.json"))
        assert len(scripts) >= 2
        keys = {s.key for s in scripts}
        assert "script" in keys or "onActionPerformed" in keys or "onStartup" in keys

    def test_tags_json(self) -> None:
        scripts = find_scripts(str(FIXTURES / "ignition-project" / "tags.json"))
        assert len(scripts) >= 1
        # Should find the eventScript
        event_scripts = [s for s in scripts if s.key == "eventScript"]
        assert len(event_scripts) >= 1

    def test_tags_context_detection(self) -> None:
        scripts = find_scripts(str(FIXTURES / "ignition-project" / "tags.json"))
        event_scripts = [s for s in scripts if s.key == "eventScript"]
        assert len(event_scripts) >= 1
        # Should detect tag name and event name context
        ctx = event_scripts[0].context
        assert "SampleTag" in ctx or "valueChanged" in ctx

    def test_nonexistent_file(self) -> None:
        scripts = find_scripts("/nonexistent/path/file.json")
        assert scripts == []

    def test_perspective_button(self) -> None:
        scripts = find_scripts(str(FIXTURES / "perspective-button-with-script.json"))
        assert len(scripts) >= 1


class TestFindScriptsInLines:
    """Test the core line-scanning logic."""

    def test_simple_script_key(self) -> None:
        lines = ['  "script": "print(\\"hello\\")\\nprint(\\"world\\")"']
        scripts = find_scripts_in_lines(lines)
        assert len(scripts) == 1
        assert scripts[0].key == "script"
        assert scripts[0].line == 1
        assert "hello" in scripts[0].decoded_preview

    def test_expression_key(self) -> None:
        lines = ['  "expression": "tag.value + 1"']
        scripts = find_scripts_in_lines(lines)
        # Expressions are always accepted even without encoded markers
        assert len(scripts) == 1
        assert scripts[0].key == "expression"

    def test_plain_string_not_detected(self) -> None:
        lines = ['  "script": "just a plain string"']
        scripts = find_scripts_in_lines(lines)
        # "just a plain string" has no encoded markers, should be skipped
        assert len(scripts) == 0

    def test_multiple_scripts(self) -> None:
        lines = [
            '  "onStartup": "# startup\\nprint(\\"init\\")"',
            '  "onShutdown": "# shutdown\\nprint(\\"cleanup\\")"',
        ]
        scripts = find_scripts_in_lines(lines)
        assert len(scripts) == 2
        keys = {s.key for s in scripts}
        assert keys == {"onStartup", "onShutdown"}

    def test_empty_script_ignored(self) -> None:
        lines = ['  "script": ""']
        scripts = find_scripts_in_lines(lines)
        assert len(scripts) == 0

    def test_tag_context_backward_scan(self) -> None:
        lines = [
            '{',
            '  "name": "MyTag",',
            '  "eventScripts": {',
            '    "valueChanged": {',
            '      "eventScript": "logger.info(\\"changed\\")\\nx \\u003d 1"',
            '    }',
            '  }',
            '}',
        ]
        scripts = find_scripts_in_lines(lines)
        assert len(scripts) == 1
        assert scripts[0].context == "MyTag/valueChanged"

    def test_expression_context(self) -> None:
        lines = [
            '{',
            '  "name": "TempSensor",',
            '  "expression": "tag.value * 1.8 + 32"',
            '}',
        ]
        scripts = find_scripts_in_lines(lines)
        assert len(scripts) == 1
        assert scripts[0].context == "TempSensor/Expression"


class TestExtractJsonStringValue:
    """Test the JSON string extraction helper."""

    def test_simple_string(self) -> None:
        text = '"hello world"'
        assert _extract_json_string_value(text, 1) == "hello world"

    def test_escaped_quotes(self) -> None:
        text = r'"say \"hi\""'
        result = _extract_json_string_value(text, 1)
        assert result == r'say \"hi\"'

    def test_escaped_backslash(self) -> None:
        text = r'"path\\to\\file"'
        result = _extract_json_string_value(text, 1)
        assert result == r"path\\to\\file"

    def test_unclosed_string(self) -> None:
        text = '"no closing quote'
        assert _extract_json_string_value(text, 1) is None


class TestReplaceScriptInLine:
    """Test replacing script content in a JSON line."""

    def test_basic_replacement(self) -> None:
        line = '    "script": "old\\ncontent"'
        result = replace_script_in_line(line, "script", "new\\ncontent")
        assert '"script": "new\\ncontent"' in result

    def test_key_not_found(self) -> None:
        line = '    "other": "value"'
        result = replace_script_in_line(line, "script", "new")
        assert result == line

    def test_preserves_surrounding(self) -> None:
        line = '    "script": "old", "other": "value"'
        result = replace_script_in_line(line, "script", "new")
        assert result == '    "script": "new", "other": "value"'

    def test_round_trip_with_find_and_replace(self) -> None:
        """Find a script, decode it, re-encode, replace — content should match."""
        from ignition_lsp.encoding import decode, encode

        line = '    "eventScript": "print(\\"hello\\")\\nprint(\\"world\\")"'
        scripts = find_scripts_in_lines([line])
        assert len(scripts) == 1

        decoded = decode(scripts[0].content)
        re_encoded = encode(decoded)
        new_line = replace_script_in_line(line, "eventScript", re_encoded)

        assert new_line == line
