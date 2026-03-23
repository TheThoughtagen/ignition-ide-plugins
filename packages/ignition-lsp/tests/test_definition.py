"""Tests for definition provider — system.* API and project script resolution."""

import textwrap

import pytest
from pathlib import Path

from lsprotocol.types import Position

from ignition_lsp.definition import (
    get_definition,
    _get_word_at_position,
    _resolve_api_function,
    _resolve_project_script,
    _resolve_import,
    _parse_import_line,
    _find_module_in_index,
    _find_function_line,
    _api_function_location,
)
from ignition_lsp.project_scanner import ProjectIndex, ScriptLocation
from ignition_lsp.script_symbols import SymbolCache


def _make_loc(**kwargs) -> ScriptLocation:
    defaults = dict(
        file_path="/project/ignition/script-python/utils/code.py",
        script_key="__file__",
        line_number=1,
        module_path="project.library.utils",
        resource_type="script-python",
        context_name="",
    )
    defaults.update(kwargs)
    return ScriptLocation(**defaults)


def _make_index(scripts=None) -> ProjectIndex:
    idx = ProjectIndex(root_path="/project")
    if scripts:
        idx.scripts = scripts
    return idx


# ── Word Extraction ──────────────────────────────────────────────────


class TestGetWordAtPosition:
    def test_dotted_identifier(self, mock_document, position):
        doc = mock_document("system.tag.readBlocking(paths)")
        word = _get_word_at_position(doc, position(0, 15))
        assert word == "system.tag.readBlocking"

    def test_bare_function_name(self, mock_document, position):
        doc = mock_document("result = readBlocking(paths)")
        word = _get_word_at_position(doc, position(0, 15))
        assert word == "readBlocking"

    def test_project_reference(self, mock_document, position):
        doc = mock_document("project.library.utils.doStuff()")
        word = _get_word_at_position(doc, position(0, 10))
        assert word == "project.library.utils.doStuff"

    def test_empty_line(self, mock_document, position):
        doc = mock_document("")
        word = _get_word_at_position(doc, position(0, 0))
        assert word == ""


# ── API Function Resolution ──────────────────────────────────────────


class TestResolveApiFunction:
    def test_full_name_match(self, api_loader):
        loc = _resolve_api_function("system.tag.readBlocking", api_loader)
        assert loc is not None
        assert loc.uri.endswith("system_tag.json")

    def test_bare_name_match(self, api_loader):
        loc = _resolve_api_function("readBlocking", api_loader)
        assert loc is not None
        assert loc.uri.endswith("system_tag.json")

    def test_no_match_returns_none(self, api_loader):
        loc = _resolve_api_function("nonexistent.function", api_loader)
        assert loc is None

    def test_location_points_to_correct_line(self, api_loader):
        loc = _resolve_api_function("system.tag.readBlocking", api_loader)
        assert loc is not None
        # The line should point to the "name": "readBlocking" entry
        json_path = Path(loc.uri.replace("file://", ""))
        text = json_path.read_text()
        lines = text.splitlines()
        target_line = lines[loc.range.start.line]
        assert '"name": "readBlocking"' in target_line

    def test_different_modules(self, api_loader):
        """Functions from different modules resolve to their correct JSON files."""
        loc_tag = _resolve_api_function("system.tag.readBlocking", api_loader)
        loc_db = _resolve_api_function("system.db.runPrepQuery", api_loader)
        assert loc_tag is not None
        assert loc_db is not None
        assert loc_tag.uri.endswith("system_tag.json")
        assert loc_db.uri.endswith("system_db.json")

    def test_module_name_returns_none(self, api_loader):
        """A module name alone (not a function) shouldn't return a definition."""
        loc = _resolve_api_function("system.tag", api_loader)
        assert loc is None


class TestFindFunctionLine:
    def test_finds_correct_line(self):
        json_path = Path(__file__).parent.parent / "ignition_lsp" / "api_db" / "system_tag.json"
        line = _find_function_line(json_path, "readBlocking")
        text = json_path.read_text()
        lines = text.splitlines()
        assert '"name": "readBlocking"' in lines[line]

    def test_not_found_returns_zero(self, tmp_path):
        json_file = tmp_path / "test.json"
        json_file.write_text('{"functions": []}')
        line = _find_function_line(json_file, "nonexistent")
        assert line == 0


# ── Project Script Resolution ────────────────────────────────────────


class TestResolveProjectScript:
    def test_exact_module_path(self):
        index = _make_index([
            _make_loc(module_path="project.library.utils", file_path="/p/utils.py", line_number=1),
        ])
        loc = _resolve_project_script("project.library.utils", index)
        assert loc is not None
        assert loc.uri == "file:///p/utils.py"
        assert loc.range.start.line == 0  # 1-based -> 0-based

    def test_line_number_conversion(self):
        index = _make_index([
            _make_loc(module_path="project.library.utils", file_path="/p/utils.py", line_number=42),
        ])
        loc = _resolve_project_script("project.library.utils", index)
        assert loc is not None
        assert loc.range.start.line == 41  # 42 (1-based) -> 41 (0-based)

    def test_unique_prefix_resolves(self):
        """If a prefix uniquely matches one script, jump to it."""
        index = _make_index([
            _make_loc(module_path="project.library.utils", file_path="/p/utils.py"),
        ])
        loc = _resolve_project_script("project.library", index)
        assert loc is not None
        assert loc.uri == "file:///p/utils.py"

    def test_ambiguous_prefix_returns_none(self):
        """If a prefix matches multiple scripts, return None."""
        index = _make_index([
            _make_loc(module_path="project.library.utils"),
            _make_loc(module_path="project.library.config"),
        ])
        loc = _resolve_project_script("project.library", index)
        assert loc is None

    def test_no_match_returns_none(self):
        index = _make_index([
            _make_loc(module_path="project.library.utils"),
        ])
        loc = _resolve_project_script("shared.something", index)
        assert loc is None

    def test_shared_prefix_works(self):
        index = _make_index([
            _make_loc(module_path="shared.utils.helpers", file_path="/p/helpers.py"),
        ])
        loc = _resolve_project_script("shared.utils.helpers", index)
        assert loc is not None
        assert loc.uri == "file:///p/helpers.py"


# ── Full get_definition Integration ──────────────────────────────────


class TestGetDefinition:
    def test_system_function_resolved(self, mock_document, position, api_loader):
        doc = mock_document("system.tag.readBlocking(paths)")
        loc = get_definition(doc, position(0, 15), api_loader, None)
        assert loc is not None
        assert loc.uri.endswith("system_tag.json")

    def test_project_script_resolved(self, mock_document, position):
        index = _make_index([
            _make_loc(module_path="project.library.utils", file_path="/p/utils.py"),
        ])
        doc = mock_document("project.library.utils.doStuff()")
        # Position on "project.library.utils" portion
        loc = get_definition(doc, position(0, 10), None, index)
        assert loc is not None
        assert loc.uri == "file:///p/utils.py"

    def test_no_loader_no_index_returns_none(self, mock_document, position):
        doc = mock_document("system.tag.readBlocking(paths)")
        loc = get_definition(doc, position(0, 15), None, None)
        assert loc is None

    def test_empty_word_returns_none(self, mock_document, position):
        doc = mock_document("  ")
        loc = get_definition(doc, position(0, 0), None, None)
        assert loc is None

    def test_api_takes_priority_over_project(self, mock_document, position, api_loader):
        """If both API and project match, API wins (system.* is always API)."""
        index = _make_index([
            _make_loc(module_path="system.tag.readBlocking"),
        ])
        doc = mock_document("system.tag.readBlocking()")
        loc = get_definition(doc, position(0, 15), api_loader, index)
        assert loc is not None
        # Should be the API JSON, not the project file
        assert loc.uri.endswith("system_tag.json")


# ── Symbol-Level Definition Tests ────────────────────────────────────


def _write_py(tmp_path, source, filename="code.py"):
    p = tmp_path / filename
    p.write_text(textwrap.dedent(source))
    return str(p)


class TestSymbolLevelDefinition:
    """Tests for go-to-definition that resolves to specific symbol lines."""

    def test_jump_to_function(self, tmp_path, mock_document, position, symbol_cache):
        path = _write_py(tmp_path, '''\
            LOGGER = "test"

            def tagChangeEvent(event):
                pass
        ''')
        index = _make_index([
            _make_loc(module_path="project.callables", file_path=path),
        ])
        doc = mock_document("project.callables.tagChangeEvent(event)")
        loc = get_definition(doc, position(0, 20), None, index, symbol_cache)
        assert loc is not None
        assert loc.uri == f"file://{path}"
        # tagChangeEvent is on line 3 (1-based) -> line 2 (0-based)
        assert loc.range.start.line == 2

    def test_jump_to_class(self, tmp_path, mock_document, position, symbol_cache):
        path = _write_py(tmp_path, '''\
            def foo():
                pass

            class Handler:
                def run(self):
                    pass
        ''')
        index = _make_index([
            _make_loc(module_path="project.utils", file_path=path),
        ])
        doc = mock_document("project.utils.Handler()")
        loc = get_definition(doc, position(0, 15), None, index, symbol_cache)
        assert loc is not None
        # Handler is on line 4 (1-based) -> line 3 (0-based)
        assert loc.range.start.line == 3

    def test_jump_to_method(self, tmp_path, mock_document, position, symbol_cache):
        path = _write_py(tmp_path, '''\
            class Handler:
                def __init__(self):
                    pass

                def process(self, data):
                    pass
        ''')
        index = _make_index([
            _make_loc(module_path="project.utils", file_path=path),
        ])
        doc = mock_document("project.utils.Handler.process(data)")
        loc = get_definition(doc, position(0, 25), None, index, symbol_cache)
        assert loc is not None
        # process is on line 5 (1-based) -> line 4 (0-based)
        assert loc.range.start.line == 4

    def test_unknown_symbol_falls_back_to_line_1(self, tmp_path, mock_document, position, symbol_cache):
        path = _write_py(tmp_path, "def foo(): pass\n")
        index = _make_index([
            _make_loc(module_path="project.utils", file_path=path),
        ])
        doc = mock_document("project.utils.nonexistent()")
        loc = get_definition(doc, position(0, 15), None, index, symbol_cache)
        assert loc is not None
        # Falls back to the module's line_number (1 -> 0)
        assert loc.range.start.line == 0

    def test_without_cache_preserves_existing(self, mock_document, position):
        """Without symbol_cache, definition jumps to file line 1 as before."""
        index = _make_index([
            _make_loc(module_path="project.utils", file_path="/p/code.py", line_number=1),
        ])
        doc = mock_document("project.utils.someFunc()")
        loc = get_definition(doc, position(0, 10), None, index)  # no symbol_cache
        assert loc is not None
        assert loc.range.start.line == 0

    def test_from_import_resolves_module(self, mock_document, position):
        """go-to-definition on module in 'from X import Y' resolves the module."""
        index = _make_index([
            _make_loc(module_path="core.util.secrets", file_path="/p/secrets.py"),
        ])
        doc = mock_document("from core.util.secrets import get_secret")
        # Cursor on "core" in the module path
        loc = get_definition(doc, position(0, 7), None, index)
        assert loc is not None
        assert loc.uri == "file:///p/secrets.py"

    def test_from_import_resolves_imported_name(self, tmp_path, mock_document, position, symbol_cache):
        """go-to-definition on imported name jumps to the symbol in the module."""
        path = _write_py(tmp_path, '''\
            DEFAULT_PROVIDER = "default"

            def get_secret(name, default=None):
                pass

            def get_service_config(service):
                pass
        ''')
        index = _make_index([
            _make_loc(module_path="core.util.secrets", file_path=path),
        ])
        doc = mock_document("from core.util.secrets import get_secret")
        # Cursor on "get_secret" (the imported name)
        loc = get_definition(doc, position(0, 35), None, index, symbol_cache)
        assert loc is not None
        assert loc.uri == f"file://{path}"
        # get_secret is on line 3 (1-based) -> line 2 (0-based)
        assert loc.range.start.line == 2

    def test_bare_import_resolves(self, mock_document, position):
        """go-to-definition on 'import X' resolves the module."""
        index = _make_index([
            _make_loc(module_path="testing.decorators", file_path="/p/decorators.py"),
        ])
        doc = mock_document("import testing.decorators")
        # Cursor on "testing"
        loc = get_definition(doc, position(0, 10), None, index)
        assert loc is not None
        assert loc.uri == "file:///p/decorators.py"


# ── Import Line Parsing ──────────────────────────────────────────────


class TestParseImportLine:
    def test_from_import_single(self):
        result = _parse_import_line("from core.util.secrets import get_secret")
        assert result == ("core.util.secrets", ["get_secret"])

    def test_from_import_multiple(self):
        result = _parse_import_line("from core.util.secrets import get_secret, get_service_config, DEFAULT_PROVIDER")
        assert result is not None
        module, names = result
        assert module == "core.util.secrets"
        assert "get_secret" in names
        assert "get_service_config" in names
        assert "DEFAULT_PROVIDER" in names

    def test_from_import_with_parens(self):
        result = _parse_import_line("from core.util.secrets import (get_secret, get_service_config)")
        assert result is not None
        module, names = result
        assert module == "core.util.secrets"
        assert "get_secret" in names
        assert "get_service_config" in names

    def test_from_import_with_alias(self):
        result = _parse_import_line("from core.util.secrets import get_secret as gs")
        assert result is not None
        module, names = result
        assert module == "core.util.secrets"
        assert names == ["get_secret"]

    def test_plain_import(self):
        result = _parse_import_line("import testing.decorators")
        assert result == ("testing.decorators", [])

    def test_not_import_line(self):
        assert _parse_import_line("x = testing.decorators.test()") is None

    def test_comment_line(self):
        assert _parse_import_line("# from testing import stuff") is None

    def test_indented_import(self):
        result = _parse_import_line("    from testing.decorators import test")
        assert result is not None
        assert result[0] == "testing.decorators"


# ── Import-Aware Definition (Integration) ────────────────────────────


class TestResolveImport:
    def test_cursor_on_imported_name_without_cache(self, mock_document, position):
        """Without symbol cache, falls back to the module file."""
        index = _make_index([
            _make_loc(module_path="testing.decorators", file_path="/p/decorators.py"),
        ])
        doc = mock_document("from testing.decorators import test")
        # Cursor on "test"
        loc = _resolve_import(doc, position(0, 32), "test", index)
        assert loc is not None
        assert loc.uri == "file:///p/decorators.py"

    def test_no_match_returns_none(self, mock_document, position):
        index = _make_index([])
        doc = mock_document("from nonexistent.module import thing")
        loc = _resolve_import(doc, position(0, 32), "thing", index)
        assert loc is None

    def test_non_import_line_returns_none(self, mock_document, position):
        index = _make_index([
            _make_loc(module_path="testing.decorators", file_path="/p/decorators.py"),
        ])
        doc = mock_document("result = testing.decorators.test()")
        loc = _resolve_import(doc, position(0, 30), "test", index)
        assert loc is None


# ── Find Module in Index ─────────────────────────────────────────────


class TestFindModuleInIndex:
    def test_exact_match(self):
        index = _make_index([
            _make_loc(module_path="testing.decorators", file_path="/p/decorators.py"),
        ])
        loc = _find_module_in_index("testing.decorators", index)
        assert loc is not None
        assert loc.file_path == "/p/decorators.py"

    def test_prefix_unique_match(self):
        index = _make_index([
            _make_loc(module_path="testing.decorators", file_path="/p/decorators.py"),
        ])
        loc = _find_module_in_index("testing", index)
        assert loc is not None

    def test_no_match(self):
        index = _make_index([])
        loc = _find_module_in_index("nonexistent.module", index)
        assert loc is None
