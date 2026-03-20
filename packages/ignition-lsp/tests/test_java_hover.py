"""Tests for Java hover integration."""

import pytest
from lsprotocol.types import Position

from ignition_lsp.api_loader import IgnitionAPILoader
from ignition_lsp.hover import get_hover_info
from ignition_lsp.java_loader import JavaAPILoader
from tests.conftest import MockTextDocument


@pytest.fixture
def api_loader():
    return IgnitionAPILoader(version="8.1")


@pytest.fixture
def java_loader():
    return JavaAPILoader()


class TestJavaClassHover:
    """Test hovering on imported class names."""

    def test_hover_imported_class(self, api_loader, java_loader):
        """Hovering on 'String' after import should show class docs."""
        source = "from java.lang import String\nx = String\n"
        doc = MockTextDocument("file:///test.py", source)
        # Hover on "String" in "x = String" (line 1, character 4-10)
        pos = Position(line=1, character=6)
        result = get_hover_info(doc, pos, api_loader, java_loader)
        assert result is not None
        assert "java.lang.String" in result.contents.value
        assert "class String" in result.contents.value

    def test_hover_class_shows_constructors(self, api_loader, java_loader):
        """Class hover should include constructor information."""
        source = "from java.lang import StringBuilder\nx = StringBuilder\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=8)
        result = get_hover_info(doc, pos, api_loader, java_loader)
        assert result is not None
        assert "Constructors:" in result.contents.value

    def test_hover_class_shows_methods(self, api_loader, java_loader):
        """Class hover should include method list."""
        source = "from java.lang import String\nx = String\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=6)
        result = get_hover_info(doc, pos, api_loader, java_loader)
        assert result is not None
        assert "Methods:" in result.contents.value

    def test_hover_unimported_class_returns_none(self, api_loader, java_loader):
        """Hovering on 'String' without import should fall through."""
        source = "x = String\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=0, character=6)
        result = get_hover_info(doc, pos, api_loader, java_loader)
        # Should return None since String is not imported
        assert result is None


class TestJavaMethodHover:
    """Test hovering on class.method expressions."""

    def test_hover_instance_method(self, api_loader, java_loader):
        """Hovering on 'String.substring' should show method docs."""
        source = "from java.lang import String\nString.substring\n"
        doc = MockTextDocument("file:///test.py", source)
        # Hover on "substring" part of "String.substring"
        pos = Position(line=1, character=10)
        result = get_hover_info(doc, pos, api_loader, java_loader)
        assert result is not None
        assert "substring" in result.contents.value
        assert "beginIndex" in result.contents.value

    def test_hover_static_method(self, api_loader, java_loader):
        """Hovering on 'Integer.parseInt' should show method docs."""
        source = "from java.lang import Integer\nInteger.parseInt\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=12)
        result = get_hover_info(doc, pos, api_loader, java_loader)
        assert result is not None
        assert "parseInt" in result.contents.value

    def test_hover_field(self, api_loader, java_loader):
        """Hovering on 'Integer.MAX_VALUE' should show field docs."""
        source = "from java.lang import Integer\nInteger.MAX_VALUE\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=12)
        result = get_hover_info(doc, pos, api_loader, java_loader)
        assert result is not None
        assert "MAX_VALUE" in result.contents.value


class TestJavaPackageHover:
    """Test hovering on package names in import statements."""

    def test_hover_package_in_import(self, api_loader, java_loader):
        """Hovering on 'java.lang' in an import should show package info."""
        source = "from java.lang import String\n"
        doc = MockTextDocument("file:///test.py", source)
        # Hover on "java.lang" (the whole identifier)
        pos = Position(line=0, character=7)
        result = get_hover_info(doc, pos, api_loader, java_loader)
        assert result is not None
        assert "java.lang" in result.contents.value
        assert "Java package" in result.contents.value


class TestJavaHoverWithoutLoader:
    """Test that hover works normally when java_loader is None."""

    def test_system_hover_still_works(self, api_loader):
        """system.* hover should work when java_loader is None."""
        source = "system.tag.readBlocking\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=0, character=15)
        result = get_hover_info(doc, pos, api_loader, None)
        assert result is not None
        assert "readBlocking" in result.contents.value

    def test_system_hover_with_java_loader(self, api_loader, java_loader):
        """system.* hover should still work when java_loader is present."""
        source = "system.tag.readBlocking\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=0, character=15)
        result = get_hover_info(doc, pos, api_loader, java_loader)
        assert result is not None
        assert "readBlocking" in result.contents.value
