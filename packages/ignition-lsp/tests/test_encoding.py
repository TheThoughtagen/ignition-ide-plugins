"""Tests for encoding.py — Ignition Flint encode/decode.

Uses shared test vectors from tests/fixtures/encoding_test_vectors.json
so that the Lua and Python implementations are cross-validated.
"""

import json
from pathlib import Path

import pytest

from ignition_lsp.encoding import decode, encode, is_encoded_script

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
