"""Tests for workspace symbol provider."""

import pytest
from lsprotocol.types import SymbolKind

from ignition_lsp.project_scanner import ProjectIndex, ScriptLocation
from ignition_lsp.workspace_symbols import (
    get_workspace_symbols,
    _symbol_name,
    _symbol_kind,
)


def _make_loc(**kwargs) -> ScriptLocation:
    """Create a ScriptLocation with sensible defaults."""
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
    """Create a ProjectIndex with given scripts."""
    idx = ProjectIndex(root_path="/project")
    if scripts:
        idx.scripts = scripts
    return idx


class TestSymbolName:
    """Tests for _symbol_name mapping."""

    def test_python_file_uses_module_path(self):
        loc = _make_loc(script_key="__file__", module_path="project.library.utils")
        assert _symbol_name(loc) == "project.library.utils"

    def test_python_file_fallback_to_stem(self):
        loc = _make_loc(script_key="__file__", module_path="", file_path="/foo/bar.py")
        assert _symbol_name(loc) == "bar"

    def test_embedded_script_with_context(self):
        loc = _make_loc(
            script_key="onActionPerformed",
            context_name="Button_1",
        )
        assert _symbol_name(loc) == "Button_1.onActionPerformed"

    def test_embedded_script_without_context(self):
        loc = _make_loc(script_key="script", context_name="")
        assert _symbol_name(loc) == "script"

    def test_transform_with_context(self):
        loc = _make_loc(script_key="transform", context_name="DataSource")
        assert _symbol_name(loc) == "DataSource.transform"


class TestSymbolKind:
    """Tests for _symbol_kind mapping."""

    def test_python_file_is_module(self):
        loc = _make_loc(script_key="__file__")
        assert _symbol_kind(loc) == SymbolKind.Module

    def test_event_handler_is_event(self):
        loc = _make_loc(script_key="onActionPerformed")
        assert _symbol_kind(loc) == SymbolKind.Event

    def test_on_change_is_event(self):
        loc = _make_loc(script_key="onChange")
        assert _symbol_kind(loc) == SymbolKind.Event

    def test_on_startup_is_event(self):
        loc = _make_loc(script_key="onStartup")
        assert _symbol_kind(loc) == SymbolKind.Event

    def test_script_is_function(self):
        loc = _make_loc(script_key="script")
        assert _symbol_kind(loc) == SymbolKind.Function

    def test_transform_is_function(self):
        loc = _make_loc(script_key="transform")
        assert _symbol_kind(loc) == SymbolKind.Function

    def test_code_is_function(self):
        loc = _make_loc(script_key="code")
        assert _symbol_kind(loc) == SymbolKind.Function


class TestGetWorkspaceSymbols:
    """Tests for the main get_workspace_symbols function."""

    def test_none_index_returns_empty(self):
        assert get_workspace_symbols("", None) == []

    def test_empty_query_returns_all(self):
        index = _make_index([
            _make_loc(module_path="utils"),
            _make_loc(script_key="onActionPerformed", context_name="Btn"),
        ])
        result = get_workspace_symbols("", index)
        assert len(result) == 2

    def test_query_filters_by_name(self):
        index = _make_index([
            _make_loc(module_path="project.library.utils"),
            _make_loc(
                script_key="onActionPerformed",
                context_name="Button_1",
                file_path="/p/view.json",
                line_number=10,
            ),
        ])
        result = get_workspace_symbols("Button", index)
        assert len(result) == 1
        assert result[0].name == "Button_1.onActionPerformed"

    def test_query_is_case_insensitive(self):
        index = _make_index([
            _make_loc(module_path="project.library.Utils"),
        ])
        result = get_workspace_symbols("utils", index)
        assert len(result) == 1

    def test_empty_index_returns_empty(self):
        index = _make_index([])
        assert get_workspace_symbols("", index) == []

    def test_symbol_has_correct_location(self):
        loc = _make_loc(
            file_path="/project/code.py",
            line_number=42,
        )
        index = _make_index([loc])
        result = get_workspace_symbols("", index)
        assert len(result) == 1
        sym = result[0]
        assert sym.location.uri == "file:///project/code.py"
        # LSP lines are 0-based, ScriptLocation lines are 1-based
        assert sym.location.range.start.line == 41

    def test_symbol_container_name_is_resource_type(self):
        loc = _make_loc(resource_type="perspective-view")
        index = _make_index([loc])
        result = get_workspace_symbols("", index)
        assert result[0].container_name == "perspective-view"

    def test_python_module_symbol_kind(self):
        loc = _make_loc(script_key="__file__")
        index = _make_index([loc])
        result = get_workspace_symbols("", index)
        assert result[0].kind == SymbolKind.Module

    def test_event_handler_symbol_kind(self):
        loc = _make_loc(script_key="onActionPerformed", context_name="Btn")
        index = _make_index([loc])
        result = get_workspace_symbols("", index)
        assert result[0].kind == SymbolKind.Event

    def test_multiple_query_matches(self):
        index = _make_index([
            _make_loc(script_key="onActionPerformed", context_name="Btn1"),
            _make_loc(script_key="onChange", context_name="Btn2"),
            _make_loc(script_key="transform", context_name="DataSrc"),
        ])
        result = get_workspace_symbols("Btn", index)
        assert len(result) == 2
        names = {s.name for s in result}
        assert names == {"Btn1.onActionPerformed", "Btn2.onChange"}
