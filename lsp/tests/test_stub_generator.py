"""Tests for stub_generator.py — .pyi stub generation for project scripts."""

import os
import textwrap

import pytest

from ignition_lsp.project_scanner import ProjectIndex, ScriptLocation
from ignition_lsp.script_symbols import SymbolCache
from ignition_lsp.stub_generator import (
    STUBS_DIR_NAME,
    _generate_stub_content,
    generate_project_stubs,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _make_project(tmp_path, scripts_dict):
    """Create a minimal Ignition project with script-python .py files.

    scripts_dict maps module_path -> source code, e.g.:
        {"project.library.utils": "def helper(x):\\n    return x\\n"}
    Returns (project_root, ProjectIndex).
    """
    root = tmp_path / "myproject"
    root.mkdir()
    (root / "project.json").write_text('{"title": "MyProject"}')

    script_base = root / "ignition" / "script-python"
    index = ProjectIndex(root_path=str(root))

    for module_path, source in scripts_dict.items():
        parts = module_path.split(".")
        # Each module gets its own directory with code.py (Ignition convention)
        # e.g., project.library.utils → script-python/project/library/utils/code.py
        file_dir = script_base
        for p in parts:
            file_dir = file_dir / p
        file_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_dir / "code.py"
        file_path.write_text(textwrap.dedent(source))

        index.scripts.append(
            ScriptLocation(
                file_path=str(file_path),
                script_key="__file__",
                line_number=1,
                module_path=module_path,
                resource_type="script-python",
            )
        )

    return root, index


# ── Core Generation Tests ────────────────────────────────────────────


class TestGenerateProjectStubs:
    def test_generates_stubs_for_simple_function(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "project.library.utils": """\
                def helper(x, y):
                    return x + y
            """,
        })
        cache = SymbolCache()
        stubs_dir = generate_project_stubs(index, cache)

        assert stubs_dir is not None
        assert stubs_dir == str(root / STUBS_DIR_NAME)

        stub_file = root / STUBS_DIR_NAME / "project" / "library" / "utils.pyi"
        assert stub_file.exists()
        content = stub_file.read_text()
        assert "def helper(x, y) -> Any: ..." in content

    def test_generates_stubs_for_class(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "project.models": """\
                class TagConfig:
                    name = "default"
                    def get_path(self, base):
                        return base + self.name
            """,
        })
        cache = SymbolCache()
        stubs_dir = generate_project_stubs(index, cache)

        stub_file = root / STUBS_DIR_NAME / "project" / "models.pyi"
        assert stub_file.exists()
        content = stub_file.read_text()
        assert "class TagConfig:" in content
        assert "name: Any" in content
        assert "def get_path(self, base) -> Any: ..." in content

    def test_generates_stubs_for_variables(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "project.constants": """\
                MAX_RETRIES = 3
                TIMEOUT = 30.0
            """,
        })
        cache = SymbolCache()
        generate_project_stubs(index, cache)

        stub_file = root / STUBS_DIR_NAME / "project" / "constants.pyi"
        content = stub_file.read_text()
        assert "MAX_RETRIES: Any" in content
        assert "TIMEOUT: Any" in content

    def test_preserves_return_type_hints(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "project.typed": """\
                def get_count() -> int:
                    return 42
            """,
        })
        cache = SymbolCache()
        generate_project_stubs(index, cache)

        stub_file = root / STUBS_DIR_NAME / "project" / "typed.pyi"
        content = stub_file.read_text()
        assert "def get_count() -> int: ..." in content
        # Should not need "from typing import Any" if all types are explicit
        # (but variables would still need it — this module has no variables)

    def test_creates_init_pyi_for_packages(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "project.library.utils": """\
                def helper():
                    pass
            """,
        })
        cache = SymbolCache()
        generate_project_stubs(index, cache)

        assert (root / STUBS_DIR_NAME / "project" / "__init__.pyi").exists()
        assert (root / STUBS_DIR_NAME / "project" / "library" / "__init__.pyi").exists()

    def test_single_part_module_path(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "utilities": """\
                def do_stuff():
                    pass
            """,
        })
        cache = SymbolCache()
        generate_project_stubs(index, cache)

        stub_file = root / STUBS_DIR_NAME / "utilities.pyi"
        assert stub_file.exists()
        content = stub_file.read_text()
        assert "def do_stuff() -> Any: ..." in content

    def test_skips_non_file_scripts(self, tmp_path):
        """Scripts with script_key != '__file__' (embedded JSON scripts) are skipped."""
        root = tmp_path / "myproject"
        root.mkdir()
        (root / "project.json").write_text('{"title": "MyProject"}')

        index = ProjectIndex(root_path=str(root))
        index.scripts.append(
            ScriptLocation(
                file_path=str(root / "view.json"),
                script_key="onActionPerformed",
                line_number=5,
                module_path="views.main",
                resource_type="perspective-view",
            )
        )

        cache = SymbolCache()
        result = generate_project_stubs(index, cache)
        assert result is None

    def test_returns_none_for_empty_index(self):
        index = ProjectIndex(root_path="/nonexistent")
        cache = SymbolCache()
        assert generate_project_stubs(index, cache) is None

    def test_returns_none_for_no_scripts(self):
        index = ProjectIndex(root_path="/nonexistent")
        index.scripts = []
        cache = SymbolCache()
        assert generate_project_stubs(index, cache) is None

    def test_multiple_modules(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "core.util.secrets": """\
                def get_secret(key):
                    pass
            """,
            "testing.decorators": """\
                def test(func):
                    return func
            """,
        })
        cache = SymbolCache()
        stubs_dir = generate_project_stubs(index, cache)
        assert stubs_dir is not None

        assert (root / STUBS_DIR_NAME / "core" / "util" / "secrets.pyi").exists()
        assert (root / STUBS_DIR_NAME / "testing" / "decorators.pyi").exists()
        # Package inits
        assert (root / STUBS_DIR_NAME / "core" / "__init__.pyi").exists()
        assert (root / STUBS_DIR_NAME / "core" / "util" / "__init__.pyi").exists()
        assert (root / STUBS_DIR_NAME / "testing" / "__init__.pyi").exists()


# ── Gitignore Tests ──────────────────────────────────────────────────


class TestGitignore:
    def test_creates_gitignore_if_missing(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "project.utils": "def f(): pass\n",
        })
        cache = SymbolCache()
        generate_project_stubs(index, cache)

        gitignore = root / ".gitignore"
        assert gitignore.exists()
        assert f"/{STUBS_DIR_NAME}/" in gitignore.read_text()

    def test_appends_to_existing_gitignore(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "project.utils": "def f(): pass\n",
        })
        gitignore = root / ".gitignore"
        gitignore.write_text("*.pyc\n__pycache__/\n")

        cache = SymbolCache()
        generate_project_stubs(index, cache)

        content = gitignore.read_text()
        assert "*.pyc" in content
        assert f"/{STUBS_DIR_NAME}/" in content

    def test_does_not_duplicate_gitignore_entry(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "project.utils": "def f(): pass\n",
        })
        gitignore = root / ".gitignore"
        gitignore.write_text(f"/{STUBS_DIR_NAME}/\n")

        cache = SymbolCache()
        generate_project_stubs(index, cache)

        content = gitignore.read_text()
        assert content.count(STUBS_DIR_NAME) == 1

    def test_recognizes_variant_gitignore_entries(self, tmp_path):
        """Should not duplicate if .ignition-stubs or .ignition-stubs/ already present."""
        root, index = _make_project(tmp_path, {
            "project.utils": "def f(): pass\n",
        })
        gitignore = root / ".gitignore"
        gitignore.write_text(f"{STUBS_DIR_NAME}/\n")

        cache = SymbolCache()
        generate_project_stubs(index, cache)

        content = gitignore.read_text()
        assert content.count(STUBS_DIR_NAME) == 1


# ── Stub Content Tests ───────────────────────────────────────────────


class TestStubContent:
    def test_function_with_type_annotations(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "project.typed": """\
                def process(data: str, count: int = 5) -> bool:
                    return True
            """,
        })
        cache = SymbolCache()
        generate_project_stubs(index, cache)

        stub = (root / STUBS_DIR_NAME / "project" / "typed.pyi").read_text()
        assert "def process(data, count) -> bool: ..." in stub

    def test_class_with_bases(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "project.models": """\
                class CustomError(Exception):
                    def __init__(self, msg):
                        self.msg = msg
            """,
        })
        cache = SymbolCache()
        generate_project_stubs(index, cache)

        stub = (root / STUBS_DIR_NAME / "project" / "models.pyi").read_text()
        assert "class CustomError(Exception):" in stub
        assert "def __init__(self, msg) -> Any: ..." in stub

    def test_empty_module_produces_no_stub(self, tmp_path):
        root, index = _make_project(tmp_path, {
            "project.empty": """\
                # Just a comment, no symbols
            """,
        })
        cache = SymbolCache()
        result = generate_project_stubs(index, cache)
        # No stubs generated since there are no symbols
        assert result is None

    def test_skips_parse_errors(self, tmp_path):
        """Modules with syntax errors are skipped gracefully."""
        root, index = _make_project(tmp_path, {
            "project.broken": """\
                def this is broken syntax
            """,
            "project.good": """\
                def works():
                    pass
            """,
        })
        cache = SymbolCache()
        stubs_dir = generate_project_stubs(index, cache)
        assert stubs_dir is not None

        # Broken module should not have a stub
        assert not (root / STUBS_DIR_NAME / "project" / "broken.pyi").exists()
        # Good module should
        assert (root / STUBS_DIR_NAME / "project" / "good.pyi").exists()
