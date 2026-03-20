"""Python stdlib scope tracking for import detection and completion context."""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from lsprotocol.types import Position
from pygls.workspace import TextDocument

from .pylib_loader import PyClass, PylibLoader, PyModule

logger = logging.getLogger(__name__)

# Regex patterns for Python import statements
# "from json import loads, dumps"
# "from collections import OrderedDict as OD"
_FROM_IMPORT_RE = re.compile(
    r"^\s*from\s+([\w.]+)\s+import\s+(.+)$"
)
# "import json"
# "import json as j"
# "import os.path"
_IMPORT_RE = re.compile(
    r"^\s*import\s+([\w.]+)(?:\s+as\s+(\w+))?\s*$"
)
# Multi-module import: "import json, csv, re"
_IMPORT_MULTI_RE = re.compile(
    r"^\s*import\s+(.+)$"
)


class PylibContextType(Enum):
    """Types of Python stdlib completion contexts."""

    IMPORT_MODULE = "import_module"      # import j|  -> suggest module names
    FROM_MODULE = "from_module"          # from json import |  -> suggest module members
    MODULE_MEMBER = "module_member"      # json.lo|  -> suggest functions/classes
    CLASS_MEMBER = "class_member"        # json.JSONEncoder.en| -> suggest class methods
    BUILTIN = "builtin"                  # le|  -> suggest built-in functions (lowest priority)


@dataclass
class PylibContext:
    """Describes the Python stdlib completion context at cursor."""

    type: PylibContextType
    module: Optional[PyModule] = None
    py_class: Optional[PyClass] = None
    partial: str = ""


@dataclass
class ImportedName:
    """Tracks what a local name refers to from a pylib import."""

    module: PyModule
    # If importing a specific member: the function, class, or constant name
    member_name: Optional[str] = None


def scan_pylib_imports(
    document: TextDocument, pylib_loader: PylibLoader
) -> Dict[str, ImportedName]:
    """Scan document for Python stdlib import statements.

    Returns a mapping of local name -> ImportedName for recognized imports.
    Example: {"json": ImportedName(module=json_module),
              "loads": ImportedName(module=json_module, member_name="loads")}
    """
    result: Dict[str, ImportedName] = {}

    for line in document.lines:
        line = line.rstrip("\n\r")

        # Skip comments and empty lines
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue

        # Try "from module import name1, name2"
        m = _FROM_IMPORT_RE.match(line)
        if m:
            module_name = m.group(1)
            imports_str = m.group(2)
            _parse_from_import(module_name, imports_str, pylib_loader, result)
            continue

        # Try "import module" or "import module as alias"
        m = _IMPORT_RE.match(line)
        if m:
            module_name = m.group(1)
            alias = m.group(2)
            _parse_direct_import(module_name, alias, pylib_loader, result)
            continue

        # Try multi-module "import json, csv, re"
        m = _IMPORT_MULTI_RE.match(line)
        if m:
            imports_str = m.group(1)
            # Only process if it looks like multiple comma-separated modules
            if "," in imports_str:
                for item in imports_str.split(","):
                    item = item.strip()
                    if not item:
                        continue
                    # Handle "module as alias"
                    as_match = re.match(r"([\w.]+)\s+as\s+(\w+)", item)
                    if as_match:
                        mod_name = as_match.group(1)
                        alias = as_match.group(2)
                    else:
                        mod_name = item.split()[0] if item.split() else item
                        alias = None
                    _parse_direct_import(mod_name, alias, pylib_loader, result)

    return result


def _parse_from_import(
    module_name: str,
    imports_str: str,
    pylib_loader: PylibLoader,
    result: Dict[str, ImportedName],
) -> None:
    """Parse 'from module import a, b, c as d' into result dict."""
    module = pylib_loader.get_module(module_name)
    if module is None:
        return

    for item in imports_str.split(","):
        item = item.strip()
        if not item:
            continue

        # Handle "name as alias"
        as_match = re.match(r"(\w+)\s+as\s+(\w+)", item)
        if as_match:
            member_name = as_match.group(1)
            alias = as_match.group(2)
        else:
            member_name = item.split()[0] if item.split() else item
            alias = member_name

        # Verify the member exists in the module
        found = False
        for f in module.functions:
            if f.name == member_name:
                found = True
                break
        if not found:
            for c in module.classes:
                if c.name == member_name:
                    found = True
                    break
        if not found:
            for const in module.constants:
                if const.name == member_name:
                    found = True
                    break

        if found:
            result[alias] = ImportedName(module=module, member_name=member_name)


def _parse_direct_import(
    module_name: str,
    alias: Optional[str],
    pylib_loader: PylibLoader,
    result: Dict[str, ImportedName],
) -> None:
    """Parse 'import json' or 'import json as j' into result dict."""
    module = pylib_loader.get_module(module_name)
    if module is None:
        return

    local_name = alias if alias else module_name
    # For "import os.path", the local name is "os.path" (or alias)
    # But for completion, we track the full module
    result[local_name] = ImportedName(module=module)


def detect_pylib_context(
    document: TextDocument,
    position: Position,
    pylib_loader: PylibLoader,
) -> Optional[PylibContext]:
    """Determine if cursor is in a Python stdlib completion context.

    Returns PylibContext describing the context, or None if not pylib-related.
    """
    line = document.lines[position.line]
    text_before = line[:position.character]

    # Check for import statement contexts first
    ctx = _detect_import_context(text_before, pylib_loader)
    if ctx:
        return ctx

    # Check for module member / class member contexts (imported names)
    ctx = _detect_member_context(text_before, document, pylib_loader)
    if ctx:
        return ctx

    return None


def _detect_import_context(
    text_before: str, pylib_loader: PylibLoader
) -> Optional[PylibContext]:
    """Detect import-related completion contexts.

    Handles:
        "import j"              -> IMPORT_MODULE with partial "j"
        "import "               -> IMPORT_MODULE
        "from json import "     -> FROM_MODULE (offer module members)
        "from json import lo"   -> FROM_MODULE with partial "lo"
        "from "                 -> IMPORT_MODULE
        "from j"                -> IMPORT_MODULE with partial "j"
    """
    stripped = text_before.strip()

    # "from module import name, ..." or "from module import "
    m = re.match(r"from\s+([\w.]+)\s+import\s*(.*)", stripped)
    if m:
        module_name = m.group(1)
        after_import = m.group(2)

        module = pylib_loader.get_module(module_name)
        if module:
            # Determine partial: last item after comma
            parts = after_import.split(",")
            partial = parts[-1].strip() if parts else ""
            return PylibContext(
                type=PylibContextType.FROM_MODULE,
                module=module,
                partial=partial,
            )
        return None

    # "from partial_name" (no "import" yet)
    m = re.match(r"from\s+([\w.]*)$", stripped)
    if m:
        partial = m.group(1)
        return PylibContext(
            type=PylibContextType.IMPORT_MODULE,
            partial=partial,
        )

    # "import partial_name" or "import "
    m = re.match(r"import\s+([\w.]+)$", stripped)
    if m:
        partial = m.group(1)
        return PylibContext(
            type=PylibContextType.IMPORT_MODULE,
            partial=partial,
        )
    # "import " with nothing after (empty partial)
    if re.match(r"import\s*$", stripped):
        return PylibContext(
            type=PylibContextType.IMPORT_MODULE,
            partial="",
        )

    return None


def _detect_member_context(
    text_before: str,
    document: TextDocument,
    pylib_loader: PylibLoader,
) -> Optional[PylibContext]:
    """Detect module member or class member completion contexts.

    Handles:
        "json."             where json is imported -> MODULE_MEMBER
        "json.lo"           partial member         -> MODULE_MEMBER with partial
        "json.JSONEncoder." class method access     -> CLASS_MEMBER
    """
    imported = scan_pylib_imports(document, pylib_loader)
    if not imported:
        return None

    stripped = text_before.rstrip()

    # Check for "name.something." or "name.something.partial" (class member)
    m = re.search(r"([\w.]+)\.(\w+)\.\s*(\w*)$", stripped)
    if m:
        mod_name = m.group(1)
        class_name = m.group(2)
        partial = m.group(3)
        if mod_name in imported:
            info = imported[mod_name]
            if info.member_name is None:
                # It's a module import, look for class
                for cls in info.module.classes:
                    if cls.name == class_name:
                        return PylibContext(
                            type=PylibContextType.CLASS_MEMBER,
                            module=info.module,
                            py_class=cls,
                            partial=partial,
                        )

    # Check for "name." or "name.partial" (module member)
    # Also handles dotted names like "os.path." from "import os.path"
    m = re.search(r"([\w.]+)\.\s*(\w*)$", stripped)
    if m:
        name = m.group(1)
        partial = m.group(2)
        if name in imported:
            info = imported[name]
            if info.member_name is None:
                # Module-level import: offer module members
                return PylibContext(
                    type=PylibContextType.MODULE_MEMBER,
                    module=info.module,
                    partial=partial,
                )
            else:
                # "from X import SomeClass" then "SomeClass." -> class member
                for cls in info.module.classes:
                    if cls.name == info.member_name:
                        return PylibContext(
                            type=PylibContextType.CLASS_MEMBER,
                            module=info.module,
                            py_class=cls,
                            partial=partial,
                        )

    return None
