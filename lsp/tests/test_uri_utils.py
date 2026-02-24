"""Tests for uri_utils — virtual buffer URI classification."""

import pytest

from ignition_lsp.uri_utils import is_expression_buffer, is_virtual_buffer


# ── is_virtual_buffer ────────────────────────────────────────────────


class TestIsVirtualBuffer:
    def test_python_script_buffer(self):
        uri = "[Ignition:resource.json:eventScript:L42]"
        assert is_virtual_buffer(uri) is True

    def test_expression_buffer(self):
        uri = "[Ignition:tags.json:MyTag/Expression:L10]"
        assert is_virtual_buffer(uri) is True

    def test_regular_file(self):
        assert is_virtual_buffer("file:///home/user/code.py") is False

    def test_empty_string(self):
        assert is_virtual_buffer("") is False


# ── is_expression_buffer ─────────────────────────────────────────────


class TestIsExpressionBuffer:
    """Cover both URI forms produced by virtual_doc.lua."""

    def test_context_variant_with_line(self):
        """[Ignition:tags.json:MyTag/Expression:L42] — context present."""
        uri = "[Ignition:tags.json:MyTag/Expression:L42]"
        assert is_expression_buffer(uri) is True

    def test_plain_key_variant_with_line(self):
        """[Ignition:tags.json:expression:L42] — no context, lowercase key."""
        uri = "[Ignition:tags.json:expression:L42]"
        assert is_expression_buffer(uri) is True

    def test_case_insensitive_mixed(self):
        """Mixed case should still match."""
        uri = "[Ignition:tags.json:EXPRESSION:L1]"
        assert is_expression_buffer(uri) is True

    def test_nested_context_path(self):
        """Deeper context like Folder/Tag/Expression."""
        uri = "[Ignition:tags.json:Folder/Tag/Expression:L5]"
        assert is_expression_buffer(uri) is True

    def test_python_script_not_expression(self):
        """eventScript buffers must NOT match."""
        uri = "[Ignition:resource.json:eventScript:L42]"
        assert is_expression_buffer(uri) is False

    def test_regular_file_not_expression(self):
        assert is_expression_buffer("file:///home/user/code.py") is False

    def test_empty_string(self):
        assert is_expression_buffer("") is False

    def test_file_uri_prefix(self):
        """URIs may be wrapped in file:/// prefix by some LSP clients."""
        uri = "file:///[Ignition:tags.json:expression:L10]"
        assert is_expression_buffer(uri) is True
