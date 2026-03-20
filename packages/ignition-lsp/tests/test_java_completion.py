"""Tests for Java completion integration."""

import pytest
from lsprotocol.types import CompletionItemKind, Position

from ignition_lsp.api_loader import IgnitionAPILoader
from ignition_lsp.completion import get_completions
from ignition_lsp.java_loader import JavaAPILoader
from tests.conftest import MockTextDocument


@pytest.fixture
def api_loader():
    return IgnitionAPILoader(version="8.1")


@pytest.fixture
def java_loader():
    return JavaAPILoader()


class TestJavaImportPackageCompletions:
    """Test completions for 'from java.' style imports."""

    def test_from_java_dot(self, api_loader, java_loader):
        """'from java.' should offer sub-packages like 'lang'."""
        doc = MockTextDocument("file:///test.py", "from java.\n")
        pos = Position(line=0, character=10)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        labels = [item.label for item in result.items]
        assert "lang" in labels

    def test_from_java_partial(self, api_loader, java_loader):
        """'from java.l' should filter to 'lang'."""
        doc = MockTextDocument("file:///test.py", "from java.l\n")
        pos = Position(line=0, character=11)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        labels = [item.label for item in result.items]
        assert "lang" in labels

    def test_package_items_are_modules(self, api_loader, java_loader):
        """Package completions should have Module kind."""
        doc = MockTextDocument("file:///test.py", "from java.\n")
        pos = Position(line=0, character=10)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        for item in result.items:
            assert item.kind == CompletionItemKind.Module


class TestJavaImportClassCompletions:
    """Test completions for 'from java.lang import ' style imports."""

    def test_import_class_list(self, api_loader, java_loader):
        """'from java.lang import ' should offer classes like String, Integer."""
        doc = MockTextDocument("file:///test.py", "from java.lang import \n")
        pos = Position(line=0, character=22)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        labels = [item.label for item in result.items]
        assert "String" in labels
        assert "Integer" in labels
        assert "Math" in labels

    def test_import_class_partial(self, api_loader, java_loader):
        """'from java.lang import S' should filter to String, StringBuilder, System."""
        doc = MockTextDocument("file:///test.py", "from java.lang import S\n")
        pos = Position(line=0, character=23)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        labels = [item.label for item in result.items]
        assert "String" in labels
        assert "StringBuilder" in labels
        assert "System" in labels
        assert "Integer" not in labels

    def test_import_class_items_are_class_kind(self, api_loader, java_loader):
        """Class import completions should have Class kind."""
        doc = MockTextDocument("file:///test.py", "from java.lang import \n")
        pos = Position(line=0, character=22)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        for item in result.items:
            assert item.kind == CompletionItemKind.Class

    def test_import_after_comma(self, api_loader, java_loader):
        """'from java.lang import String, I' should offer Integer."""
        doc = MockTextDocument("file:///test.py", "from java.lang import String, I\n")
        pos = Position(line=0, character=31)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        labels = [item.label for item in result.items]
        assert "Integer" in labels


class TestJavaClassMemberCompletions:
    """Test completions for class member access (e.g., 'url.openConnection')."""

    def test_static_member_access(self, api_loader, java_loader):
        """'Integer.' should offer static methods like parseInt and fields like MAX_VALUE."""
        source = "from java.lang import Integer\nInteger.\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=8)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        labels = [item.label for item in result.items]
        assert "parseInt" in labels
        assert "MAX_VALUE" in labels

    def test_instance_member_access(self, api_loader, java_loader):
        """'sb.' (aliased StringBuilder) should offer instance methods."""
        source = "from java.lang import StringBuilder as sb\nsb.\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=3)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        labels = [item.label for item in result.items]
        assert "append" in labels
        assert "toString" in labels
        assert "length" in labels

    def test_member_with_partial(self, api_loader, java_loader):
        """'Integer.par' should filter to parseInt."""
        source = "from java.lang import Integer\nInteger.par\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=11)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        labels = [item.label for item in result.items]
        assert "parseInt" in labels
        assert "MAX_VALUE" not in labels

    def test_static_fields_have_field_kind(self, api_loader, java_loader):
        """Static fields should have Field kind."""
        source = "from java.lang import Integer\nInteger.\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=8)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        field_items = [item for item in result.items if item.label == "MAX_VALUE"]
        assert len(field_items) == 1
        assert field_items[0].kind == CompletionItemKind.Field


class TestJavaConstructorCompletions:
    """Test completions for constructor calls."""

    def test_constructor_completions(self, api_loader, java_loader):
        """'StringBuilder(' should offer constructor signatures."""
        source = "from java.lang import StringBuilder\nx = StringBuilder(\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=18)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        assert len(result.items) > 0
        labels = [item.label for item in result.items]
        assert any("StringBuilder" in l for l in labels)

    def test_constructor_items_are_constructor_kind(self, api_loader, java_loader):
        """Constructor completions should have Constructor kind."""
        source = "from java.lang import StringBuilder\nx = StringBuilder(\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=18)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        for item in result.items:
            assert item.kind == CompletionItemKind.Constructor


class TestJavaCompletionWithoutLoader:
    """Test that completion works normally when java_loader is None."""

    def test_system_completions_still_work(self, api_loader):
        """system.* completions should work when java_loader is None."""
        doc = MockTextDocument("file:///test.py", "system.\n")
        pos = Position(line=0, character=7)
        result = get_completions(doc, pos, api_loader, None, None)
        labels = [item.label for item in result.items]
        assert "tag" in labels

    def test_no_java_in_plain_code(self, api_loader, java_loader):
        """Regular code should still get system.* completions, not Java ones."""
        doc = MockTextDocument("file:///test.py", "system.\n")
        pos = Position(line=0, character=7)
        result = get_completions(doc, pos, api_loader, None, java_loader)
        labels = [item.label for item in result.items]
        assert "tag" in labels
