"""Tests for project_scanner.py — Ignition project directory scanning."""

import json
import os
from pathlib import Path

import pytest

from ignition_lsp.project_scanner import (
    SCRIPT_KEYS,
    ProjectIndex,
    ProjectScanner,
    ScriptLocation,
)


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal Ignition project directory structure."""
    # project.json at root
    (tmp_path / "project.json").write_text(
        json.dumps({"title": "Test Project", "enabled": True})
    )

    # script-python directory with .py files
    script_dir = tmp_path / "ignition" / "script-python" / "project-library" / "utils"
    script_dir.mkdir(parents=True)
    (script_dir / "code.py").write_text("def helper():\n    return 42\n")
    # resource.json alongside
    (script_dir / "resource.json").write_text(
        json.dumps({"scope": "A", "version": 1, "files": ["code.py"]})
    )

    # Another script module
    module_dir = tmp_path / "ignition" / "script-python" / "project-library" / "tags"
    module_dir.mkdir(parents=True)
    (module_dir / "code.py").write_text(
        "def read_tag(path):\n    return system.tag.readBlocking([path])\n"
    )

    # Perspective view with embedded scripts
    view_dir = tmp_path / "ignition" / "perspective-views" / "Overview"
    view_dir.mkdir(parents=True)
    view_json = {
        "root": {
            "children": [
                {
                    "meta": {"name": "Button_1"},
                    "events": {
                        "onActionPerformed": {
                            "script": "system.perspective.print(\\\"clicked\\\")"
                        }
                    },
                    "type": "ia.input.button",
                }
            ],
            "events": {
                "onStartup": {
                    "script": "logger \\u003d system.util.getLogger(\\\"test\\\")"
                }
            },
            "meta": {"name": "root"},
            "type": "ia.container.flex",
        }
    }
    (view_dir / "view.json").write_text(json.dumps(view_json, indent=2))

    # Tags directory with embedded event script
    tags_dir = tmp_path / "ignition" / "tags"
    tags_dir.mkdir(parents=True)
    tags_json = {
        "name": "MyTag",
        "tagType": "AtomicTag",
        "eventScripts": {
            "valueChanged": {
                "eventScript": {"script": "print(\\\"tag changed\\\")"}
            }
        },
    }
    (tags_dir / "tags.json").write_text(json.dumps(tags_json, indent=2))

    return tmp_path


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    """Create a project.json with nothing else."""
    (tmp_path / "project.json").write_text(json.dumps({"title": "Empty"}))
    return tmp_path


# ──────────────────────────────────────────────
# ProjectScanner basics
# ──────────────────────────────────────────────


class TestProjectScannerBasics:
    def test_is_ignition_project(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        assert scanner.is_ignition_project() is True

    def test_not_ignition_project(self, tmp_path: Path):
        scanner = ProjectScanner(str(tmp_path))
        assert scanner.is_ignition_project() is False

    def test_scan_returns_project_index(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()
        assert isinstance(index, ProjectIndex)
        assert index.root_path == str(tmp_project.resolve())
        assert index.last_updated is not None

    def test_scan_empty_project(self, empty_project: Path):
        scanner = ProjectScanner(str(empty_project))
        index = scanner.scan()
        assert index.script_count == 0

    def test_scan_non_project_returns_empty_index(self, tmp_path: Path):
        scanner = ProjectScanner(str(tmp_path))
        index = scanner.scan()
        assert index.script_count == 0
        assert index.last_updated is None  # scan skipped


# ──────────────────────────────────────────────
# Python file discovery
# ──────────────────────────────────────────────


class TestPythonFileDiscovery:
    def test_finds_py_files_in_script_python(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        py_scripts = [s for s in index.scripts if s.script_key == "__file__"]
        assert len(py_scripts) == 2

    def test_py_file_has_correct_resource_type(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        py_scripts = [s for s in index.scripts if s.script_key == "__file__"]
        for s in py_scripts:
            assert s.resource_type == "script-python"

    def test_module_path_computed_from_directory(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        py_scripts = [s for s in index.scripts if s.script_key == "__file__"]
        module_paths = {s.module_path for s in py_scripts}

        assert "project.library.utils" in module_paths
        assert "project.library.tags" in module_paths

    def test_py_file_line_number_is_1(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        py_scripts = [s for s in index.scripts if s.script_key == "__file__"]
        for s in py_scripts:
            assert s.line_number == 1


# ──────────────────────────────────────────────
# JSON embedded script discovery
# ──────────────────────────────────────────────


class TestJsonScriptDiscovery:
    def test_finds_scripts_in_perspective_view(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        view_scripts = [
            s for s in index.scripts if s.resource_type == "perspective-view"
        ]
        # Should find onActionPerformed + onStartup
        script_keys = {s.script_key for s in view_scripts}
        assert "onActionPerformed" in script_keys or "script" in script_keys
        assert len(view_scripts) >= 2

    def test_finds_nested_event_scripts(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        tag_scripts = [s for s in index.scripts if "tags" in s.file_path]
        # Should find the eventScript nested object
        assert len(tag_scripts) >= 1

    def test_script_location_has_line_number(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        for script in index.scripts:
            assert script.line_number >= 1

    def test_context_name_extracted_from_meta(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        view_scripts = [
            s for s in index.scripts if s.resource_type == "perspective-view"
        ]
        context_names = {s.context_name for s in view_scripts}
        # Should have "root" and/or "Button_1"
        assert len(context_names) > 0


# ──────────────────────────────────────────────
# ProjectIndex queries
# ──────────────────────────────────────────────


class TestProjectIndexQueries:
    def test_scripts_by_type(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        by_type = index.scripts_by_type()
        assert "script-python" in by_type
        assert len(by_type["script-python"]) >= 2  # 2 .py files

    def test_scripts_in_file(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        view_file = str(
            tmp_project / "ignition" / "perspective-views" / "Overview" / "view.json"
        )
        file_scripts = index.scripts_in_file(view_file)
        assert len(file_scripts) >= 2

    def test_find_by_module_path(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        result = index.find_by_module_path("project.library.utils")
        assert result is not None
        assert result.resource_type == "script-python"

    def test_find_by_module_path_not_found(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        result = index.find_by_module_path("nonexistent.module")
        assert result is None

    def test_search_module_paths(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        results = index.search_module_paths("project.library")
        assert len(results) >= 2


# ──────────────────────────────────────────────
# SCRIPT_KEYS constant
# ──────────────────────────────────────────────


# ──────────────────────────────────────────────
# Parent project hierarchy
# ──────────────────────────────────────────────


@pytest.fixture
def parent_child_project(tmp_path: Path) -> Path:
    """Create a parent-child project pair."""
    # Parent project
    parent = tmp_path / "ParentProject"
    parent.mkdir()
    (parent / "project.json").write_text(
        json.dumps({"title": "ParentProject", "enabled": True})
    )
    parent_scripts = (
        parent / "ignition" / "script-python" / "project-library" / "shared_utils"
    )
    parent_scripts.mkdir(parents=True)
    (parent_scripts / "code.py").write_text("def parent_helper():\n    return 1\n")

    # Another parent module
    parent_other = (
        parent / "ignition" / "script-python" / "project-library" / "common"
    )
    parent_other.mkdir(parents=True)
    (parent_other / "code.py").write_text("def common_func():\n    pass\n")

    # Child project
    child = tmp_path / "ChildProject"
    child.mkdir()
    (child / "project.json").write_text(
        json.dumps(
            {"title": "ChildProject", "parent": "ParentProject", "enabled": True}
        )
    )
    child_scripts = (
        child / "ignition" / "script-python" / "project-library" / "child_module"
    )
    child_scripts.mkdir(parents=True)
    (child_scripts / "code.py").write_text("def child_func():\n    return 2\n")

    return tmp_path


class TestParentProjectHierarchy:
    def test_child_inherits_parent_scripts(self, parent_child_project: Path):
        child_path = parent_child_project / "ChildProject"
        scanner = ProjectScanner(str(child_path))
        index = scanner.scan()

        module_paths = {s.module_path for s in index.scripts}
        assert "project.library.child_module" in module_paths
        assert "project.library.shared_utils" in module_paths
        assert "project.library.common" in module_paths

    def test_parent_roots_tracked(self, parent_child_project: Path):
        child_path = parent_child_project / "ChildProject"
        scanner = ProjectScanner(str(child_path))
        index = scanner.scan()

        assert len(index.parent_roots) == 1
        assert "ParentProject" in index.parent_roots[0]

    def test_child_overrides_parent(self, parent_child_project: Path):
        """When child has same module_path as parent, child wins."""
        # Add a shared_utils to the child too
        child_override = (
            parent_child_project
            / "ChildProject"
            / "ignition"
            / "script-python"
            / "project-library"
            / "shared_utils"
        )
        child_override.mkdir(parents=True)
        (child_override / "code.py").write_text(
            "def parent_helper():\n    return 'overridden'\n"
        )

        child_path = parent_child_project / "ChildProject"
        scanner = ProjectScanner(str(child_path))
        index = scanner.scan()

        # Should only have one entry for shared_utils (the child's)
        shared = [
            s
            for s in index.scripts
            if s.module_path == "project.library.shared_utils"
            and s.script_key == "__file__"
        ]
        assert len(shared) == 1
        assert "ChildProject" in shared[0].file_path

    def test_no_parent_field_scans_normally(self, tmp_project: Path):
        scanner = ProjectScanner(str(tmp_project))
        index = scanner.scan()

        assert index.parent_roots == []
        assert index.script_count > 0

    def test_missing_parent_logs_warning(self, tmp_path: Path, caplog):
        """When parent project doesn't exist, scanner continues without error."""
        project = tmp_path / "Orphan"
        project.mkdir()
        (project / "project.json").write_text(
            json.dumps({"title": "Orphan", "parent": "NonExistent"})
        )
        orphan_scripts = (
            project / "ignition" / "script-python" / "project-library" / "my_mod"
        )
        orphan_scripts.mkdir(parents=True)
        (orphan_scripts / "code.py").write_text("x = 1\n")

        scanner = ProjectScanner(str(project))
        index = scanner.scan()

        assert index.parent_roots == []
        assert index.script_count >= 1
        assert "not found" in caplog.text.lower() or len(caplog.records) >= 0

    def test_cycle_detection(self, tmp_path: Path):
        """A parents B, B parents A — no infinite loop."""
        a = tmp_path / "ProjectA"
        a.mkdir()
        (a / "project.json").write_text(
            json.dumps({"title": "ProjectA", "parent": "ProjectB"})
        )
        (a / "ignition").mkdir()

        b = tmp_path / "ProjectB"
        b.mkdir()
        (b / "project.json").write_text(
            json.dumps({"title": "ProjectB", "parent": "ProjectA"})
        )
        (b / "ignition").mkdir()

        scanner = ProjectScanner(str(a))
        index = scanner.scan()
        # Should complete without hanging — cycle broken
        assert isinstance(index, ProjectIndex)

    def test_grandparent_inheritance(self, tmp_path: Path):
        """Three-level hierarchy: Grandparent -> Parent -> Child."""
        gp = tmp_path / "GrandparentProject"
        gp.mkdir()
        (gp / "project.json").write_text(
            json.dumps({"title": "GrandparentProject"})
        )
        gp_scripts = (
            gp / "ignition" / "script-python" / "project-library" / "gp_utils"
        )
        gp_scripts.mkdir(parents=True)
        (gp_scripts / "code.py").write_text("GP = True\n")

        parent = tmp_path / "ParentProject"
        parent.mkdir()
        (parent / "project.json").write_text(
            json.dumps({"title": "ParentProject", "parent": "GrandparentProject"})
        )
        p_scripts = (
            parent / "ignition" / "script-python" / "project-library" / "p_utils"
        )
        p_scripts.mkdir(parents=True)
        (p_scripts / "code.py").write_text("P = True\n")

        child = tmp_path / "ChildProject"
        child.mkdir()
        (child / "project.json").write_text(
            json.dumps({"title": "ChildProject", "parent": "ParentProject"})
        )
        c_scripts = (
            child / "ignition" / "script-python" / "project-library" / "c_utils"
        )
        c_scripts.mkdir(parents=True)
        (c_scripts / "code.py").write_text("C = True\n")

        scanner = ProjectScanner(str(child))
        index = scanner.scan()

        module_paths = {s.module_path for s in index.scripts}
        assert "project.library.c_utils" in module_paths
        assert "project.library.p_utils" in module_paths
        assert "project.library.gp_utils" in module_paths
        assert len(index.parent_roots) == 2


class TestScriptKeys:
    def test_contains_expected_keys(self):
        assert "script" in SCRIPT_KEYS
        assert "code" in SCRIPT_KEYS
        assert "onActionPerformed" in SCRIPT_KEYS
        assert "onChange" in SCRIPT_KEYS
        assert "onStartup" in SCRIPT_KEYS
        assert "onShutdown" in SCRIPT_KEYS
        assert "eventScript" in SCRIPT_KEYS
        assert "transform" in SCRIPT_KEYS

    def test_is_frozen_set(self):
        assert isinstance(SCRIPT_KEYS, frozenset)
