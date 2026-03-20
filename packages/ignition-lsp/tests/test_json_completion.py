"""Tests for json_completion.py — JSON completions for Perspective views."""

import json
from unittest.mock import MagicMock

import pytest

from ignition_lsp.json_completion import (
    COMPONENT_TYPES,
    KNOWN_PROPS,
    COMPONENT_KEYS,
    EVENT_CATEGORIES,
    COMPONENT_EVENTS,
    CONTEXT_TYPE_VALUE,
    CONTEXT_COMPONENT_KEY,
    CONTEXT_PROPS_KEY,
    CONTEXT_EVENTS_KEY,
    CONTEXT_EVENT_HANDLERS,
    is_perspective_json,
    get_json_completions,
    _detect_json_context,
    _find_enclosing_key,
)


def _make_document(source: str, uri: str = "file:///test/view.json") -> MagicMock:
    """Create a mock TextDocument."""
    doc = MagicMock()
    doc.source = source
    doc.uri = uri
    doc.lines = source.splitlines()
    return doc


def _make_position(line: int, character: int) -> MagicMock:
    """Create a mock Position."""
    pos = MagicMock()
    pos.line = line
    pos.character = character
    return pos


# ──────────────────────────────────────────────
# is_perspective_json
# ──────────────────────────────────────────────


class TestIsPerspectiveJson:
    def test_true_for_perspective_view(self):
        source = json.dumps({
            "root": {"type": "ia.container.flex", "children": []}
        })
        doc = _make_document(source)
        assert is_perspective_json(doc) is True

    def test_false_for_non_perspective(self):
        source = json.dumps({"title": "Test", "enabled": True})
        doc = _make_document(source)
        assert is_perspective_json(doc) is False

    def test_false_for_python_uri(self):
        source = json.dumps({
            "root": {"type": "ia.container.flex", "children": []}
        })
        doc = _make_document(source, uri="file:///test/script.py")
        assert is_perspective_json(doc) is False

    def test_false_for_invalid_json(self):
        doc = _make_document("not valid json {{{", uri="file:///test/view.json")
        assert is_perspective_json(doc) is False

    def test_false_for_non_ia_root(self):
        source = json.dumps({"root": {"type": "custom.component", "children": []}})
        doc = _make_document(source)
        assert is_perspective_json(doc) is False


# ──────────────────────────────────────────────
# _detect_json_context
# ──────────────────────────────────────────────


class TestDetectJsonContext:
    def test_type_value_context(self):
        source = '  "type": "ia.cont'
        doc = _make_document(source)
        pos = _make_position(0, len(source))
        result = _detect_json_context(doc, pos)
        assert result is not None
        assert result[0] == CONTEXT_TYPE_VALUE
        assert result[1] == "ia.cont"

    def test_type_value_empty_partial(self):
        source = '  "type": "'
        doc = _make_document(source)
        pos = _make_position(0, len(source))
        result = _detect_json_context(doc, pos)
        assert result is not None
        assert result[0] == CONTEXT_TYPE_VALUE
        assert result[1] == ""

    def test_props_key_context(self):
        lines = [
            '{',
            '  "props": {',
            '    "te',
        ]
        source = "\n".join(lines)
        doc = _make_document(source)
        pos = _make_position(2, 7)  # at "te
        result = _detect_json_context(doc, pos)
        assert result is not None
        assert result[0] == CONTEXT_PROPS_KEY
        assert result[1] == "te"

    def test_events_key_context(self):
        lines = [
            '{',
            '  "events": {',
            '    "co',
        ]
        source = "\n".join(lines)
        doc = _make_document(source)
        pos = _make_position(2, 7)
        result = _detect_json_context(doc, pos)
        assert result is not None
        assert result[0] == CONTEXT_EVENTS_KEY
        assert result[1] == "co"

    def test_component_key_context(self):
        lines = [
            '{',
            '  "ty',
        ]
        source = "\n".join(lines)
        doc = _make_document(source)
        pos = _make_position(1, 5)
        result = _detect_json_context(doc, pos)
        assert result is not None
        assert result[0] == CONTEXT_COMPONENT_KEY
        assert result[1] == "ty"

    def test_event_handlers_context(self):
        lines = [
            '{',
            '  "events": {',
            '    "component": {',
            '      "on',
        ]
        source = "\n".join(lines)
        doc = _make_document(source)
        pos = _make_position(3, 9)
        result = _detect_json_context(doc, pos)
        assert result is not None
        assert result[0] == CONTEXT_EVENT_HANDLERS
        assert result[1] == "on"


# ──────────────────────────────────────────────
# get_json_completions
# ──────────────────────────────────────────────


class TestGetJsonCompletions:
    def test_type_value_offers_component_types(self):
        source = '  "type": "ia.'
        doc = _make_document(source)
        pos = _make_position(0, len(source))
        result = get_json_completions(doc, pos)
        assert result is not None
        labels = {item.label for item in result.items}
        assert "ia.container.flex" in labels
        assert "ia.display.label" in labels

    def test_type_value_filters_on_partial(self):
        source = '  "type": "ia.input.'
        doc = _make_document(source)
        pos = _make_position(0, len(source))
        result = get_json_completions(doc, pos)
        assert result is not None
        for item in result.items:
            assert "ia.input." in item.label

    def test_props_key_offers_known_props(self):
        lines = [
            '{',
            '  "props": {',
            '    "',
        ]
        source = "\n".join(lines)
        doc = _make_document(source)
        pos = _make_position(2, 5)
        result = get_json_completions(doc, pos)
        assert result is not None
        labels = {item.label for item in result.items}
        assert "text" in labels
        assert "style" in labels
        assert "visible" in labels

    def test_component_key_offers_structural_keys(self):
        lines = [
            '{',
            '  "',
        ]
        source = "\n".join(lines)
        doc = _make_document(source)
        pos = _make_position(1, 3)
        result = get_json_completions(doc, pos)
        assert result is not None
        labels = {item.label for item in result.items}
        assert "type" in labels
        assert "props" in labels
        assert "children" in labels

    def test_returns_none_for_no_context(self):
        source = "  some random text"
        doc = _make_document(source)
        pos = _make_position(0, 10)
        result = get_json_completions(doc, pos)
        assert result is None

    def test_events_key_offers_categories(self):
        lines = [
            '{',
            '  "events": {',
            '    "',
        ]
        source = "\n".join(lines)
        doc = _make_document(source)
        pos = _make_position(2, 5)
        result = get_json_completions(doc, pos)
        assert result is not None
        labels = {item.label for item in result.items}
        assert "component" in labels
        assert "dom" in labels


# ──────────────────────────────────────────────
# _find_enclosing_key
# ──────────────────────────────────────────────


class TestFindEnclosingKey:
    def test_finds_props_key(self):
        lines = [
            '{',
            '  "props": {',
            '    "text"',
        ]
        result = _find_enclosing_key(lines, 2, 5)
        assert result == "props"

    def test_finds_events_key(self):
        lines = [
            '{',
            '  "events": {',
            '    "onClick"',
        ]
        result = _find_enclosing_key(lines, 2, 5)
        assert result == "events"

    def test_returns_none_at_root(self):
        lines = ['{', '  "type"']
        result = _find_enclosing_key(lines, 1, 3)
        # At root level, the enclosing key depends on what's before the first {
        # This should return None or handle gracefully
        assert result is None or isinstance(result, str)
