"""Definition provider for Ignition scripts and API functions.

Resolves go-to-definition requests for:
1. system.* API functions -> jump to the function entry in the api_db/ JSON file
2. project.*/shared.* references -> jump to the script source file via ProjectIndex
"""

import json
import logging
from pathlib import Path
from typing import Optional

from lsprotocol.types import Location, Position, Range
from pygls.workspace import TextDocument

from .api_loader import APIFunction, IgnitionAPILoader
from .project_scanner import ProjectIndex, ScriptLocation
from .script_symbols import SymbolCache

logger = logging.getLogger(__name__)


def get_definition(
    document: TextDocument,
    position: Position,
    api_loader: Optional[IgnitionAPILoader],
    project_index: Optional[ProjectIndex],
    symbol_cache: Optional[SymbolCache] = None,
) -> Optional[Location]:
    """Resolve go-to-definition for the identifier at position.

    Tries system.* API lookup first, then project script lookup.
    """
    word = _get_word_at_position(document, position)
    if not word:
        return None

    logger.info(f"Definition requested for: '{word}'")

    # 1. Try system.* API function definition
    if api_loader is not None:
        loc = _resolve_api_function(word, api_loader)
        if loc is not None:
            return loc

    # 2. Try project/shared script definition
    if project_index is not None:
        loc = _resolve_project_script(word, project_index, symbol_cache)
        if loc is not None:
            return loc

    return None


def _get_word_at_position(document: TextDocument, position: Position) -> str:
    """Extract the full dotted identifier at the cursor position.

    Reuses the same logic as hover.py's get_word_at_position.
    """
    line = document.lines[position.line]
    character = position.character

    start = character
    while start > 0 and (line[start - 1].isalnum() or line[start - 1] in "._"):
        start -= 1

    end = character
    while end < len(line) and (line[end].isalnum() or line[end] in "._"):
        end += 1

    return line[start:end].strip()


def _resolve_api_function(
    word: str, api_loader: IgnitionAPILoader
) -> Optional[Location]:
    """Resolve a system.* function to its definition in the api_db/ JSON file.

    Finds the JSON file containing the function and the line number of
    the function's "name" key, so the user jumps directly to the entry.
    """
    # Try full name match (e.g., "system.tag.readBlocking")
    func = api_loader.get_function(word)

    # Try bare name match (e.g., just "readBlocking")
    if func is None and "." not in word:
        for _, candidate in api_loader.api_db.items():
            if candidate.name == word:
                func = candidate
                break

    if func is None:
        return None

    return _api_function_location(func)


def _api_function_location(func: APIFunction) -> Optional[Location]:
    """Build an LSP Location pointing to the function's entry in its api_db JSON file."""
    # Derive the JSON file path from the module name
    # "system.tag" -> "system_tag.json"
    module_filename = func.module.replace(".", "_") + ".json"
    json_path = Path(__file__).parent / "api_db" / module_filename

    if not json_path.is_file():
        logger.debug(f"API JSON file not found: {json_path}")
        return None

    # Find the line number of this function's "name" entry
    line_number = _find_function_line(json_path, func.name)

    return Location(
        uri=json_path.as_uri(),
        range=Range(
            start=Position(line=line_number, character=0),
            end=Position(line=line_number, character=0),
        ),
    )


def _find_function_line(json_path: Path, function_name: str) -> int:
    """Find the 0-based line number of a function's "name" key in a JSON file."""
    try:
        text = json_path.read_text(encoding="utf-8")
    except OSError:
        return 0

    # Search for the pattern: "name": "functionName"
    target = f'"name": "{function_name}"'
    for i, line in enumerate(text.splitlines()):
        if target in line:
            return i

    return 0


def _resolve_project_script(
    word: str,
    project_index: ProjectIndex,
    symbol_cache: Optional[SymbolCache] = None,
) -> Optional[Location]:
    """Resolve a project.*/shared.* reference to its source file location.

    Tries progressively shorter prefixes: if the cursor is on
    "project.library.utils.doStuff", we try the full string first,
    then "project.library.utils", then "project.library", etc.

    When a leaf module is found and there are remaining segments past the
    module path, looks up the symbol in the file and jumps to its line.
    """
    # Try the word and progressively shorter prefixes
    candidate = word
    while "." in candidate:
        loc = project_index.find_by_module_path(candidate)
        if loc is not None:
            # Check if the original word has symbols past this module path
            if symbol_cache is not None and loc.script_key == "__file__" and word != candidate:
                remaining = word[len(candidate) + 1:]  # e.g., "doStuff" or "MyClass.method"
                symbol_loc = _resolve_symbol_in_file(loc, remaining, symbol_cache)
                if symbol_loc is not None:
                    return symbol_loc
            return _script_location_to_lsp(loc)

        # Try prefix match — if this candidate uniquely matches one script, jump to it
        matches = project_index.search_module_paths(candidate)
        if len(matches) == 1:
            return _script_location_to_lsp(matches[0])

        # Strip the last segment and try again
        candidate = candidate.rsplit(".", 1)[0]

    return None


def _resolve_symbol_in_file(
    loc: ScriptLocation, symbol_name: str, symbol_cache: SymbolCache
) -> Optional[Location]:
    """Look up a symbol by name in a script file and return its Location.

    Handles dotted names like "ClassName.method" by looking up the class
    first, then the method within it.

    Falls back to None if the symbol isn't found (caller falls back to file line 1).
    """
    symbols = symbol_cache.get(loc.file_path, loc.module_path)
    if symbols.parse_error:
        return None

    parts = symbol_name.split(".", 1)
    name = parts[0]

    # Check functions
    for func in symbols.functions:
        if func.name == name:
            return Location(
                uri=f"file://{loc.file_path}",
                range=Range(
                    start=Position(line=func.line_number - 1, character=0),
                    end=Position(line=func.line_number - 1, character=0),
                ),
            )

    # Check classes
    for cls in symbols.classes:
        if cls.name == name:
            # If there's a method after the class name, jump to the method
            if len(parts) > 1:
                method_name = parts[1]
                for method in cls.methods:
                    if method.name == method_name:
                        return Location(
                            uri=f"file://{loc.file_path}",
                            range=Range(
                                start=Position(line=method.line_number - 1, character=0),
                                end=Position(line=method.line_number - 1, character=0),
                            ),
                        )
            # Jump to the class definition
            return Location(
                uri=f"file://{loc.file_path}",
                range=Range(
                    start=Position(line=cls.line_number - 1, character=0),
                    end=Position(line=cls.line_number - 1, character=0),
                ),
            )

    # Check variables
    for var in symbols.variables:
        if var.name == name:
            return Location(
                uri=f"file://{loc.file_path}",
                range=Range(
                    start=Position(line=var.line_number - 1, character=0),
                    end=Position(line=var.line_number - 1, character=0),
                ),
            )

    return None


def _script_location_to_lsp(loc: ScriptLocation) -> Location:
    """Convert a ScriptLocation to an LSP Location."""
    line = max(0, loc.line_number - 1)  # Convert 1-based to 0-based
    return Location(
        uri=f"file://{loc.file_path}",
        range=Range(
            start=Position(line=line, character=0),
            end=Position(line=line, character=0),
        ),
    )
