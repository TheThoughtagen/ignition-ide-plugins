"""Workspace symbol provider for Ignition project scripts.

Converts the ProjectIndex into LSP SymbolInformation results,
allowing users to search across all scripts in their Ignition project
via workspace/symbol requests (e.g., Telescope lsp_workspace_symbols).
"""

import logging
from pathlib import PurePosixPath
from typing import List, Optional

from lsprotocol.types import (
    Location,
    Position,
    Range,
    SymbolInformation,
    SymbolKind,
)

from ignition_lsp.project_scanner import ProjectIndex, ScriptLocation

logger = logging.getLogger(__name__)


def get_workspace_symbols(
    query: str,
    project_index: Optional[ProjectIndex],
) -> List[SymbolInformation]:
    """Return workspace symbols matching the query string.

    Args:
        query: Filter string from the client. Empty string means "all symbols".
        project_index: The current project index, or None if not yet built.

    Returns:
        List of SymbolInformation matching the query.
    """
    if project_index is None:
        return []

    symbols: List[SymbolInformation] = []

    for loc in project_index.scripts:
        name = _symbol_name(loc)
        # Case-insensitive substring match (LSP spec: client may do further filtering)
        if query and query.lower() not in name.lower():
            continue

        symbols.append(_to_symbol_info(loc, name))

    return symbols


def _symbol_name(loc: ScriptLocation) -> str:
    """Derive a human-readable symbol name from a ScriptLocation.

    - Python files: use module_path (e.g., "project.library.utils")
    - Embedded scripts: combine context_name and script_key
      (e.g., "Button_1.onActionPerformed")
    """
    if loc.script_key == "__file__":
        return loc.module_path or PurePosixPath(loc.file_path).stem

    if loc.context_name:
        return f"{loc.context_name}.{loc.script_key}"

    return loc.script_key


def _symbol_kind(loc: ScriptLocation) -> SymbolKind:
    """Map a ScriptLocation to an LSP SymbolKind.

    - Python script modules -> Module
    - Event handlers (onActionPerformed, onChange, etc.) -> Event
    - Transform scripts -> Function
    - Generic "script" / "code" keys -> Function
    """
    if loc.script_key == "__file__":
        return SymbolKind.Module

    if loc.script_key.startswith("on"):
        return SymbolKind.Event

    return SymbolKind.Function


def _to_symbol_info(loc: ScriptLocation, name: str) -> SymbolInformation:
    """Convert a ScriptLocation into an LSP SymbolInformation."""
    line = max(0, loc.line_number - 1)  # LSP uses 0-based lines

    return SymbolInformation(
        name=name,
        kind=_symbol_kind(loc),
        location=Location(
            uri=f"file://{loc.file_path}",
            range=Range(
                start=Position(line=line, character=0),
                end=Position(line=line, character=0),
            ),
        ),
        container_name=loc.resource_type,
    )
