"""Tests for PylibLoader."""

import pytest

from ignition_lsp.pylib_loader import PylibLoader, PyFunction, PyClass, PyField, PyModule, PyConstant


@pytest.fixture
def pylib_loader():
    """Create a real PylibLoader from the pylib_db directory."""
    return PylibLoader()


class TestPylibLoaderLoading:
    """Test that pylib_db files load correctly."""

    def test_loads_modules(self, pylib_loader):
        """Loader should find modules from pylib_db."""
        assert len(pylib_loader.modules) > 0

    def test_loads_json_module(self, pylib_loader):
        """json module should be loaded."""
        module = pylib_loader.get_module("json")
        assert module is not None
        assert module.name == "json"

    def test_loads_re_module(self, pylib_loader):
        """re module should be loaded."""
        module = pylib_loader.get_module("re")
        assert module is not None
        assert module.name == "re"

    def test_loads_datetime_module(self, pylib_loader):
        """datetime module should be loaded."""
        module = pylib_loader.get_module("datetime")
        assert module is not None

    def test_loads_collections_module(self, pylib_loader):
        """collections module should be loaded."""
        module = pylib_loader.get_module("collections")
        assert module is not None

    def test_loads_builtins(self, pylib_loader):
        """__builtin__ module should be loaded and set as builtins."""
        assert pylib_loader.builtins is not None
        assert pylib_loader.builtins.name == "__builtin__"

    def test_json_has_functions(self, pylib_loader):
        """json module should have functions like loads and dumps."""
        module = pylib_loader.get_module("json")
        func_names = [f.name for f in module.functions]
        assert "loads" in func_names
        assert "dumps" in func_names

    def test_json_has_classes(self, pylib_loader):
        """json module should have classes like JSONEncoder."""
        module = pylib_loader.get_module("json")
        class_names = [c.name for c in module.classes]
        assert "JSONEncoder" in class_names

    def test_re_has_constants(self, pylib_loader):
        """re module should have constants like IGNORECASE."""
        module = pylib_loader.get_module("re")
        const_names = [c.name for c in module.constants]
        assert "IGNORECASE" in const_names or "I" in const_names

    def test_loads_docs_url(self, pylib_loader):
        """Modules should have docs_url populated."""
        module = pylib_loader.get_module("json")
        assert module.docs_url.startswith("https://docs.python.org")

    def test_function_has_params(self, pylib_loader):
        """Functions should have parameter information."""
        func = pylib_loader.get_function("json.loads")
        assert func is not None
        assert len(func.params) > 0
        assert func.params[0]["name"] == "s"

    def test_function_has_returns(self, pylib_loader):
        """Functions should have return type information."""
        func = pylib_loader.get_function("json.loads")
        assert func is not None
        assert func.returns.get("type") is not None


class TestPylibLoaderIndexes:
    """Test the various lookup indexes."""

    def test_get_all_module_names(self, pylib_loader):
        """get_all_module_names should return loaded module names."""
        names = pylib_loader.get_all_module_names()
        assert "json" in names
        assert "re" in names
        assert "math" in names

    def test_get_function_by_full_name(self, pylib_loader):
        """get_function should find by full name like 'json.loads'."""
        func = pylib_loader.get_function("json.loads")
        assert func is not None
        assert func.name == "loads"

    def test_get_function_not_found(self, pylib_loader):
        """get_function should return None for unknown functions."""
        assert pylib_loader.get_function("json.nonexistent") is None

    def test_get_module_not_found(self, pylib_loader):
        """get_module should return None for unknown modules."""
        assert pylib_loader.get_module("nonexistent_module") is None

    def test_search_functions(self, pylib_loader):
        """search_functions should find matching functions."""
        results = pylib_loader.search_functions("json.l")
        names = [f.name for f in results]
        assert "loads" in names or "load" in names

    def test_search_functions_empty(self, pylib_loader):
        """search_functions should return empty for no matches."""
        results = pylib_loader.search_functions("zzzzz.zzzzz")
        assert results == []

    def test_class_methods_indexed(self, pylib_loader):
        """Class methods should be indexed as module.Class.method."""
        func = pylib_loader.get_function("json.JSONEncoder.encode")
        assert func is not None
        assert func.name == "encode"


class TestPyFunctionSnippet:
    """Test completion snippet generation."""

    def test_snippet_with_params(self):
        """Functions with params should generate placeholder snippets."""
        f = PyFunction(
            name="loads",
            signature="loads(s, encoding=None)",
            params=[
                {"name": "s", "type": "str", "description": "JSON string"},
                {"name": "encoding", "type": "str", "description": "Encoding"},
            ],
            returns={"type": "object", "description": ""},
            description="test",
        )
        assert f.get_completion_snippet() == "loads(${1:s}, ${2:encoding})$0"

    def test_snippet_no_params(self):
        """Functions without params should generate empty parens."""
        f = PyFunction(
            name="random",
            signature="random()",
            params=[],
            returns={"type": "float", "description": ""},
            description="test",
        )
        assert f.get_completion_snippet() == "random()$0"


class TestPyFunctionMarkdown:
    """Test Markdown documentation generation."""

    def test_function_markdown(self, pylib_loader):
        """get_markdown_doc should produce formatted documentation."""
        func = pylib_loader.get_function("json.loads")
        md = func.get_markdown_doc("json")
        assert "json.loads" in md
        assert "Parameters:" in md

    def test_deprecated_function_markdown(self):
        """Deprecated functions should show deprecation notice."""
        f = PyFunction(
            name="old_func",
            signature="old_func()",
            params=[],
            returns={},
            description="Old function.",
            deprecated=True,
        )
        md = f.get_markdown_doc()
        assert "DEPRECATED" in md


class TestPyClassMarkdown:
    """Test class documentation generation."""

    def test_class_markdown(self, pylib_loader):
        """get_markdown_doc should produce formatted class documentation."""
        module = pylib_loader.get_module("json")
        encoder = None
        for cls in module.classes:
            if cls.name == "JSONEncoder":
                encoder = cls
                break
        assert encoder is not None
        md = encoder.get_markdown_doc("json")
        assert "json.JSONEncoder" in md
        assert "class JSONEncoder" in md

    def test_method_markdown(self, pylib_loader):
        """get_method_markdown should produce method documentation."""
        module = pylib_loader.get_module("json")
        encoder = None
        for cls in module.classes:
            if cls.name == "JSONEncoder":
                encoder = cls
                break
        md = encoder.get_method_markdown("encode", "json")
        assert md is not None
        assert "encode" in md

    def test_method_markdown_not_found(self, pylib_loader):
        """get_method_markdown returns None for unknown methods."""
        module = pylib_loader.get_module("json")
        encoder = module.classes[0]
        assert encoder.get_method_markdown("nonExistent") is None


class TestPyModuleMarkdown:
    """Test module documentation generation."""

    def test_module_markdown(self, pylib_loader):
        """get_markdown_doc should produce formatted module documentation."""
        module = pylib_loader.get_module("json")
        md = module.get_markdown_doc()
        assert "**json**" in md
        assert "Functions:" in md
        assert "Documentation" in md


class TestGracefulDegradation:
    """Test that missing/empty pylib_db is handled gracefully."""

    def test_empty_loader(self):
        """PylibLoader with empty indexes should still work."""
        loader = PylibLoader.__new__(PylibLoader)
        loader.modules = {}
        loader.all_functions = {}
        loader.builtins = None
        # Should not crash
        assert loader.get_module("json") is None
        assert loader.get_function("json.loads") is None
        assert loader.get_all_module_names() == []
        assert loader.search_functions("json") == []
