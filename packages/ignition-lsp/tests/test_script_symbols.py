"""Tests for script_symbols.py — AST extraction, Py2 handling, cache, helpers."""

import os
import textwrap
import time

import pytest

from ignition_lsp.script_symbols import (
    ModuleSymbols,
    ScriptClass,
    ScriptFunction,
    ScriptVariable,
    SymbolCache,
    _preprocess_py2,
    extract_symbols,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _write_py(tmp_path, source, filename="code.py"):
    """Write a .py file and return its path."""
    p = tmp_path / filename
    p.write_text(textwrap.dedent(source))
    return str(p)


# ── Extraction Tests ─────────────────────────────────────────────────


class TestExtractSimpleFunction:
    def test_basic_function(self, tmp_path):
        path = _write_py(tmp_path, """\
            def helper(tagPath):
                return tagPath
        """)
        symbols = extract_symbols(path, "project.utils")
        assert len(symbols.functions) == 1
        f = symbols.functions[0]
        assert f.name == "helper"
        assert f.params == ["tagPath"]
        assert f.line_number == 1
        assert f.is_method is False

    def test_function_with_docstring(self, tmp_path):
        path = _write_py(tmp_path, '''\
            def process(data, timeout=30):
                """Process incoming data with optional timeout."""
                pass
        ''')
        symbols = extract_symbols(path)
        f = symbols.functions[0]
        assert f.docstring == "Process incoming data with optional timeout."
        assert f.params == ["data", "timeout=..."]

    def test_function_with_defaults(self, tmp_path):
        path = _write_py(tmp_path, """\
            def configure(name, value=None, enabled=True):
                pass
        """)
        symbols = extract_symbols(path)
        f = symbols.functions[0]
        assert f.params == ["name", "value=...", "enabled=..."]

    def test_function_with_decorators(self, tmp_path):
        path = _write_py(tmp_path, """\
            @staticmethod
            def helper():
                pass
        """)
        symbols = extract_symbols(path)
        f = symbols.functions[0]
        assert "staticmethod" in f.decorators

    def test_multiple_functions(self, tmp_path):
        path = _write_py(tmp_path, """\
            def foo():
                pass

            def bar():
                pass

            def baz():
                pass
        """)
        symbols = extract_symbols(path)
        assert len(symbols.functions) == 3
        names = [f.name for f in symbols.functions]
        assert names == ["foo", "bar", "baz"]


class TestExtractClass:
    def test_basic_class(self, tmp_path):
        path = _write_py(tmp_path, """\
            class TagHandler:
                pass
        """)
        symbols = extract_symbols(path)
        assert len(symbols.classes) == 1
        cls = symbols.classes[0]
        assert cls.name == "TagHandler"
        assert cls.line_number == 1

    def test_class_with_bases(self, tmp_path):
        path = _write_py(tmp_path, """\
            class MyHandler(BaseHandler, Mixin):
                pass
        """)
        symbols = extract_symbols(path)
        cls = symbols.classes[0]
        assert cls.bases == ["BaseHandler", "Mixin"]

    def test_class_with_methods(self, tmp_path):
        path = _write_py(tmp_path, '''\
            class Worker:
                """A background worker."""

                def __init__(self, name):
                    self.name = name

                def run(self):
                    pass

                def stop(self, force=False):
                    pass
        ''')
        symbols = extract_symbols(path)
        cls = symbols.classes[0]
        assert cls.docstring == "A background worker."
        method_names = [m.name for m in cls.methods]
        assert "__init__" in method_names
        assert "run" in method_names
        assert "stop" in method_names
        # Methods should skip 'self' in params
        init = next(m for m in cls.methods if m.name == "__init__")
        assert init.params == ["name"]
        assert init.is_method is True

    def test_class_variables(self, tmp_path):
        path = _write_py(tmp_path, """\
            class Config:
                MAX_RETRIES = 3
                TIMEOUT = 30
        """)
        symbols = extract_symbols(path)
        cls = symbols.classes[0]
        assert "MAX_RETRIES" in cls.class_variables
        assert "TIMEOUT" in cls.class_variables


class TestExtractVariables:
    def test_top_level_assignment(self, tmp_path):
        path = _write_py(tmp_path, """\
            LOGGER_NAME = "MyScript"
            MAX_RETRIES = 5
        """)
        symbols = extract_symbols(path)
        assert len(symbols.variables) == 2
        names = [v.name for v in symbols.variables]
        assert "LOGGER_NAME" in names
        assert "MAX_RETRIES" in names

    def test_variable_value_repr(self, tmp_path):
        path = _write_py(tmp_path, """\
            TIMEOUT = 30
        """)
        symbols = extract_symbols(path)
        v = symbols.variables[0]
        assert v.value_repr == "30"

    def test_annotated_variable(self, tmp_path):
        path = _write_py(tmp_path, """\
            count: int = 0
        """)
        symbols = extract_symbols(path)
        v = symbols.variables[0]
        assert v.name == "count"
        assert v.type_hint == "int"
        assert v.value_repr == "0"


class TestEdgeCases:
    def test_empty_file(self, tmp_path):
        path = _write_py(tmp_path, "")
        symbols = extract_symbols(path)
        assert symbols.functions == []
        assert symbols.classes == []
        assert symbols.variables == []
        assert symbols.parse_error is None

    def test_nonexistent_file(self):
        symbols = extract_symbols("/nonexistent/path/code.py")
        assert symbols.parse_error is not None
        assert "not found" in symbols.parse_error.lower() or "No such file" in symbols.parse_error

    def test_syntax_error(self, tmp_path):
        path = _write_py(tmp_path, """\
            def broken(
                # missing closing paren
        """)
        symbols = extract_symbols(path)
        assert symbols.parse_error is not None

    def test_module_path_preserved(self, tmp_path):
        path = _write_py(tmp_path, "x = 1\n")
        symbols = extract_symbols(path, "core.networking.callables")
        assert symbols.module_path == "core.networking.callables"

    def test_mixed_content(self, tmp_path):
        path = _write_py(tmp_path, '''\
            LOGGER = "test"

            def helper():
                """A helper function."""
                pass

            class Handler:
                def process(self):
                    pass

            TIMEOUT = 30
        ''')
        symbols = extract_symbols(path)
        assert len(symbols.functions) == 1
        assert len(symbols.classes) == 1
        assert len(symbols.variables) == 2


# ── Py2 Preprocessing Tests ─────────────────────────────────────────


class TestPy2Preprocessing:
    def test_print_statement(self, tmp_path):
        path = _write_py(tmp_path, """\
            print "hello world"
        """)
        symbols = extract_symbols(path)
        assert symbols.parse_error is None

    def test_except_comma(self, tmp_path):
        path = _write_py(tmp_path, """\
            try:
                pass
            except Exception, e:
                pass
        """)
        symbols = extract_symbols(path)
        assert symbols.parse_error is None

    def test_raise_comma(self, tmp_path):
        path = _write_py(tmp_path, """\
            raise ValueError, "bad value"
        """)
        symbols = extract_symbols(path)
        assert symbols.parse_error is None

    def test_mixed_py2_with_functions(self, tmp_path):
        path = _write_py(tmp_path, """\
            def handler(event):
                print "Processing event"
                try:
                    result = event.value
                except Exception, e:
                    print "Error:", e
                return result
        """)
        symbols = extract_symbols(path)
        assert symbols.parse_error is None
        assert len(symbols.functions) == 1
        assert symbols.functions[0].name == "handler"

    def test_preprocess_preserves_valid_py3(self):
        source = 'print("hello")\nx = 1'
        result = _preprocess_py2(source)
        assert 'print("hello")' in result


# ── Cache Tests ──────────────────────────────────────────────────────


class TestSymbolCache:
    def test_cache_hit(self, tmp_path):
        path = _write_py(tmp_path, "def foo(): pass\n")
        cache = SymbolCache()
        s1 = cache.get(path, "mod")
        s2 = cache.get(path, "mod")
        # Same object returned from cache
        assert s1 is s2

    def test_mtime_invalidation(self, tmp_path):
        path = _write_py(tmp_path, "def foo(): pass\n")
        cache = SymbolCache()
        s1 = cache.get(path, "mod")
        assert len(s1.functions) == 1

        # Wait briefly and modify the file
        time.sleep(0.05)
        with open(path, "w") as f:
            f.write("def foo(): pass\ndef bar(): pass\n")
        # Force mtime change (some filesystems have 1s granularity)
        os.utime(path, (time.time() + 1, time.time() + 1))

        s2 = cache.get(path, "mod")
        assert s2 is not s1
        assert len(s2.functions) == 2

    def test_explicit_invalidation(self, tmp_path):
        path = _write_py(tmp_path, "def foo(): pass\n")
        cache = SymbolCache()
        s1 = cache.get(path, "mod")
        cache.invalidate(path)
        s2 = cache.get(path, "mod")
        assert s2 is not s1

    def test_clear(self, tmp_path):
        path = _write_py(tmp_path, "def foo(): pass\n")
        cache = SymbolCache()
        cache.get(path, "mod")
        cache.clear()
        s2 = cache.get(path, "mod")
        # After clear, should re-extract (new object)
        assert s2.module_path == "mod"

    def test_nonexistent_file(self):
        cache = SymbolCache()
        s = cache.get("/nonexistent/code.py", "mod")
        assert s.parse_error is not None


# ── Snippet & Doc Generation Tests ───────────────────────────────────


class TestSnippetGeneration:
    def test_no_params(self):
        f = ScriptFunction(name="run", line_number=1, signature="def run()", params=[])
        assert f.get_completion_snippet() == "run()$0"

    def test_single_param(self):
        f = ScriptFunction(name="process", line_number=1, signature="def process(data)", params=["data"])
        assert f.get_completion_snippet() == "process(${1:data})$0"

    def test_multiple_params(self):
        f = ScriptFunction(
            name="configure", line_number=1,
            signature="def configure(name, value, enabled)",
            params=["name", "value", "enabled"],
        )
        snippet = f.get_completion_snippet()
        assert snippet == "configure(${1:name}, ${2:value}, ${3:enabled})$0"

    def test_method_skips_self(self):
        """Params should already exclude self; snippet should not include it."""
        f = ScriptFunction(
            name="process", line_number=1,
            signature="def process(self, data)",
            params=["data"],  # self already excluded
            is_method=True,
        )
        assert f.get_completion_snippet() == "process(${1:data})$0"


class TestMarkdownDocGeneration:
    def test_function_doc(self):
        f = ScriptFunction(
            name="helper", line_number=1,
            signature="def helper(tagPath)",
            params=["tagPath"],
            docstring="Look up a tag path.",
        )
        md = f.get_markdown_doc("project.utils")
        assert "**project.utils.helper**" in md
        assert "def helper(tagPath)" in md
        assert "Look up a tag path." in md

    def test_function_doc_no_module(self):
        f = ScriptFunction(
            name="helper", line_number=1,
            signature="def helper()", params=[],
        )
        md = f.get_markdown_doc()
        assert "**helper**" in md

    def test_class_doc(self):
        cls = ScriptClass(
            name="Worker", line_number=1,
            docstring="Background worker.",
            bases=["BaseWorker"],
            methods=[
                ScriptFunction(name="run", line_number=5, signature="def run(self)", params=[], is_method=True),
                ScriptFunction(name="stop", line_number=10, signature="def stop(self)", params=[], is_method=True),
            ],
            class_variables=["MAX_RETRIES"],
        )
        md = cls.get_markdown_doc("core.workers")
        assert "**core.workers.Worker** (class)" in md
        assert "class Worker(BaseWorker)" in md
        assert "Background worker." in md
        assert "`run`" in md
        assert "`stop`" in md
        assert "`MAX_RETRIES`" in md

    def test_class_doc_hides_dunder(self):
        """Dunder methods should be hidden except __init__."""
        cls = ScriptClass(
            name="Foo", line_number=1,
            methods=[
                ScriptFunction(name="__init__", line_number=2, signature="def __init__(self)", params=[], is_method=True),
                ScriptFunction(name="__repr__", line_number=5, signature="def __repr__(self)", params=[], is_method=True),
                ScriptFunction(name="process", line_number=8, signature="def process(self)", params=[], is_method=True),
            ],
        )
        md = cls.get_markdown_doc()
        assert "`__init__`" in md
        assert "`__repr__`" not in md
        assert "`process`" in md
