"""Hover provider for Ignition APIs."""

import logging
import re
from typing import Optional

from lsprotocol.types import Hover, HoverParams, MarkupContent, MarkupKind
from pygls.workspace import TextDocument

from .api_loader import IgnitionAPILoader
from .java_loader import JavaAPILoader
from .project_scanner import ProjectIndex
from .pylib_loader import PylibLoader
from .script_symbols import SymbolCache
from .uri_utils import is_expression_buffer

logger = logging.getLogger(__name__)


def get_word_at_position(document: TextDocument, position: HoverParams.position) -> str:
    """Get the full identifier at the cursor position."""
    line = document.lines[position.line]
    character = position.character

    # Find the start of the identifier (go backwards)
    start = character
    while start > 0 and (line[start - 1].isalnum() or line[start - 1] in "._"):
        start -= 1

    # Find the end of the identifier (go forwards)
    end = character
    while end < len(line) and (line[end].isalnum() or line[end] in "._"):
        end += 1

    word = line[start:end]
    return word


def get_hover_info(
    document: TextDocument,
    position: HoverParams.position,
    api_loader: IgnitionAPILoader,
    java_loader: Optional[JavaAPILoader] = None,
    project_index: Optional[ProjectIndex] = None,
    symbol_cache: Optional[SymbolCache] = None,
    pylib_loader: Optional[PylibLoader] = None,
) -> Optional[Hover]:
    """Get hover information for the word at position."""
    word = get_word_at_position(document, position)
    logger.info(f"Hover requested for: '{word}'")

    if not word:
        return None

    # Expression function hover for virtual expression buffers
    if is_expression_buffer(document.uri):
        return _get_expression_hover(word)

    # Try Java class/method hover first
    if java_loader is not None:
        java_hover = _get_java_hover(document, position, word, java_loader)
        if java_hover:
            return java_hover

    # Try Python stdlib hover
    if pylib_loader is not None:
        pylib_hover = _get_pylib_hover(word, document, pylib_loader)
        if pylib_hover:
            return pylib_hover

    # Try project symbol hover (functions/classes in project .py files)
    if project_index is not None and symbol_cache is not None:
        project_hover = _get_project_symbol_hover(word, project_index, symbol_cache)
        if project_hover:
            return project_hover

    # Try to find the function in the API database
    func = api_loader.get_function(word)

    if func:
        # Found a function - return full documentation
        markdown = func.get_markdown_doc()

        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=markdown,
            )
        )

    # Check if it's a module (e.g., hovering over "system" or "system.tag")
    if word.startswith("system."):
        module_funcs = api_loader.get_module_functions(word)
        if module_funcs:
            func_names = [f.name for f in module_funcs[:10]]
            if len(module_funcs) > 10:
                func_names.append("...")

            markdown = f"**{word}**\n\nIgnition module with {len(module_funcs)} functions:\n\n"
            markdown += ", ".join(f"`{name}`" for name in func_names)

            return Hover(
                contents=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=markdown,
                )
            )

    # Check for partial matches (e.g., hovering over just "readBlocking" without "system.tag.")
    if "." not in word and word:
        # Search all functions for this name
        for full_name, func in api_loader.api_db.items():
            if func.name == word:
                markdown = func.get_markdown_doc()
                return Hover(
                    contents=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=markdown,
                    )
                )

    # No match found
    logger.debug(f"No hover info found for '{word}'")
    return None


def _get_project_symbol_hover(
    word: str,
    project_index: ProjectIndex,
    symbol_cache: SymbolCache,
) -> Optional[Hover]:
    """Get hover for a project script symbol.

    Splits word on dots, tries progressively shorter module paths.
    When a leaf module is found, looks up the remaining symbol name.

    Handles:
        - "module.functionName" -> function hover
        - "module.ClassName" -> class hover
        - "module.ClassName.method" -> method hover
        - "module.varName" -> variable hover
    """
    parts = word.split(".")
    # Try progressively shorter module paths
    for i in range(len(parts) - 1, 0, -1):
        module_path = ".".join(parts[:i])
        remaining = parts[i:]

        loc = project_index.find_by_module_path(module_path)
        if loc is None or loc.script_key != "__file__":
            continue

        symbols = symbol_cache.get(loc.file_path, loc.module_path)
        if symbols.parse_error:
            continue

        symbol_name = remaining[0]

        # Check functions
        for func in symbols.functions:
            if func.name == symbol_name:
                return Hover(
                    contents=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=func.get_markdown_doc(module_path),
                    )
                )

        # Check classes
        for cls in symbols.classes:
            if cls.name == symbol_name:
                # If there's a method name after the class name
                if len(remaining) > 1:
                    method_name = remaining[1]
                    for method in cls.methods:
                        if method.name == method_name:
                            return Hover(
                                contents=MarkupContent(
                                    kind=MarkupKind.Markdown,
                                    value=method.get_markdown_doc(f"{module_path}.{cls.name}"),
                                )
                            )
                # Just the class itself
                return Hover(
                    contents=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=cls.get_markdown_doc(module_path),
                    )
                )

        # Check variables
        for var in symbols.variables:
            if var.name == symbol_name:
                detail = var.name
                if var.type_hint:
                    detail += f": {var.type_hint}"
                if var.value_repr:
                    detail += f" = {var.value_repr}"
                md = f"**{module_path}.{var.name}**\n\n`{detail}`"
                return Hover(
                    contents=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=md,
                    )
                )

    return None


def _get_expression_hover(word: str) -> Optional[Hover]:
    """Get hover information for an Ignition expression function."""
    from .expression_functions import EXPRESSION_FUNCTIONS

    info = EXPRESSION_FUNCTIONS.get(word)
    if not info:
        return None

    params_md = ""
    if info.get("params"):
        params_md = "\n\n**Parameters:**\n"
        for p in info["params"]:
            opt = " *(optional)*" if p.get("optional") else ""
            params_md += f"- `{p['name']}`: {p['type']}{opt}\n"

    md = (
        f"**{info['signature']}**\n\n"
        f"{info['description']}"
        f"{params_md}\n\n"
        f"**Returns:** {info['return_type']}  \n"
        f"**Category:** {info['category']}"
    )

    return Hover(
        contents=MarkupContent(kind=MarkupKind.Markdown, value=md)
    )


def _get_java_hover(
    document: TextDocument,
    position,
    word: str,
    java_loader: JavaAPILoader,
) -> Optional[Hover]:
    """Get hover information for Java classes and methods.

    Handles:
        - Hovering on an imported class name -> class documentation
        - Hovering on ClassName.methodName -> method documentation
        - Hovering on a package in an import statement -> package summary
    """
    from .java_scope import scan_imports

    imported = scan_imports(document, java_loader)

    # Check for "ClassName.methodName" or "ClassName.FIELD_NAME"
    if "." in word:
        parts = word.split(".", 1)
        class_name = parts[0]
        member_name = parts[1]

        if class_name in imported:
            cls = imported[class_name]
            # Try method first
            md = cls.get_method_markdown(member_name)
            if md:
                return Hover(
                    contents=MarkupContent(kind=MarkupKind.Markdown, value=md)
                )
            # Try field
            md = cls.get_field_markdown(member_name)
            if md:
                return Hover(
                    contents=MarkupContent(kind=MarkupKind.Markdown, value=md)
                )

    # Check if word is an imported class name
    if word in imported:
        cls = imported[word]
        md = cls.get_markdown_doc()
        return Hover(
            contents=MarkupContent(kind=MarkupKind.Markdown, value=md)
        )

    # Check if hovering over a package name in an import statement
    line = document.lines[position.line].rstrip("\n\r")
    if line.strip().startswith(("from ", "import ")):
        # Check if word matches a known package
        for pkg in java_loader.get_all_packages():
            if word == pkg or pkg.endswith(f".{word}"):
                classes = java_loader.get_package_classes(pkg)
                class_names = [c.name for c in classes[:15]]
                if len(classes) > 15:
                    class_names.append("...")
                md = f"**{pkg}** (Java package)\n\n"
                md += f"{len(classes)} classes: {', '.join(f'`{n}`' for n in class_names)}"
                return Hover(
                    contents=MarkupContent(kind=MarkupKind.Markdown, value=md)
                )

    return None


def _get_pylib_hover(
    word: str,
    document: TextDocument,
    pylib_loader: PylibLoader,
) -> Optional[Hover]:
    """Get hover information for Python stdlib modules, functions, and classes.

    Handles:
        - Hovering on an imported module name -> module documentation
        - Hovering on module.function -> function documentation
        - Hovering on module.Class -> class documentation
        - Hovering on module.Class.method -> method documentation
        - Hovering on a builtin function name -> builtin documentation
    """
    from .pylib_scope import scan_pylib_imports

    imported = scan_pylib_imports(document, pylib_loader)

    # Check for dotted names like "json.loads" or "json.JSONEncoder.encode"
    if "." in word:
        parts = word.split(".")
        first = parts[0]

        if first in imported:
            info = imported[first]
            if info.member_name is None:
                # Module-level import: "json.loads" or "json.JSONEncoder.encode"
                module = info.module
                if len(parts) == 2:
                    member_name = parts[1]
                    # Try function
                    for func in module.functions:
                        if func.name == member_name:
                            return Hover(
                                contents=MarkupContent(
                                    kind=MarkupKind.Markdown,
                                    value=func.get_markdown_doc(module.name),
                                )
                            )
                    # Try class
                    for cls in module.classes:
                        if cls.name == member_name:
                            return Hover(
                                contents=MarkupContent(
                                    kind=MarkupKind.Markdown,
                                    value=cls.get_markdown_doc(module.name),
                                )
                            )
                    # Try constant
                    for const in module.constants:
                        if const.name == member_name:
                            md = f"**{module.name}.{const.name}**\n\n`{const.type}` - {const.description}"
                            return Hover(
                                contents=MarkupContent(
                                    kind=MarkupKind.Markdown, value=md
                                )
                            )
                elif len(parts) == 3:
                    # "json.JSONEncoder.encode"
                    class_name = parts[1]
                    method_name = parts[2]
                    for cls in module.classes:
                        if cls.name == class_name:
                            md = cls.get_method_markdown(method_name, module.name)
                            if md:
                                return Hover(
                                    contents=MarkupContent(
                                        kind=MarkupKind.Markdown, value=md
                                    )
                                )
                            # Try field
                            md = cls.get_field_markdown(method_name, module.name)
                            if md:
                                return Hover(
                                    contents=MarkupContent(
                                        kind=MarkupKind.Markdown, value=md
                                    )
                                )

    # Check if word is an imported module name
    if word in imported:
        info = imported[word]
        if info.member_name is None:
            # Module import
            return Hover(
                contents=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=info.module.get_markdown_doc(),
                )
            )
        else:
            # "from json import loads" -> hovering on "loads"
            module = info.module
            for func in module.functions:
                if func.name == info.member_name:
                    return Hover(
                        contents=MarkupContent(
                            kind=MarkupKind.Markdown,
                            value=func.get_markdown_doc(module.name),
                        )
                    )
            for cls in module.classes:
                if cls.name == info.member_name:
                    return Hover(
                        contents=MarkupContent(
                            kind=MarkupKind.Markdown,
                            value=cls.get_markdown_doc(module.name),
                        )
                    )

    # Check builtins (always in scope)
    if "." not in word and pylib_loader.builtins:
        builtins = pylib_loader.builtins
        for func in builtins.functions:
            if func.name == word:
                return Hover(
                    contents=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=func.get_markdown_doc("__builtin__"),
                    )
                )
        for cls in builtins.classes:
            if cls.name == word:
                return Hover(
                    contents=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=cls.get_markdown_doc("__builtin__"),
                    )
                )

    return None
