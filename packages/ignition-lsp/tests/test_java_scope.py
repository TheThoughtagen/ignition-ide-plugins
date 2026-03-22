"""Tests for Java scope tracking and import detection."""

import pytest
from lsprotocol.types import Position

from ignition_lsp.java_loader import JavaAPILoader
from ignition_lsp.java_scope import (
    JavaContext,
    JavaContextType,
    detect_java_context,
    scan_imports,
)
from tests.conftest import MockTextDocument


@pytest.fixture
def java_loader():
    """Create a real JavaAPILoader from the java_db directory."""
    return JavaAPILoader()


class TestScanImports:
    """Test import statement scanning."""

    def test_from_import_single(self, java_loader):
        """Detect 'from java.lang import String'."""
        doc = MockTextDocument("file:///test.py", "from java.lang import String\n")
        result = scan_imports(doc, java_loader)
        assert "String" in result
        assert result["String"].full_name == "java.lang.String"

    def test_from_import_multiple(self, java_loader):
        """Detect 'from java.lang import String, Integer'."""
        doc = MockTextDocument(
            "file:///test.py",
            "from java.lang import String, Integer\n",
        )
        result = scan_imports(doc, java_loader)
        assert "String" in result
        assert "Integer" in result
        assert result["String"].full_name == "java.lang.String"
        assert result["Integer"].full_name == "java.lang.Integer"

    def test_from_import_with_alias(self, java_loader):
        """Detect 'from java.lang import Exception as JException'."""
        doc = MockTextDocument(
            "file:///test.py",
            "from java.lang import Exception as JException\n",
        )
        result = scan_imports(doc, java_loader)
        assert "JException" in result
        assert result["JException"].full_name == "java.lang.Exception"
        # Original name should NOT be in scope
        assert "Exception" not in result

    def test_import_direct(self, java_loader):
        """Detect 'import java.lang.String'."""
        doc = MockTextDocument("file:///test.py", "import java.lang.String\n")
        result = scan_imports(doc, java_loader)
        assert "String" in result
        assert result["String"].full_name == "java.lang.String"

    def test_import_direct_with_alias(self, java_loader):
        """Detect 'import java.lang.Thread as JThread'."""
        doc = MockTextDocument(
            "file:///test.py",
            "import java.lang.Thread as JThread\n",
        )
        result = scan_imports(doc, java_loader)
        assert "JThread" in result
        assert result["JThread"].full_name == "java.lang.Thread"

    def test_no_java_imports(self, java_loader):
        """Script with no Java imports returns empty dict."""
        doc = MockTextDocument(
            "file:///test.py",
            "import system\nlogger = system.util.getLogger('test')\n",
        )
        result = scan_imports(doc, java_loader)
        assert result == {}

    def test_unknown_class_ignored(self, java_loader):
        """Unknown Java classes are silently skipped."""
        doc = MockTextDocument(
            "file:///test.py",
            "from java.lang import String, FakeClass\n",
        )
        result = scan_imports(doc, java_loader)
        assert "String" in result
        assert "FakeClass" not in result

    def test_multiple_import_lines(self, java_loader):
        """Multiple import lines are all scanned."""
        doc = MockTextDocument(
            "file:///test.py",
            "from java.lang import String\nfrom java.lang import Integer\n",
        )
        result = scan_imports(doc, java_loader)
        assert "String" in result
        assert "Integer" in result

    def test_mixed_imports(self, java_loader):
        """Mix of from-import and direct import."""
        doc = MockTextDocument(
            "file:///test.py",
            "from java.lang import String\nimport java.lang.Integer as JInt\n",
        )
        result = scan_imports(doc, java_loader)
        assert "String" in result
        assert "JInt" in result

    def test_multiple_aliases_on_one_line(self, java_loader):
        """Multiple imports with aliases on one from-import line."""
        doc = MockTextDocument(
            "file:///test.py",
            "from java.lang import String, Exception as JException, Integer\n",
        )
        result = scan_imports(doc, java_loader)
        assert "String" in result
        assert "JException" in result
        assert "Integer" in result
        assert "Exception" not in result


class TestDetectJavaContext:
    """Test completion context detection."""

    def test_import_package_from_java_dot(self, java_loader):
        """'from java.' should detect IMPORT_PACKAGE context."""
        doc = MockTextDocument("file:///test.py", "from java.\n")
        pos = Position(line=0, character=10)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.IMPORT_PACKAGE
        assert ctx.package == "java"

    def test_import_package_partial(self, java_loader):
        """'from java.l' should detect IMPORT_PACKAGE with partial 'l'."""
        doc = MockTextDocument("file:///test.py", "from java.l\n")
        pos = Position(line=0, character=11)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.IMPORT_PACKAGE
        assert ctx.package == "java"
        assert ctx.partial == "l"

    def test_import_class_from_package(self, java_loader):
        """'from java.lang import ' should detect IMPORT_CLASS context."""
        doc = MockTextDocument("file:///test.py", "from java.lang import \n")
        pos = Position(line=0, character=22)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.IMPORT_CLASS
        assert ctx.package == "java.lang"

    def test_import_class_with_partial(self, java_loader):
        """'from java.lang import S' should detect IMPORT_CLASS with partial 'S'."""
        doc = MockTextDocument("file:///test.py", "from java.lang import S\n")
        pos = Position(line=0, character=23)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.IMPORT_CLASS
        assert ctx.partial == "S"

    def test_import_class_after_comma(self, java_loader):
        """'from java.lang import String, ' should detect IMPORT_CLASS."""
        doc = MockTextDocument(
            "file:///test.py", "from java.lang import String, \n"
        )
        pos = Position(line=0, character=30)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.IMPORT_CLASS
        assert ctx.partial == ""

    def test_class_member_context(self, java_loader):
        """'sb.' after importing StringBuilder as sb should detect CLASS_MEMBER."""
        source = "from java.lang import StringBuilder as sb\nsb.\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=3)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.CLASS_MEMBER
        assert ctx.java_class.name == "StringBuilder"

    def test_static_member_context(self, java_loader):
        """'Integer.' should detect STATIC_MEMBER."""
        source = "from java.lang import Integer\nInteger.\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=8)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.STATIC_MEMBER
        assert ctx.java_class.name == "Integer"

    def test_constructor_context(self, java_loader):
        """'StringBuilder(' should detect CONSTRUCTOR."""
        source = "from java.lang import StringBuilder\nx = StringBuilder(\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=18)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.CONSTRUCTOR
        assert ctx.java_class.name == "StringBuilder"

    def test_no_context_plain_code(self, java_loader):
        """Regular Python code should return None."""
        doc = MockTextDocument("file:///test.py", "x = 42\n")
        pos = Position(line=0, character=6)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is None

    def test_no_context_system_api(self, java_loader):
        """system.tag. should not trigger Java context."""
        doc = MockTextDocument("file:///test.py", "system.tag.\n")
        pos = Position(line=0, character=11)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is None

    def test_member_with_partial(self, java_loader):
        """'Integer.par' should detect STATIC_MEMBER with partial 'par'."""
        source = "from java.lang import Integer\nInteger.par\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=11)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.STATIC_MEMBER
        assert ctx.partial == "par"

    def test_no_context_without_import(self, java_loader):
        """'Integer.' without an import should return None."""
        doc = MockTextDocument("file:///test.py", "Integer.\n")
        pos = Position(line=0, character=8)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is None

    def test_import_unknown_package(self, java_loader):
        """'from java.fake import ' should return None (unknown package)."""
        doc = MockTextDocument("file:///test.py", "from java.fake import \n")
        pos = Position(line=0, character=22)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is None


class TestInlineQualifiedContext:
    """Test fully-qualified Java references used directly in code."""

    def test_java_dot_offers_sub_packages(self, java_loader):
        """'java.' in code should offer sub-packages (lang, net, util, ...)."""
        doc = MockTextDocument("file:///test.py", "x = java.\n")
        pos = Position(line=0, character=9)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.IMPORT_PACKAGE
        assert ctx.package == "java"

    def test_java_lang_dot_offers_classes(self, java_loader):
        """'java.lang.' in code should offer classes in java.lang."""
        doc = MockTextDocument("file:///test.py", "x = java.lang.\n")
        pos = Position(line=0, character=14)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.IMPORT_CLASS
        assert ctx.package == "java.lang"

    def test_java_lang_thread_dot_offers_methods(self, java_loader):
        """'java.lang.Thread.' should offer Thread's static methods."""
        doc = MockTextDocument("file:///test.py", "java.lang.Thread.\n")
        pos = Position(line=0, character=17)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.STATIC_MEMBER
        assert ctx.java_class.name == "Thread"

    def test_java_lang_partial_class(self, java_loader):
        """'java.lang.Th' should offer classes with partial 'Th'."""
        doc = MockTextDocument("file:///test.py", "java.lang.Th\n")
        pos = Position(line=0, character=12)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.IMPORT_CLASS
        assert ctx.partial == "Th"

    def test_com_dot_offers_inductiveautomation(self, java_loader):
        """'com.' in code should offer 'inductiveautomation' sub-package."""
        doc = MockTextDocument("file:///test.py", "com.\n")
        pos = Position(line=0, character=4)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.IMPORT_PACKAGE
        assert ctx.package == "com"

    def test_com_inductiveautomation_dot(self, java_loader):
        """'com.inductiveautomation.' should offer sub-packages."""
        doc = MockTextDocument(
            "file:///test.py", "com.inductiveautomation.\n"
        )
        pos = Position(line=0, character=24)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.IMPORT_PACKAGE

    def test_system_dot_not_java(self, java_loader):
        """'system.tag.' should NOT trigger inline Java detection."""
        doc = MockTextDocument("file:///test.py", "system.tag.\n")
        pos = Position(line=0, character=11)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is None

    def test_self_dot_not_java(self, java_loader):
        """'self.value' should NOT trigger inline Java detection."""
        doc = MockTextDocument("file:///test.py", "self.value\n")
        pos = Position(line=0, character=10)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is None

    def test_inline_with_partial_method(self, java_loader):
        """'java.lang.Thread.sle' should offer methods with partial 'sle'."""
        doc = MockTextDocument("file:///test.py", "java.lang.Thread.sle\n")
        pos = Position(line=0, character=20)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.STATIC_MEMBER
        assert ctx.java_class.name == "Thread"
        assert ctx.partial == "sle"

    def test_inline_after_equals(self, java_loader):
        """'x = java.lang.Math.' should work after assignment."""
        doc = MockTextDocument("file:///test.py", "x = java.lang.Math.\n")
        pos = Position(line=0, character=19)
        ctx = detect_java_context(doc, pos, java_loader)
        assert ctx is not None
        assert ctx.type == JavaContextType.STATIC_MEMBER
        assert ctx.java_class.name == "Math"
