"""Tests for api_loader.py — loading, indexing, search, version filtering."""

import json
import tempfile
from pathlib import Path

import pytest

from ignition_lsp.api_loader import APIFunction, IgnitionAPILoader


# ── APIFunction Tests ─────────────────────────────────────────────────


class TestAPIFunction:
    """Tests for the APIFunction data class."""

    @pytest.fixture
    def sample_func_data(self):
        return {
            "name": "readBlocking",
            "signature": "readBlocking(tagPaths)",
            "description": "Reads values from tags synchronously.",
            "long_description": "Reads from one or more tags at the current time.",
            "params": [
                {
                    "name": "tagPaths",
                    "type": "List[String]",
                    "description": "List of tag paths to read",
                }
            ],
            "returns": {"type": "List[QualifiedValue]", "description": "List of qualified values"},
            "scope": ["Gateway", "Vision", "Perspective"],
            "deprecated": False,
            "since": "8.0",
            "docs_url": "https://docs.inductiveautomation.com/docs/8.1/system-tag-readBlocking",
            "examples": ["tags = system.tag.readBlocking(['[default]MyTag'])"],
        }

    def test_basic_attributes(self, sample_func_data):
        func = APIFunction(sample_func_data, "system.tag")

        assert func.name == "readBlocking"
        assert func.module == "system.tag"
        assert func.full_name == "system.tag.readBlocking"
        assert func.signature == "readBlocking(tagPaths)"
        assert func.description == "Reads values from tags synchronously."
        assert func.deprecated is False
        assert func.since == "8.0"

    def test_full_name_format(self, sample_func_data):
        func = APIFunction(sample_func_data, "system.tag")
        assert func.full_name == "system.tag.readBlocking"

    def test_optional_fields_default(self):
        """Minimal function data should use sensible defaults."""
        data = {
            "name": "myFunc",
            "signature": "myFunc()",
            "description": "A function.",
        }
        func = APIFunction(data, "system.test")

        assert func.params == []
        assert func.returns == {}
        assert func.long_description == ""
        assert func.scope == []
        assert func.deprecated is False
        assert func.since == "8.0"
        assert func.docs_url == ""
        assert func.examples == []

    def test_get_markdown_doc_contains_key_sections(self, sample_func_data):
        func = APIFunction(sample_func_data, "system.tag")
        doc = func.get_markdown_doc()

        assert "**system.tag.readBlocking**" in doc
        assert "```python" in doc
        assert "readBlocking(tagPaths)" in doc
        assert "List[QualifiedValue]" in doc
        assert "Reads values from tags synchronously." in doc
        assert "**Parameters:**" in doc
        assert "`tagPaths`" in doc
        assert "**Returns:**" in doc
        assert "**Scope:**" in doc
        assert "Gateway" in doc
        assert "[Documentation]" in doc

    def test_get_markdown_doc_long_description(self, sample_func_data):
        func = APIFunction(sample_func_data, "system.tag")
        doc = func.get_markdown_doc()
        assert "Reads from one or more tags at the current time." in doc

    def test_get_markdown_doc_no_params(self):
        data = {
            "name": "now",
            "signature": "now()",
            "description": "Returns current time.",
        }
        func = APIFunction(data, "system.date")
        doc = func.get_markdown_doc()

        assert "**Parameters:**" not in doc

    def test_format_params_required(self, sample_func_data):
        func = APIFunction(sample_func_data, "system.tag")
        assert func._format_params() == "tagPaths"

    def test_format_params_optional(self):
        data = {
            "name": "jsonEncode",
            "signature": "jsonEncode(pyObject, indentFactor=4)",
            "description": "Encodes object as JSON.",
            "params": [
                {"name": "pyObject", "type": "Object", "description": "Object to encode"},
                {
                    "name": "indentFactor",
                    "type": "int",
                    "description": "Indent",
                    "optional": True,
                    "default": "4",
                },
            ],
        }
        func = APIFunction(data, "system.util")
        assert func._format_params() == "pyObject, indentFactor=4"

    def test_get_completion_snippet_with_params(self, sample_func_data):
        func = APIFunction(sample_func_data, "system.tag")
        snippet = func.get_completion_snippet()
        assert snippet == "readBlocking(${1:tagPaths})$0"

    def test_get_completion_snippet_no_params(self):
        data = {
            "name": "now",
            "signature": "now()",
            "description": "Returns current time.",
        }
        func = APIFunction(data, "system.date")
        assert func.get_completion_snippet() == "now()$0"

    def test_get_completion_snippet_skips_optional(self):
        data = {
            "name": "func",
            "signature": "func(a, b=None)",
            "description": "Test.",
            "params": [
                {"name": "a", "type": "str", "description": "Required"},
                {"name": "b", "type": "str", "description": "Optional", "optional": True},
            ],
        }
        func = APIFunction(data, "system.test")
        snippet = func.get_completion_snippet()
        assert snippet == "func(${1:a})$0"

    def test_deprecated_function(self):
        data = {
            "name": "oldFunc",
            "signature": "oldFunc()",
            "description": "Deprecated function.",
            "deprecated": True,
        }
        func = APIFunction(data, "system.test")
        assert func.deprecated is True


# ── IgnitionAPILoader Tests ───────────────────────────────────────────


class TestIgnitionAPILoader:
    """Tests for the IgnitionAPILoader class."""

    def test_loads_from_api_db(self, api_loader):
        """Loader should find and load the real api_db files."""
        assert len(api_loader.api_db) > 0
        assert len(api_loader.modules) > 0

    def test_known_modules_loaded(self, api_loader):
        """The 4 existing module files should all be loaded."""
        modules = api_loader.get_all_modules()
        assert "system.tag" in modules
        assert "system.db" in modules
        assert "system.perspective" in modules
        assert "system.util" in modules

    def test_get_function_exists(self, api_loader):
        func = api_loader.get_function("system.tag.readBlocking")
        assert func is not None
        assert func.name == "readBlocking"
        assert func.module == "system.tag"

    def test_get_function_not_found(self, api_loader):
        assert api_loader.get_function("system.fake.nonExistent") is None

    def test_get_module_functions(self, api_loader):
        funcs = api_loader.get_module_functions("system.tag")
        assert len(funcs) > 0
        assert all(f.module == "system.tag" for f in funcs)

    def test_get_module_functions_empty(self, api_loader):
        funcs = api_loader.get_module_functions("system.nonexistent")
        assert funcs == []

    def test_get_all_modules_returns_list(self, api_loader):
        modules = api_loader.get_all_modules()
        assert isinstance(modules, list)
        assert len(modules) >= 4  # at minimum: tag, db, perspective, util

    def test_search_functions_by_prefix(self, api_loader):
        results = api_loader.search_functions("system.tag.")
        assert len(results) > 0
        assert all(f.full_name.startswith("system.tag.") for f in results)

    def test_search_functions_no_match(self, api_loader):
        results = api_loader.search_functions("system.nonexistent.")
        assert results == []

    def test_get_module_from_prefix(self, api_loader):
        assert api_loader.get_module_from_prefix("system.tag.") == "system.tag"
        assert api_loader.get_module_from_prefix("system.tag") == "system.tag"
        assert api_loader.get_module_from_prefix("system.db.") == "system.db"

    def test_get_module_from_prefix_not_found(self, api_loader):
        assert api_loader.get_module_from_prefix("system.nonexistent.") is None
        assert api_loader.get_module_from_prefix("foo") is None

    def test_version_filtering_compatible(self):
        """Version 8.1 should load 8.0+ and 8.1+ modules."""
        loader = IgnitionAPILoader(version="8.1")
        assert len(loader.modules) > 0

    def test_version_filtering_incompatible(self):
        """Version 7.0 should skip modules requiring 8.0+."""
        loader = IgnitionAPILoader(version="7.0")
        # All our modules require 8.0+ or 8.1+, so nothing should load
        assert len(loader.modules) == 0

    def test_is_compatible_version(self, api_loader):
        assert api_loader._is_compatible_version("8.0+") is True
        assert api_loader._is_compatible_version("8.1+") is True
        assert api_loader._is_compatible_version("8.0") is True
        assert api_loader._is_compatible_version("9.0") is False

    def test_is_compatible_version_malformed(self, api_loader):
        """Malformed versions should be treated as compatible (fail open)."""
        assert api_loader._is_compatible_version("abc") is True

    def test_functions_have_required_fields(self, api_loader):
        """Every loaded function should have the required fields."""
        for full_name, func in api_loader.api_db.items():
            assert func.name, f"{full_name} missing name"
            assert func.module, f"{full_name} missing module"
            assert func.signature, f"{full_name} missing signature"
            assert func.description, f"{full_name} missing description"
            assert func.full_name == f"{func.module}.{func.name}"
