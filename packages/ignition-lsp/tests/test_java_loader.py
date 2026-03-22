"""Tests for JavaAPILoader."""

import pytest

from ignition_lsp.java_loader import JavaAPILoader, JavaClass, JavaMethod, JavaField


@pytest.fixture
def java_loader():
    """Create a real JavaAPILoader from the java_db directory."""
    return JavaAPILoader()


class TestJavaAPILoaderLoading:
    """Test that java_db files load correctly."""

    def test_loads_classes(self, java_loader):
        """Loader should find classes from java_lang.json."""
        assert len(java_loader.classes) > 0

    def test_loads_java_lang_string(self, java_loader):
        """String class should be loaded."""
        cls = java_loader.get_class("java.lang.String")
        assert cls is not None
        assert cls.name == "String"
        assert cls.package == "java.lang"
        assert cls.full_name == "java.lang.String"

    def test_loads_java_lang_integer(self, java_loader):
        """Integer class should be loaded."""
        cls = java_loader.get_class("java.lang.Integer")
        assert cls is not None
        assert cls.name == "Integer"

    def test_loads_constructors(self, java_loader):
        """String class should have constructors."""
        cls = java_loader.get_class("java.lang.String")
        assert len(cls.constructors) > 0
        assert cls.constructors[0].name == "String"

    def test_loads_methods(self, java_loader):
        """String class should have instance methods."""
        cls = java_loader.get_class("java.lang.String")
        method_names = [m.name for m in cls.methods]
        assert "length" in method_names
        assert "substring" in method_names
        assert "trim" in method_names

    def test_loads_static_methods(self, java_loader):
        """String class should have static methods separated out."""
        cls = java_loader.get_class("java.lang.String")
        static_names = [m.name for m in cls.static_methods]
        assert "format" in static_names
        assert "valueOf" in static_names

    def test_loads_fields(self, java_loader):
        """Integer class should have fields."""
        cls = java_loader.get_class("java.lang.Integer")
        field_names = [f.name for f in cls.fields]
        assert "MAX_VALUE" in field_names
        assert "MIN_VALUE" in field_names

    def test_field_attributes(self, java_loader):
        """Fields should have correct static/final attributes."""
        cls = java_loader.get_class("java.lang.Integer")
        max_val = next(f for f in cls.fields if f.name == "MAX_VALUE")
        assert max_val.static is True
        assert max_val.final is True

    def test_loads_math_static_only(self, java_loader):
        """Math class should have all static methods."""
        cls = java_loader.get_class("java.lang.Math")
        assert len(cls.static_methods) > 0
        # Math has no constructors
        assert len(cls.constructors) == 0

    def test_loads_docs_url(self, java_loader):
        """Classes should have docs_url populated."""
        cls = java_loader.get_class("java.lang.String")
        assert cls.docs_url.startswith("https://docs.oracle.com")


class TestJavaAPILoaderIndexes:
    """Test the various lookup indexes."""

    def test_package_listing(self, java_loader):
        """get_package_classes should return classes in a package."""
        classes = java_loader.get_package_classes("java.lang")
        assert len(classes) > 0
        names = [c.name for c in classes]
        assert "String" in names
        assert "Integer" in names

    def test_all_packages(self, java_loader):
        """get_all_packages should return loaded packages."""
        packages = java_loader.get_all_packages()
        assert "java.lang" in packages

    def test_short_name_lookup(self, java_loader):
        """find_by_short_name should return matching classes."""
        results = java_loader.find_by_short_name("String")
        assert len(results) >= 1
        assert results[0].full_name == "java.lang.String"

    def test_short_name_not_found(self, java_loader):
        """find_by_short_name should return empty list for unknown names."""
        results = java_loader.find_by_short_name("NonExistentClass")
        assert results == []

    def test_get_class_not_found(self, java_loader):
        """get_class should return None for unknown classes."""
        assert java_loader.get_class("com.example.Foo") is None

    def test_get_package_classes_not_found(self, java_loader):
        """get_package_classes should return empty list for unknown packages."""
        assert java_loader.get_package_classes("com.example") == []

    def test_sub_packages(self, java_loader):
        """get_sub_packages should return child segments."""
        subs = java_loader.get_sub_packages("java")
        assert "lang" in subs


class TestJavaClassMarkdown:
    """Test Markdown documentation generation."""

    def test_class_markdown(self, java_loader):
        """get_markdown_doc should produce formatted class documentation."""
        cls = java_loader.get_class("java.lang.String")
        md = cls.get_markdown_doc()
        assert "**java.lang.String**" in md
        assert "class String" in md
        assert "Constructors:" in md
        assert "Methods:" in md
        assert "Documentation" in md

    def test_method_markdown(self, java_loader):
        """get_method_markdown should produce method documentation."""
        cls = java_loader.get_class("java.lang.String")
        md = cls.get_method_markdown("substring")
        assert md is not None
        assert "String.substring" in md
        assert "beginIndex" in md

    def test_method_markdown_not_found(self, java_loader):
        """get_method_markdown returns None for unknown methods."""
        cls = java_loader.get_class("java.lang.String")
        assert cls.get_method_markdown("nonExistentMethod") is None

    def test_field_markdown(self, java_loader):
        """get_field_markdown should produce field documentation."""
        cls = java_loader.get_class("java.lang.Integer")
        md = cls.get_field_markdown("MAX_VALUE")
        assert md is not None
        assert "MAX_VALUE" in md
        assert "int" in md

    def test_field_markdown_not_found(self, java_loader):
        """get_field_markdown returns None for unknown fields."""
        cls = java_loader.get_class("java.lang.Integer")
        assert cls.get_field_markdown("NO_SUCH_FIELD") is None

    def test_static_method_markdown(self, java_loader):
        """Static methods should be found by get_method_markdown."""
        cls = java_loader.get_class("java.lang.Integer")
        md = cls.get_method_markdown("parseInt")
        assert md is not None
        assert "parseInt" in md


class TestJavaMethodSnippet:
    """Test completion snippet generation."""

    def test_method_snippet_with_params(self):
        """Methods with params should generate placeholder snippets."""
        m = JavaMethod(
            name="substring",
            signature="substring(beginIndex, endIndex)",
            params=[
                {"name": "beginIndex", "type": "int", "description": "start"},
                {"name": "endIndex", "type": "int", "description": "end"},
            ],
            returns={"type": "String", "description": ""},
            description="test",
        )
        assert m.get_completion_snippet() == "substring(${1:beginIndex}, ${2:endIndex})$0"

    def test_method_snippet_no_params(self):
        """Methods without params should generate empty parens."""
        m = JavaMethod(
            name="length",
            signature="length()",
            params=[],
            returns={"type": "int", "description": ""},
            description="test",
        )
        assert m.get_completion_snippet() == "length()$0"


class TestGracefulDegradation:
    """Test that missing/empty java_db is handled gracefully."""

    def test_empty_loader(self):
        """JavaAPILoader with empty indexes should still work."""
        loader = JavaAPILoader.__new__(JavaAPILoader)
        loader.classes = {}
        loader.packages = {}
        loader.short_names = {}
        # Should not crash
        assert loader.get_class("java.lang.String") is None
        assert loader.get_package_classes("java.lang") == []
        assert loader.get_all_packages() == []
        assert loader.find_by_short_name("String") == []
        assert loader.get_sub_packages("java") == []
