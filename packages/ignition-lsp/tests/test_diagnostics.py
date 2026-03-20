"""Tests for diagnostics.py — severity mapping, routing, Perspective/tag detection."""

import json
from pathlib import Path

import pytest
from lsprotocol.types import DiagnosticSeverity

from ignition_lsp.diagnostics import (
    get_diagnostics,
    get_diagnostics_for_file,
    _is_perspective_view,
    _is_tag_json,
    _find_script_line,
    _get_tag_diagnostics,
    _get_tag_structural_diagnostics,
    _TAG_LINTER_AVAILABLE,
)


class MockDocument:
    """Simple mock document for diagnostics tests."""

    def __init__(self, uri: str, source: str):
        self.uri = uri
        self.source = source


# ── Routing Tests ────────────────────────────────────────────────────


class TestGetDiagnostics:
    def test_non_perspective_json_returns_empty(self):
        """Non-Perspective JSON files should be skipped."""
        doc = MockDocument("file:///project/resource.json", '{"key": "value"}')
        result = get_diagnostics(doc)
        assert result == []

    def test_python_file_returns_list(self):
        """Python files should return a list (possibly empty if ignition-lint not available)."""
        doc = MockDocument("file:///script.py", "import system\nprint('hello')")
        result = get_diagnostics(doc)
        assert isinstance(result, list)

    def test_empty_source(self):
        """Empty documents should not crash."""
        doc = MockDocument("file:///empty.py", "")
        result = get_diagnostics(doc)
        assert isinstance(result, list)

    def test_virtual_buffer_not_skipped(self):
        """Virtual buffers with [Ignition: prefix in URI should be processed."""
        doc = MockDocument(
            "file:///[Ignition: script.py]",
            "import system\nsystem.tag.readBlocking([])",
        )
        result = get_diagnostics(doc)
        assert isinstance(result, list)

    def test_no_crash_on_syntax_error(self):
        """Documents with syntax errors should not crash the diagnostics provider."""
        doc = MockDocument("file:///bad.py", "def broken(\n    pass")
        result = get_diagnostics(doc)
        assert isinstance(result, list)

    def test_perspective_view_json_returns_list(self):
        """Perspective view.json files should return diagnostics (list)."""
        view_json = '{"root": {"type": "ia.container.flex", "meta": {"name": "root"}, "props": {}}}'
        doc = MockDocument("file:///project/views/MyView/view.json", view_json)
        result = get_diagnostics(doc)
        assert isinstance(result, list)

    def test_invalid_json_returns_syntax_error(self):
        """Invalid JSON in a .json file should return a syntax error diagnostic."""
        doc = MockDocument("file:///project/broken.json", "not valid json {{{")
        result = get_diagnostics(doc)
        assert len(result) == 1
        assert result[0].code == "JSON_SYNTAX_ERROR"
        assert result[0].severity == DiagnosticSeverity.Error

    def test_json_syntax_error_has_location(self):
        """JSON syntax error should point to the error location."""
        # Missing comma after "a": 1
        doc = MockDocument("file:///view.json", '{\n  "a": 1\n  "b": 2\n}')
        result = get_diagnostics(doc)
        assert len(result) == 1
        assert result[0].code == "JSON_SYNTAX_ERROR"
        # Error should be on line 3 (0-indexed: 2)
        assert result[0].range.start.line == 2


# ── Perspective Detection Tests ──────────────────────────────────────


class TestIsPerspectiveView:
    def test_true_for_perspective_view(self):
        content = '{"root": {"type": "ia.container.flex", "meta": {"name": "root"}}}'
        assert _is_perspective_view(content) is True

    def test_false_for_resource_json(self):
        content = '{"scope": "G", "version": 1}'
        assert _is_perspective_view(content) is False

    def test_false_for_invalid_json(self):
        assert _is_perspective_view("not json") is False

    def test_false_for_non_ia_root_type(self):
        content = '{"root": {"type": "custom.thing"}}'
        assert _is_perspective_view(content) is False

    def test_false_for_missing_root(self):
        content = '{"custom": {}, "params": {}}'
        assert _is_perspective_view(content) is False

    def test_false_for_empty_object(self):
        assert _is_perspective_view("{}") is False


# ── File Path Helper Tests ───────────────────────────────────────────


class TestGetDiagnosticsForFile:
    def test_returns_list(self):
        result = get_diagnostics_for_file("test.py", "print('hello')")
        assert isinstance(result, list)

    def test_json_file_skipped(self):
        result = get_diagnostics_for_file("resource.json", '{"key": "value"}')
        assert result == []

    def test_perspective_json_returns_list(self):
        content = '{"root": {"type": "ia.container.flex", "meta": {"name": "root"}, "props": {}}}'
        result = get_diagnostics_for_file("view.json", content)
        assert isinstance(result, list)


# ── Tag Detection Tests ─────────────────────────────────────────────


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestIsTagJson:
    def test_true_for_single_tag(self):
        content = '{"name": "MyTag", "tagType": "AtomicTag"}'
        assert _is_tag_json(content) is True

    def test_true_for_tag_folder(self):
        content = '{"name": "Folder", "tagType": "Folder", "tags": []}'
        assert _is_tag_json(content) is True

    def test_true_for_tags_array_root(self):
        content = '{"tags": [{"name": "T1", "tagType": "AtomicTag"}]}'
        assert _is_tag_json(content) is True

    def test_false_for_perspective_view(self):
        content = '{"root": {"type": "ia.container.flex"}}'
        assert _is_tag_json(content) is False

    def test_false_for_resource_json(self):
        content = '{"scope": "G", "version": 1}'
        assert _is_tag_json(content) is False

    def test_false_for_invalid_json(self):
        assert _is_tag_json("not json") is False

    def test_false_for_empty_object(self):
        assert _is_tag_json("{}") is False


# ── Tag Diagnostics Tests ───────────────────────────────────────────


class TestTagDiagnostics:
    def test_tag_without_scripts_returns_list(self):
        """Tag JSON with no eventScripts returns a list (structural diagnostics may exist)."""
        content = '{"name": "PlainTag", "tagType": "AtomicTag", "value": 0}'
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_diagnostics(doc)
        assert isinstance(result, list)

    def test_tag_with_valid_script_returns_list(self):
        """Tag with a valid eventScript returns a list (may be empty if lint unavailable)."""
        content = json.dumps({
            "name": "GoodTag",
            "tagType": "AtomicTag",
            "eventScripts": {
                "valueChanged": {
                    "eventScript": "x = 1\n",
                    "enabled": True,
                }
            },
        })
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_diagnostics(doc)
        assert isinstance(result, list)

    def test_empty_eventscript_no_script_diagnostics(self):
        """Empty eventScript strings should produce no script diagnostics."""
        content = json.dumps({
            "name": "EmptyTag",
            "tagType": "AtomicTag",
            "dataType": "Int4",
            "valueSource": "memory",
            "eventScripts": {
                "valueChanged": {
                    "eventScript": "",
                    "enabled": False,
                }
            },
        })
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_diagnostics(doc)
        # No script-related diagnostics (structural may still exist)
        script_diags = [d for d in result if "JYTHON" in (d.code or "")]
        assert script_diags == []

    def test_whitespace_only_eventscript_no_script_diagnostics(self):
        """Whitespace-only eventScript should produce no script diagnostics."""
        content = json.dumps({
            "name": "WsTag",
            "tagType": "AtomicTag",
            "dataType": "Int4",
            "valueSource": "memory",
            "eventScripts": {
                "valueChanged": {
                    "eventScript": "   \n  \n",
                    "enabled": True,
                }
            },
        })
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_diagnostics(doc)
        script_diags = [d for d in result if "JYTHON" in (d.code or "")]
        assert script_diags == []

    def test_nested_tags_all_visited(self):
        """Scripts in nested tags should be found and processed."""
        content = json.dumps({
            "name": "Folder",
            "tagType": "Folder",
            "tags": [
                {
                    "name": "Child1",
                    "tagType": "AtomicTag",
                    "eventScripts": {
                        "valueChanged": {
                            "eventScript": "x = 1\n",
                            "enabled": True,
                        }
                    },
                },
                {
                    "name": "Child2",
                    "tagType": "AtomicTag",
                    "eventScripts": {
                        "qualityChanged": {
                            "eventScript": "y = 2\n",
                            "enabled": True,
                        }
                    },
                },
            ],
        })
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_diagnostics(doc)
        # Should not crash; results depend on lint availability
        assert isinstance(result, list)

    def test_multiple_events_per_tag(self):
        """Tags with multiple event types should all be processed."""
        content = json.dumps({
            "name": "MultiTag",
            "tagType": "AtomicTag",
            "eventScripts": {
                "valueChanged": {
                    "eventScript": "a = 1\n",
                    "enabled": True,
                },
                "qualityChanged": {
                    "eventScript": "b = 2\n",
                    "enabled": True,
                },
            },
        })
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_diagnostics(doc)
        assert isinstance(result, list)

    def test_tag_json_routed_by_get_diagnostics(self):
        """Tag JSON files should be routed to tag diagnostics, not skipped."""
        content = json.dumps({
            "name": "RoutedTag",
            "tagType": "AtomicTag",
            "eventScripts": {
                "valueChanged": {
                    "eventScript": "x = 1\n",
                    "enabled": True,
                }
            },
        })
        doc = MockDocument("file:///project/tags.json", content)
        result = get_diagnostics(doc)
        assert isinstance(result, list)

    def test_fixture_file_loads(self):
        """The tag fixture file should parse and be detected as tag JSON."""
        fixture = FIXTURES_DIR / "tag_with_scripts.json"
        content = fixture.read_text()
        assert _is_tag_json(content) is True

    def test_fixture_returns_diagnostics_list(self):
        """The fixture file should produce a list of diagnostics (possibly empty)."""
        fixture = FIXTURES_DIR / "tag_with_scripts.json"
        content = fixture.read_text()
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_diagnostics(doc)
        assert isinstance(result, list)


# ── _find_script_line Tests ─────────────────────────────────────────


class TestFindScriptLine:
    def test_finds_eventscript_line(self):
        raw = '{\n  "name": "T",\n  "eventScript": "x = 1"\n}'
        line = _find_script_line(raw, "eventScript", "x = 1")
        assert line == 2  # 0-indexed

    def test_returns_zero_when_not_found(self):
        raw = '{"name": "T"}'
        line = _find_script_line(raw, "eventScript", "missing")
        assert line == 0

    def test_fallback_to_key_match(self):
        raw = '{\n  "eventScript": "something_else"\n}'
        line = _find_script_line(raw, "eventScript", "totally_different")
        # Should fall back to finding just the key
        assert line == 1


# ── Tag Structural Diagnostics Tests ─────────────────────────────


class TestTagStructuralDiagnostics:
    """Tests for IgnitionTagLinter integration via _get_tag_structural_diagnostics."""

    def test_valid_tag_no_structural_errors(self):
        """A fully valid AtomicTag should produce no ERROR-level structural diagnostics."""
        fixture = FIXTURES_DIR / "tag_atomic_valid.json"
        content = fixture.read_text()
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_structural_diagnostics(doc)
        if _TAG_LINTER_AVAILABLE:
            errors = [d for d in result if d.severity == DiagnosticSeverity.Error]
            assert errors == []
        else:
            assert result == []

    def test_invalid_tag_type_caught(self):
        """An invalid tagType should produce an ERROR diagnostic."""
        content = json.dumps({
            "name": "BadType",
            "tagType": "NotAValidType",
            "dataType": "Int4",
        })
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_structural_diagnostics(doc)
        if _TAG_LINTER_AVAILABLE:
            codes = {d.code for d in result}
            assert "INVALID_TAG_TYPE" in codes
        else:
            assert result == []

    def test_udt_instance_missing_type_id(self):
        """UdtInstance without typeId should produce MISSING_TYPE_ID."""
        content = json.dumps({
            "name": "NoTypeId",
            "tagType": "UdtInstance",
        })
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_structural_diagnostics(doc)
        if _TAG_LINTER_AVAILABLE:
            codes = {d.code for d in result}
            assert "MISSING_TYPE_ID" in codes
        else:
            assert result == []

    def test_unknown_keys_flagged(self):
        """Unknown property keys on AtomicTag should produce UNKNOWN_TAG_PROP."""
        fixture = FIXTURES_DIR / "tag_invalid_keys.json"
        content = fixture.read_text()
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_structural_diagnostics(doc)
        if _TAG_LINTER_AVAILABLE:
            codes = {d.code for d in result}
            assert "UNKNOWN_TAG_PROP" in codes
        else:
            assert result == []

    def test_structural_and_script_combined(self):
        """Tag diagnostics should include both structural and script results."""
        content = json.dumps({
            "name": "Combined",
            "tagType": "AtomicTag",
            "eventScripts": {
                "valueChanged": {
                    "eventScript": "x = 1\n",
                    "enabled": True,
                }
            },
        })
        doc = MockDocument("file:///tags.json", content)
        result = _get_tag_diagnostics(doc)
        assert isinstance(result, list)
        if _TAG_LINTER_AVAILABLE:
            # Should have at least MISSING_DATA_TYPE from structural linter
            codes = {d.code for d in result}
            assert "MISSING_DATA_TYPE" in codes
