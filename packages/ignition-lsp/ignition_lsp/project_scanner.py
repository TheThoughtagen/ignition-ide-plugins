"""Project scanner for Ignition project directories.

Walks an Ignition project tree, finding all resource.json, view.json,
and .py files that contain scripts. Builds a ScriptLocation index for
use by workspace symbols, go-to-definition, and cross-file completions.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# JSON keys that contain embedded scripts (mirrors lua/ignition/json_parser.lua SCRIPT_KEYS)
SCRIPT_KEYS = frozenset({
    "script",
    "code",
    "eventScript",
    "transform",
    "onActionPerformed",
    "onChange",
    "onStartup",
    "onShutdown",
})

# File patterns to scan for embedded scripts
SCRIPT_JSON_FILES = {"resource.json", "view.json", "tags.json", "data.json"}

# Known Ignition resource directories and their types
RESOURCE_TYPE_DIRS = {
    "script-python": "script-python",
    "named-query": "named-query",
    "perspective-views": "perspective-view",
    "vision-windows": "vision-window",
}


@dataclass
class ScriptLocation:
    """A single script location within the project."""

    file_path: str  # Absolute path to the file containing the script
    script_key: str  # JSON key (e.g., "script", "onActionPerformed") or "__file__" for .py
    line_number: int  # 1-based line number in the source file
    module_path: str  # Logical path (e.g., "project.library.utils")
    resource_type: str  # "script-python", "perspective-view", etc.
    context_name: str = ""  # Component/tag name context (e.g., "Button_1")


@dataclass
class ProjectIndex:
    """Index of all scripts in an Ignition project."""

    root_path: str
    scripts: List[ScriptLocation] = field(default_factory=list)
    parent_roots: List[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None

    @property
    def script_count(self) -> int:
        return len(self.scripts)

    def scripts_by_type(self) -> Dict[str, List[ScriptLocation]]:
        """Group scripts by resource type."""
        result: Dict[str, List[ScriptLocation]] = {}
        for loc in self.scripts:
            result.setdefault(loc.resource_type, []).append(loc)
        return result

    def scripts_in_file(self, file_path: str) -> List[ScriptLocation]:
        """Get all scripts in a specific file."""
        return [s for s in self.scripts if s.file_path == file_path]

    def find_by_module_path(self, module_path: str) -> Optional[ScriptLocation]:
        """Find a script by its logical module path."""
        for loc in self.scripts:
            if loc.module_path == module_path:
                return loc
        return None

    def search_module_paths(self, prefix: str) -> List[ScriptLocation]:
        """Find all scripts whose module_path starts with prefix."""
        return [s for s in self.scripts if s.module_path.startswith(prefix)]


class ProjectScanner:
    """Scans an Ignition project directory to build a script index."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path).resolve()

    def is_ignition_project(self) -> bool:
        """Check if root_path looks like an Ignition project."""
        return (self.root_path / "project.json").is_file()

    def scan(self) -> ProjectIndex:
        """Scan the project and return a complete index."""
        index = ProjectIndex(root_path=str(self.root_path))

        if not self.is_ignition_project():
            logger.warning(f"No project.json found at {self.root_path}")
            return index

        logger.info(f"Scanning Ignition project at {self.root_path}")

        # 1. Scan this project's directories
        self._scan_project_dir(index)

        # 2. Collect and merge parent scripts
        parent_chain = self._collect_parent_scripts(set())
        if parent_chain:
            child_module_paths = {s.module_path for s in index.scripts}
            for parent_root, parent_scripts in parent_chain:
                index.parent_roots.append(parent_root)
                for script in parent_scripts:
                    # Child overrides parent: skip if module_path already exists
                    if script.module_path not in child_module_paths:
                        index.scripts.append(script)
                        child_module_paths.add(script.module_path)

        index.last_updated = datetime.now()
        logger.info(
            f"Scan complete: {index.script_count} scripts found "
            f"in {len(index.scripts_by_type())} resource types"
        )
        return index

    def _scan_project_dir(self, index: ProjectIndex) -> None:
        """Scan this project's directories into the index."""
        ignition_dir = self.root_path / "ignition"
        if ignition_dir.is_dir():
            self._scan_ignition_dir(ignition_dir, index)

        # Also scan root for view.json / resource.json at top level
        # (some project exports have flattened structures)
        for json_file in self.root_path.glob("*.json"):
            if json_file.name in SCRIPT_JSON_FILES:
                self._scan_json_file(json_file, "unknown", "", index)

    def _read_project_json(self) -> Optional[Dict]:
        """Parse project.json and return its contents."""
        project_file = self.root_path / "project.json"
        if not project_file.is_file():
            return None
        try:
            return json.loads(project_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"Could not read project.json at {self.root_path}: {e}")
            return None

    def _resolve_parent_path(self, parent_name: str) -> Optional[Path]:
        """Find the parent project directory by name.

        Searches sibling directories for a project.json whose 'title' matches,
        falling back to a sibling directory whose name matches.
        """
        siblings_dir = self.root_path.parent
        if not siblings_dir.is_dir():
            return None

        # First pass: look for project.json with matching title
        for child in sorted(siblings_dir.iterdir()):
            if not child.is_dir() or child == self.root_path:
                continue
            pj = child / "project.json"
            if pj.is_file():
                try:
                    data = json.loads(pj.read_text(encoding="utf-8"))
                    if data.get("title") == parent_name:
                        return child
                except (json.JSONDecodeError, OSError):
                    continue

        # Fallback: match directory name
        candidate = siblings_dir / parent_name
        if candidate.is_dir() and candidate != self.root_path:
            return candidate

        return None

    def _collect_parent_scripts(
        self, visited: set,
    ) -> List[tuple]:
        """Recursively collect scripts from parent projects.

        Returns list of (root_path_str, scripts_list) tuples,
        deepest ancestor first (so closer parents override).
        Uses visited set for cycle detection.
        """
        project_data = self._read_project_json()
        if not project_data:
            return []

        parent_name = project_data.get("parent")
        if not parent_name:
            return []

        parent_path = self._resolve_parent_path(parent_name)
        if parent_path is None:
            logger.warning(
                f"Parent project '{parent_name}' not found for {self.root_path}"
            )
            return []

        parent_str = str(parent_path.resolve())
        if parent_str in visited:
            logger.warning(
                f"Cycle detected in project hierarchy: {parent_name} at {parent_str}"
            )
            return []

        visited.add(parent_str)

        # Scan parent project
        parent_scanner = ProjectScanner(parent_str)
        parent_index = ProjectIndex(root_path=parent_str)
        if parent_scanner.is_ignition_project():
            parent_scanner._scan_project_dir(parent_index)

        # Recurse into grandparent (deepest first)
        result = parent_scanner._collect_parent_scripts(visited)
        # Append this parent's scripts last (closer parent overrides)
        result.append((parent_str, parent_index.scripts))
        return result

    def _scan_ignition_dir(self, ignition_dir: Path, index: ProjectIndex) -> None:
        """Scan the ignition/ subdirectory."""
        for child in sorted(ignition_dir.iterdir()):
            if not child.is_dir():
                continue

            resource_type = RESOURCE_TYPE_DIRS.get(child.name, child.name)

            if child.name == "script-python":
                self._scan_script_python_dir(child, resource_type, index)
            else:
                self._scan_resource_dir(child, resource_type, index)

    def _scan_script_python_dir(
        self, base_dir: Path, resource_type: str, index: ProjectIndex
    ) -> None:
        """Scan script-python/ for .py files and resource.json files."""
        for root, _dirs, files in os.walk(base_dir):
            root_path = Path(root)

            for filename in files:
                file_path = root_path / filename

                if filename.endswith(".py"):
                    module_path = self._compute_module_path(file_path, base_dir)
                    index.scripts.append(
                        ScriptLocation(
                            file_path=str(file_path),
                            script_key="__file__",
                            line_number=1,
                            module_path=module_path,
                            resource_type=resource_type,
                        )
                    )

                elif filename in SCRIPT_JSON_FILES:
                    module_path = self._compute_module_path(file_path, base_dir)
                    self._scan_json_file(file_path, resource_type, module_path, index)

    def _scan_resource_dir(
        self, base_dir: Path, resource_type: str, index: ProjectIndex
    ) -> None:
        """Scan a resource directory (perspectives, vision, queries, etc.)."""
        for root, _dirs, files in os.walk(base_dir):
            root_path = Path(root)

            for filename in files:
                if filename in SCRIPT_JSON_FILES or filename.endswith(".json"):
                    file_path = root_path / filename
                    module_path = self._compute_module_path(file_path, base_dir)
                    self._scan_json_file(file_path, resource_type, module_path, index)

    # Skip JSON files larger than this (tag exports like tags.json/udts.json
    # can be tens of MB and are not useful to index for script completions)
    _MAX_JSON_SIZE = 1_000_000  # 1 MB

    def _scan_json_file(
        self,
        file_path: Path,
        resource_type: str,
        module_path: str,
        index: ProjectIndex,
    ) -> None:
        """Scan a single JSON file for embedded scripts."""
        try:
            size = file_path.stat().st_size
            if size > self._MAX_JSON_SIZE:
                logger.debug(f"Skipping large file ({size} bytes): {file_path}")
                return
            text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.debug(f"Could not read {file_path}: {e}")
            return

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.debug(f"Invalid JSON in {file_path}")
            return

        # Find all script keys by walking the JSON tree
        locations = self._find_scripts_in_json(data, text, str(file_path))

        for script_key, line_number, context_name in locations:
            index.scripts.append(
                ScriptLocation(
                    file_path=str(file_path),
                    script_key=script_key,
                    line_number=line_number,
                    module_path=module_path,
                    resource_type=resource_type,
                    context_name=context_name,
                )
            )

    def _find_scripts_in_json(
        self, data: object, raw_text: str, file_path: str
    ) -> List[tuple]:
        """Walk a parsed JSON structure to find all script keys.

        Returns list of (script_key, line_number, context_name) tuples.
        """
        results: List[tuple] = []
        self._walk_json(data, raw_text, results, context_name="")
        return results

    def _walk_json(
        self,
        node: object,
        raw_text: str,
        results: List[tuple],
        context_name: str,
    ) -> None:
        """Recursively walk JSON to find script key/value pairs."""
        if isinstance(node, dict):
            # Track context from "meta.name" or "name" fields
            name = ""
            if "meta" in node and isinstance(node["meta"], dict):
                name = node["meta"].get("name", "")
            elif "name" in node and isinstance(node["name"], str):
                name = node["name"]

            current_context = name or context_name

            for key, value in node.items():
                if key in SCRIPT_KEYS and isinstance(value, str) and value.strip():
                    line_num = self._find_key_line(raw_text, key, value)
                    results.append((key, line_num, current_context))
                elif key in SCRIPT_KEYS and isinstance(value, dict):
                    # Nested script object like {"script": "...", "enabled": true}
                    inner_script = value.get("script", "")
                    if isinstance(inner_script, str) and inner_script.strip():
                        line_num = self._find_key_line(raw_text, "script", inner_script)
                        results.append((key, line_num, current_context))
                else:
                    self._walk_json(value, raw_text, results, current_context)

        elif isinstance(node, list):
            for item in node:
                self._walk_json(item, raw_text, results, context_name)

    def _find_key_line(self, raw_text: str, key: str, value_prefix: str) -> int:
        """Find the line number of a script key in raw JSON text.

        Searches for the pattern `"key": "value_start...` to locate the line.
        Returns 1-based line number, or 1 if not found.
        """
        # Build a search pattern: "key": " followed by start of value
        search_key = f'"{key}"'
        # Use the first 40 chars of the value for matching (avoid huge strings)
        value_start = value_prefix[:40].replace("\n", "\\n")

        lines = raw_text.splitlines()
        for i, line in enumerate(lines, 1):
            if search_key in line and value_start[:20] in line:
                return i

        # Fallback: just find the key
        for i, line in enumerate(lines, 1):
            if search_key in line:
                return i

        return 1

    def _compute_module_path(self, file_path: Path, base_dir: Path) -> str:
        """Compute the logical module path for a file.

        Example:
            base_dir = /project/ignition/script-python
            file_path = /project/ignition/script-python/project-library/utils/code.py
            result = "project.library.utils"
        """
        try:
            rel = file_path.relative_to(base_dir)
        except ValueError:
            return file_path.stem

        # Remove filename, join directory parts with dots
        parts = list(rel.parent.parts)

        # Ignition convention: "project-library" -> "project.library"
        expanded = []
        for part in parts:
            if "-" in part:
                expanded.extend(part.split("-"))
            else:
                expanded.append(part)

        if not expanded or expanded == ["."]:
            return file_path.stem

        return ".".join(expanded)
