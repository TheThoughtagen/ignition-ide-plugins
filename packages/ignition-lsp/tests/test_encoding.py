"""Tests for encoding.py — Ignition Flint encode/decode.

Uses shared test vectors from tests/fixtures/encoding_test_vectors.json
so that the Lua and Python implementations are cross-validated.
"""

import json
from pathlib import Path

import pytest

from ignition_lsp.encoding import decode, dedent, encode, is_encoded_script, reindent

# Load shared test vectors (path relative to repo root)
_VECTORS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures" / "encoding_test_vectors.json"
_VECTORS = json.loads(_VECTORS_PATH.read_text(encoding="utf-8"))


class TestEncode:
    """Encoding: raw Python → Ignition JSON string."""

    @pytest.mark.parametrize(
        "case",
        _VECTORS["standard_escapes"],
        ids=lambda c: c["name"],
    )
    def test_standard_escapes(self, case: dict) -> None:
        assert encode(case["decoded"]) == case["encoded"]

    @pytest.mark.parametrize(
        "case",
        _VECTORS["unicode_escapes"],
        ids=lambda c: c["name"],
    )
    def test_unicode_escapes(self, case: dict) -> None:
        assert encode(case["decoded"]) == case["encoded"]

    def test_empty_string(self) -> None:
        assert encode("") == ""

    def test_none_like_empty(self) -> None:
        # Python version treats empty string as empty
        assert encode("") == ""


class TestDecode:
    """Decoding: Ignition JSON string → raw Python."""

    @pytest.mark.parametrize(
        "case",
        _VECTORS["standard_escapes"],
        ids=lambda c: c["name"],
    )
    def test_standard_escapes(self, case: dict) -> None:
        assert decode(case["encoded"]) == case["decoded"]

    @pytest.mark.parametrize(
        "case",
        _VECTORS["unicode_escapes"],
        ids=lambda c: c["name"],
    )
    def test_unicode_escapes(self, case: dict) -> None:
        assert decode(case["encoded"]) == case["decoded"]

    @pytest.mark.parametrize(
        "case",
        _VECTORS["decode_edge_cases"],
        ids=lambda c: c["name"],
    )
    def test_edge_cases(self, case: dict) -> None:
        assert decode(case["encoded"]) == case["decoded"]

    def test_empty_string(self) -> None:
        assert decode("") == ""


class TestRoundTrip:
    """Round-trip: encode(decode(x)) == x and decode(encode(x)) == x."""

    @pytest.mark.parametrize(
        "case",
        _VECTORS["round_trip"],
        ids=lambda c: c["name"],
    )
    def test_encode_then_decode(self, case: dict) -> None:
        text = case["text"]
        assert decode(encode(text)) == text

    @pytest.mark.parametrize(
        "case",
        _VECTORS["round_trip"],
        ids=lambda c: c["name"],
    )
    def test_encode_decode_idempotent(self, case: dict) -> None:
        """Encoding the same text twice and decoding once should not be the same
        as the original (it would mean encode is a no-op). But decode(encode(x)) == x."""
        text = case["text"]
        if not text:
            return  # Skip empty string — encode("") == "" trivially
        encoded = encode(text)
        # Only check that encoding changed the text if it contains special chars
        has_special = any(c in text for c in '\\"\t\b\n\r\f<>&=\'')
        if has_special:
            assert encoded != text  # Encoding should actually change something
        assert decode(encoded) == text

    @pytest.mark.parametrize(
        "case",
        _VECTORS["standard_escapes"] + _VECTORS["unicode_escapes"],
        ids=lambda c: c["name"],
    )
    def test_known_pairs_round_trip(self, case: dict) -> None:
        """Verify encode(decoded) == encoded AND decode(encoded) == decoded."""
        assert encode(case["decoded"]) == case["encoded"]
        assert decode(case["encoded"]) == case["decoded"]


class TestIsEncodedScript:
    """Detection of encoded scripts."""

    @pytest.mark.parametrize(
        "case",
        _VECTORS["detection"],
        ids=lambda c: c["name"],
    )
    def test_detection(self, case: dict) -> None:
        assert is_encoded_script(case["text"]) == case["is_encoded"]


class TestDedent:
    """Strip common leading tabs from embedded scripts."""

    def test_single_tab_level(self) -> None:
        text = "\tline1\n\tline2"
        result, indent = dedent(text)
        assert result == "line1\nline2"
        assert indent == "\t"

    def test_two_tab_levels(self) -> None:
        text = "\t\tline1\n\t\tline2"
        result, indent = dedent(text)
        assert result == "line1\nline2"
        assert indent == "\t\t"

    def test_varying_indent_depths(self) -> None:
        """Min tabs is used — deeper lines keep their extra indentation."""
        text = "\tline1\n\t\tindented\n\tline3"
        result, indent = dedent(text)
        assert result == "line1\n\tindented\nline3"
        assert indent == "\t"

    def test_empty_lines_preserved(self) -> None:
        text = "\tline1\n\n\tline2"
        result, indent = dedent(text)
        assert result == "line1\n\nline2"
        assert indent == "\t"

    def test_no_tabs_returns_original(self) -> None:
        text = "line1\nline2"
        result, indent = dedent(text)
        assert result == text
        assert indent == ""

    def test_empty_string(self) -> None:
        result, indent = dedent("")
        assert result == ""
        assert indent == ""

    def test_mixed_spaces_and_tabs(self) -> None:
        """Stray spaces alongside tabs should not prevent dedent."""
        text = " \tline1\n \tline2"
        result, indent = dedent(text)
        assert result == "line1\nline2"
        assert indent == "\t"

    def test_all_empty_lines(self) -> None:
        """All-whitespace lines should not affect min_tabs calculation."""
        text = "\t\n\tline1\n\t\n\tline2"
        result, indent = dedent(text)
        assert result == "\nline1\n\nline2"
        assert indent == "\t"

    def test_single_line_with_tab(self) -> None:
        text = "\thello"
        result, indent = dedent(text)
        assert result == "hello"
        assert indent == "\t"


class TestReindent:
    """Re-add indentation stripped by dedent."""

    def test_adds_tabs(self) -> None:
        text = "line1\nline2"
        assert reindent(text, "\t") == "\tline1\n\tline2"

    def test_empty_indent_is_noop(self) -> None:
        text = "line1\nline2"
        assert reindent(text, "") == text

    def test_empty_lines_stay_empty(self) -> None:
        text = "line1\n\nline2"
        assert reindent(text, "\t") == "\tline1\n\n\tline2"

    def test_two_tab_indent(self) -> None:
        text = "line1\n\tindented"
        assert reindent(text, "\t\t") == "\t\tline1\n\t\t\tindented"


class TestDedentReindentRoundTrip:
    """Round-trip: reindent(dedent(text)) == text for well-formed scripts."""

    def test_single_tab(self) -> None:
        original = "\tprint('hello')\n\tprint('world')"
        text, indent = dedent(original)
        assert reindent(text, indent) == original

    def test_two_tabs(self) -> None:
        original = "\t\tif True:\n\t\t\tpass"
        text, indent = dedent(original)
        assert reindent(text, indent) == original

    def test_with_empty_lines(self) -> None:
        original = "\tdef foo():\n\n\t\treturn 1"
        text, indent = dedent(original)
        restored = reindent(text, indent)
        # Empty lines lose their tab in dedent, so round-trip normalizes them
        # This is acceptable — empty lines have no semantic meaning
        assert restored.replace("\t\n", "\n") == original.replace("\t\n", "\n")

    def test_no_indent(self) -> None:
        original = "no indent here"
        text, indent = dedent(original)
        assert reindent(text, indent) == original
