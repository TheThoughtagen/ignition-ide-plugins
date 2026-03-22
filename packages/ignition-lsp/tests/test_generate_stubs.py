"""Tests for generate_stubs.py — system.* API stub generation."""

import json
import tempfile
from pathlib import Path

import pytest

from ignition_lsp.generate_stubs import _convert_type, _generate_module_stub


class TestConvertType:
    """Test Ignition type → Python type conversion."""

    def test_string(self):
        assert _convert_type("String") == "str"

    def test_string_lowercase(self):
        assert _convert_type("string") == "str"

    def test_int(self):
        assert _convert_type("int") == "int"

    def test_integer(self):
        assert _convert_type("Integer") == "int"

    def test_boolean(self):
        assert _convert_type("boolean") == "bool"

    def test_float(self):
        assert _convert_type("float") == "float"

    def test_double(self):
        assert _convert_type("Double") == "float"

    def test_void(self):
        assert _convert_type("void") == "None"

    def test_object(self):
        assert _convert_type("Object") == "Any"

    def test_empty_returns_any(self):
        assert _convert_type("") == "Any"

    def test_list_of_string(self):
        assert _convert_type("List[String]") == "list[str]"

    def test_list_of_int(self):
        assert _convert_type("List[int]") == "list[int]"

    def test_bare_list(self):
        assert _convert_type("List") == "list[Any]"

    def test_union_type(self):
        result = _convert_type("String | List[String]")
        assert result == "str | list[str]"

    def test_unknown_type_passthrough(self):
        assert _convert_type("CustomWidget") == "CustomWidget"

    def test_dataset(self):
        assert _convert_type("Dataset") == "Any"

    def test_callable(self):
        assert _convert_type("Function") == "Callable[..., Any]"


class TestGenerateModuleStub:
    """Test stub file generation from API JSON."""

    def _make_api_file(self, data: dict) -> Path:
        """Write API data to a temp file and return its path."""
        path = Path(tempfile.mktemp(suffix=".json"))
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_basic_function(self):
        data = {
            "module": "system.util",
            "functions": [
                {
                    "name": "getGatewayAddress",
                    "description": "Returns the gateway address.",
                    "params": [],
                    "returns": {"type": "String"},
                }
            ],
        }
        path = self._make_api_file(data)
        module, submodule, content = _generate_module_stub(path)
        path.unlink()

        assert module == "system.util"
        assert submodule == "util"
        assert "def getGatewayAddress() -> str:" in content
        assert "Returns the gateway address." in content

    def test_function_with_params(self):
        data = {
            "module": "system.tag",
            "functions": [
                {
                    "name": "readBlocking",
                    "params": [
                        {"name": "tagPaths", "type": "List[String]"},
                    ],
                    "returns": {"type": "List[QualifiedValue]"},
                }
            ],
        }
        path = self._make_api_file(data)
        _, _, content = _generate_module_stub(path)
        path.unlink()

        # QualifiedValue is not in TYPE_MAP, but it's inside List[] so _convert_type
        # processes it — it passes through as-is. However the outer List[] wraps it.
        assert "def readBlocking(tagPaths: list[str]) -> list[Any]:" in content

    def test_optional_param_with_none_default(self):
        data = {
            "module": "system.db",
            "functions": [
                {
                    "name": "runQuery",
                    "params": [
                        {"name": "query", "type": "String"},
                        {"name": "database", "type": "String", "optional": True, "default": "None"},
                    ],
                    "returns": {"type": "Dataset"},
                }
            ],
        }
        path = self._make_api_file(data)
        _, _, content = _generate_module_stub(path)
        path.unlink()

        assert "database: str = None" in content

    def test_optional_param_with_numeric_default(self):
        data = {
            "module": "system.util",
            "functions": [
                {
                    "name": "sleep",
                    "params": [
                        {"name": "millis", "type": "int", "optional": True, "default": "1000"},
                    ],
                    "returns": {"type": "void"},
                }
            ],
        }
        path = self._make_api_file(data)
        _, _, content = _generate_module_stub(path)
        path.unlink()

        assert "millis: int = 1000" in content

    def test_optional_param_with_boolean_default(self):
        data = {
            "module": "system.tag",
            "functions": [
                {
                    "name": "browse",
                    "params": [
                        {"name": "recursive", "type": "boolean", "optional": True, "default": "False"},
                    ],
                    "returns": {"type": "List"},
                }
            ],
        }
        path = self._make_api_file(data)
        _, _, content = _generate_module_stub(path)
        path.unlink()

        assert "recursive: bool = False" in content

    def test_optional_param_with_string_default(self):
        data = {
            "module": "system.net",
            "functions": [
                {
                    "name": "httpGet",
                    "params": [
                        {"name": "contentType", "type": "String", "optional": True, "default": "text/html"},
                    ],
                    "returns": {"type": "String"},
                }
            ],
        }
        path = self._make_api_file(data)
        _, _, content = _generate_module_stub(path)
        path.unlink()

        assert 'contentType: str = "text/html"' in content

    def test_no_functions(self):
        data = {"module": "system.empty", "functions": []}
        path = self._make_api_file(data)
        module, submodule, content = _generate_module_stub(path)
        path.unlink()

        assert submodule == "empty"
        assert "def " not in content
