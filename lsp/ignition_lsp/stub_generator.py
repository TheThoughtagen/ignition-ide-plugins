"""Auto-generate .pyi stub files for Ignition project scripts.

Generates type stubs in {project_root}/.ignition-stubs/ so that external
type checkers (pyright, basedpyright) can resolve project-internal imports
like `from core.util.secrets import get_secret`.

Reuses the SymbolCache already populated during project scanning — stub
generation is just string formatting on top of already-extracted AST data.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from ignition_lsp.project_scanner import ProjectIndex
from ignition_lsp.script_symbols import (
    ModuleSymbols,
    ScriptClass,
    ScriptFunction,
    ScriptVariable,
    SymbolCache,
)

logger = logging.getLogger(__name__)

STUBS_DIR_NAME = ".ignition-stubs"


def generate_project_stubs(
    project_index: ProjectIndex,
    symbol_cache: SymbolCache,
) -> Optional[str]:
    """Generate .pyi stub files for all script-python modules in the project.

    Returns the stubs directory path on success, or None if nothing was generated.
    """
    if not project_index or not project_index.scripts:
        return None

    stubs_dir = Path(project_index.root_path) / STUBS_DIR_NAME

    # Filter to actual .py modules (script_key == "__file__")
    py_scripts = [s for s in project_index.scripts if s.script_key == "__file__"]
    if not py_scripts:
        return None

    # Track which stub files we write so we can clean up stale ones
    written_paths: set = set()

    for script in py_scripts:
        symbols = symbol_cache.get(script.file_path, script.module_path)
        if symbols.parse_error:
            logger.debug(f"Skipping {script.module_path}: {symbols.parse_error}")
            continue

        stub_content = _generate_stub_content(symbols)
        if not stub_content:
            continue

        # Convert module_path (e.g., "project.library.utils") to file path
        parts = script.module_path.split(".")
        stub_path = stubs_dir / Path(*parts[:-1]) / f"{parts[-1]}.pyi" if len(parts) > 1 else stubs_dir / f"{parts[0]}.pyi"

        stub_path.parent.mkdir(parents=True, exist_ok=True)
        stub_path.write_text(stub_content, encoding="utf-8")
        written_paths.add(str(stub_path))

        # Create __init__.pyi for each intermediate package directory
        _ensure_init_stubs(stubs_dir, parts[:-1], written_paths)

    if not written_paths:
        return None

    _update_gitignore(project_index.root_path)
    _update_pyrightconfig(project_index.root_path)

    logger.info(
        f"Generated {len(written_paths)} stub files in {stubs_dir}"
    )
    return str(stubs_dir)


def _generate_stub_content(symbols: ModuleSymbols) -> str:
    """Generate .pyi stub content from extracted module symbols."""
    lines: list = []

    # Add typing import if needed
    needs_any = False
    for func in symbols.functions:
        if not func.returns:
            needs_any = True
            break
    if not needs_any:
        for cls in symbols.classes:
            for method in cls.methods:
                if not method.returns:
                    needs_any = True
                    break
    if not needs_any and symbols.variables:
        needs_any = True

    if needs_any:
        lines.append("from typing import Any")
        lines.append("")

    # Functions
    for func in symbols.functions:
        lines.append(_generate_function_stub(func))
        lines.append("")

    # Classes
    for cls in symbols.classes:
        lines.extend(_generate_class_stub(cls))
        lines.append("")

    # Variables
    for var in symbols.variables:
        lines.append(_generate_variable_stub(var))

    content = "\n".join(lines).rstrip() + "\n"
    # Don't emit stubs that are just the import line
    stripped = content.replace("from typing import Any", "").strip()
    if not stripped:
        return ""
    return content


def _generate_function_stub(func: ScriptFunction) -> str:
    """Generate a stub line for a function."""
    params = ", ".join(func.params)
    ret = func.returns if func.returns else "Any"
    return f"def {func.name}({params}) -> {ret}: ..."


def _generate_method_stub(method: ScriptFunction, indent: str = "    ") -> str:
    """Generate a stub line for a class method."""
    all_params = ["self"] + method.params if method.is_method else method.params
    params = ", ".join(all_params)
    ret = method.returns if method.returns else "Any"
    return f"{indent}def {method.name}({params}) -> {ret}: ..."


def _generate_class_stub(cls: ScriptClass) -> list:
    """Generate stub lines for a class."""
    lines = []
    bases = f"({', '.join(cls.bases)})" if cls.bases else ""
    lines.append(f"class {cls.name}{bases}:")

    has_body = False

    for var_name in cls.class_variables:
        lines.append(f"    {var_name}: Any")
        has_body = True

    for method in cls.methods:
        lines.append(_generate_method_stub(method))
        has_body = True

    if not has_body:
        lines.append("    ...")

    return lines


def _generate_variable_stub(var: ScriptVariable) -> str:
    """Generate a stub line for a module-level variable."""
    type_hint = var.type_hint if var.type_hint else "Any"
    return f"{var.name}: {type_hint}"


def _ensure_init_stubs(
    stubs_dir: Path, package_parts: list, written_paths: set
) -> None:
    """Create __init__.pyi for each intermediate package directory."""
    current = stubs_dir
    for part in package_parts:
        current = current / part
        init_path = current / "__init__.pyi"
        if not init_path.exists():
            current.mkdir(parents=True, exist_ok=True)
            init_path.write_text("", encoding="utf-8")
        written_paths.add(str(init_path))


def _update_gitignore(root_path: str) -> None:
    """Append .ignition-stubs/ to .gitignore if not already present."""
    gitignore_path = Path(root_path) / ".gitignore"
    entry = f"/{STUBS_DIR_NAME}/"

    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        # Check for the entry with or without leading slash
        for line in content.splitlines():
            stripped = line.strip()
            if stripped in (entry, STUBS_DIR_NAME, f"{STUBS_DIR_NAME}/"):
                return  # Already present
        # Append with a newline separator
        if not content.endswith("\n"):
            content += "\n"
        content += f"{entry}\n"
        gitignore_path.write_text(content, encoding="utf-8")
    else:
        gitignore_path.write_text(f"{entry}\n", encoding="utf-8")


def _update_pyrightconfig(root_path: str) -> None:
    """Create or update pyrightconfig.json so Pyright can find .ignition-stubs/."""
    config_path = Path(root_path) / "pyrightconfig.json"
    stubs_entry = f".{STUBS_DIR_NAME.lstrip('.')}"  # ".ignition-stubs"

    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning(f"Could not parse {config_path}, skipping pyrightconfig update")
            return
    else:
        config = {}

    extra_paths = config.get("extraPaths", [])
    if stubs_entry not in extra_paths:
        extra_paths.append(stubs_entry)
        config["extraPaths"] = extra_paths

    config.setdefault("reportMissingImports", "warning")
    config.setdefault("reportMissingModuleSource", "none")

    config_path.write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
