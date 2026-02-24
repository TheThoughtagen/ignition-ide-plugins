"""Completion provider for Ignition APIs."""

import logging
import re
from typing import Dict, List, Optional

from lsprotocol.types import (
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    CompletionParams,
    InsertTextFormat,
    MarkupContent,
    MarkupKind,
)
from pygls.workspace import TextDocument

from .api_loader import IgnitionAPILoader
from .java_loader import JavaAPILoader
from .project_scanner import ProjectIndex
from .script_symbols import SymbolCache

logger = logging.getLogger(__name__)

# Prefixes that trigger project-level completions
PROJECT_PREFIXES = ("project.", "shared.")


def get_completion_context(document: TextDocument, position: CompletionParams.position) -> str:
    """Get the text context before cursor for completion."""
    line = document.lines[position.line]
    text_before_cursor = line[:position.character]

    # Extract the last partial identifier (e.g., "system.tag.")
    match = re.search(r'([\w\.]+)$', text_before_cursor)
    if match:
        return match.group(1)

    return ""


def get_completions(
    document: TextDocument,
    position: CompletionParams.position,
    api_loader: IgnitionAPILoader,
    project_index: Optional[ProjectIndex] = None,
    java_loader: Optional[JavaAPILoader] = None,
    symbol_cache: Optional[SymbolCache] = None,
) -> CompletionList:
    """Generate completion items based on context."""
    # Expression completions for virtual expression buffers
    if "[Ignition:" in document.uri and (
        "/Expression:" in document.uri or "/Expression]" in document.uri
    ):
        return _get_expression_completions(document, position)

    # JSON completions for Perspective views
    if document.uri.endswith(".json"):
        from .json_completion import get_json_completions, is_perspective_json

        if is_perspective_json(document):
            result = get_json_completions(document, position)
            if result is not None:
                return result

    # Java import / class member completions
    if java_loader:
        from .java_scope import detect_java_context
        java_ctx = detect_java_context(document, position, java_loader)
        if java_ctx:
            java_items = _get_java_completions(java_ctx, java_loader)
            if java_items:
                return CompletionList(is_incomplete=False, items=java_items)

    context = get_completion_context(document, position)
    logger.info(f"Completion context: '{context}'")

    items = []

    if not context:
        # No context - offer top-level modules
        items.extend(_get_top_level_completions(project_index))
    elif context == "system" or context == "system.":
        # Just typed "system" or "system." - show available modules
        items.extend(_get_system_modules(api_loader))
    elif context.startswith("system.") and context.endswith("."):
        # Typed "system.tag." (with trailing dot) - show functions for that module
        module = context.rstrip(".")  # "system.tag." -> "system.tag"
        items.extend(_get_module_functions(module, api_loader))
    elif context.startswith("system.") and context.count(".") == 1:
        # Typed "system.tag" or partial like "system.t"
        module = context
        funcs = _get_module_functions(module, api_loader)
        if funcs:
            # Exact module match (e.g., "system.tag") - show its functions
            items.extend(funcs)
        else:
            # Partial module name (e.g., "system.t") - show matching modules
            partial = context.split(".")[-1].lower()
            items.extend(
                m for m in _get_system_modules(api_loader)
                if m.label.lower().startswith(partial)
            )
    elif context.startswith("system.") and context.count(".") >= 2:
        # Typed "system.tag.read" etc - show matching functions
        items.extend(_get_function_completions(context, api_loader))
    elif _is_project_module(context, project_index):
        # Typed "project.", "shared.", "general.", or any known script package
        items.extend(_get_project_completions(context, project_index, symbol_cache))

    logger.info(f"Generated {len(items)} completion items")
    return CompletionList(is_incomplete=False, items=items)


def _get_top_level_completions(project_index: Optional[ProjectIndex] = None) -> List[CompletionItem]:
    """Get completions for top-level Ignition objects."""
    items = [
        CompletionItem(
            label="system",
            kind=CompletionItemKind.Module,
            detail="Ignition system functions",
            documentation="Ignition platform system functions and APIs",
        ),
        CompletionItem(
            label="shared",
            kind=CompletionItemKind.Module,
            detail="Project shared scripts",
            documentation="Access project-level shared scripts",
        ),
    ]

    # Include top-level project packages (general, core, Alerts, etc.)
    if project_index is not None:
        for pkg in _get_project_packages(project_index):
            if pkg not in ("system", "shared"):
                items.append(
                    CompletionItem(
                        label=pkg,
                        kind=CompletionItemKind.Module,
                        detail=f"Project script package",
                        documentation=f"Project script package '{pkg}'",
                    )
                )

    return items


def _get_system_modules(api_loader: IgnitionAPILoader) -> List[CompletionItem]:
    """Get completions for system.* modules."""
    modules = api_loader.get_all_modules()
    items = []

    for module in modules:
        if module.startswith("system."):
            module_name = module.split(".")[-1]  # "system.tag" -> "tag"
            func_count = len(api_loader.get_module_functions(module))

            items.append(
                CompletionItem(
                    label=module_name,
                    kind=CompletionItemKind.Module,
                    detail=f"{module} ({func_count} functions)",
                    documentation=f"Ignition {module} module",
                    insert_text=module_name,
                )
            )

    return items


def _get_module_functions(module: str, api_loader: IgnitionAPILoader) -> List[CompletionItem]:
    """Get all functions for a module (e.g., system.tag)."""
    functions = api_loader.get_module_functions(module)
    items = []

    for func in functions:
        # Create completion item with full details
        doc_md = f"**{func.signature}**\n\n{func.description}"
        if func.deprecated:
            doc_md = "⚠️ **DEPRECATED**\n\n" + doc_md

        items.append(
            CompletionItem(
                label=func.name,
                kind=CompletionItemKind.Function,
                detail=func.signature,
                documentation=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=doc_md,
                ),
                insert_text=func.get_completion_snippet(),
                insert_text_format=InsertTextFormat.Snippet,
                deprecated=func.deprecated,
            )
        )

    return items


def _get_function_completions(prefix: str, api_loader: IgnitionAPILoader) -> List[CompletionItem]:
    """Get function completions matching a prefix (e.g., 'system.tag.read')."""
    matching_functions = api_loader.search_functions(prefix)
    items = []

    for func in matching_functions:
        doc_md = f"**{func.signature}**\n\n{func.description}"

        items.append(
            CompletionItem(
                label=func.name,
                kind=CompletionItemKind.Function,
                detail=func.signature,
                documentation=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=doc_md,
                ),
                insert_text=func.get_completion_snippet(),
                insert_text_format=InsertTextFormat.Snippet,
            )
        )

    return items


# ── Project Script Completions ───────────────────────────────────────


def _get_project_packages(project_index: ProjectIndex) -> List[str]:
    """Get unique top-level package names from the project index."""
    packages = set()
    for loc in project_index.scripts:
        top = loc.module_path.split(".")[0]
        if top:
            packages.add(top)
    return sorted(packages)


def _is_project_module(context: str, project_index: Optional[ProjectIndex]) -> bool:
    """Check if the context matches a known project module prefix.

    Handles static prefixes (project.*, shared.*) and dynamic top-level
    packages discovered by the project scanner (general.*, core.*, etc.).
    """
    if project_index is None:
        return False

    # Static prefixes always match
    if any(context == p.rstrip(".") or context.startswith(p) for p in PROJECT_PREFIXES):
        return True

    # Check if the first segment matches a known project package
    first_segment = context.split(".")[0]
    return first_segment in _get_project_packages(project_index)


def _get_project_completions(
    context: str,
    project_index: ProjectIndex,
    symbol_cache: Optional[SymbolCache] = None,
) -> List[CompletionItem]:
    """Get completions for project-level script references.

    Handles contexts like:
        "project."         -> list top-level children (e.g., "library")
        "project.library." -> list children at that level (e.g., "utils", "config")
        "project.library.u" -> filter children matching "u" prefix
        "shared."          -> list shared script modules
        "project.library.utils." -> list symbols inside utils.py (leaf module)
        "project.library.utils.MyClass." -> list class members
    """
    # Strip trailing dot for prefix search
    if context.endswith("."):
        prefix = context.rstrip(".")
        partial = ""
    else:
        # "project.library.ut" -> prefix="project.library", partial="ut"
        parts = context.rsplit(".", 1)
        if len(parts) == 2:
            prefix = parts[0]
            partial = parts[1]
        else:
            prefix = context
            partial = ""

    # ── Leaf module detection: show symbols inside .py files ──
    if symbol_cache is not None:
        # Check if prefix itself is a leaf module (no children beyond itself)
        leaf = project_index.find_by_module_path(prefix)
        if leaf and leaf.script_key == "__file__":
            children = [
                s for s in project_index.search_module_paths(prefix)
                if s.module_path != prefix
            ]
            if not children:
                return _get_leaf_symbol_completions(leaf, partial, symbol_cache)

        # Check for class member access: prefix = "module_path.ClassName"
        if "." in prefix:
            module_candidate, class_name = prefix.rsplit(".", 1)
            leaf = project_index.find_by_module_path(module_candidate)
            if leaf and leaf.script_key == "__file__":
                symbols = symbol_cache.get(leaf.file_path, leaf.module_path)
                for cls in symbols.classes:
                    if cls.name == class_name:
                        return _get_class_member_completions(cls, partial, module_candidate)

    # Find all scripts whose module_path starts with our prefix
    matching = project_index.search_module_paths(prefix)

    if not matching:
        return []

    # Collect the next path segment after the prefix
    prefix_depth = prefix.count(".") + 1
    seen: Dict[str, str] = {}  # segment -> full module_path (for detail)

    for loc in matching:
        parts = loc.module_path.split(".")
        if len(parts) <= prefix_depth:
            continue

        segment = parts[prefix_depth]

        # If there's a partial, filter by it
        if partial and not segment.lower().startswith(partial.lower()):
            continue

        if segment not in seen:
            # Track the resource type for the detail string
            seen[segment] = loc.resource_type

    items = []
    for segment, resource_type in sorted(seen.items()):
        # Check if this segment is a leaf (final module) or intermediate package
        full_path = f"{prefix}.{segment}"
        children = [
            s for s in project_index.search_module_paths(full_path)
            if s.module_path != full_path
        ]
        is_package = len(children) > 0
        exact_match = project_index.find_by_module_path(full_path)

        if exact_match and not is_package:
            # Leaf module — show as a script reference
            items.append(
                CompletionItem(
                    label=segment,
                    kind=CompletionItemKind.Module,
                    detail=f"{full_path} ({resource_type})",
                    documentation=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=f"**{full_path}**\n\nProject script module\n\nSource: `{exact_match.file_path}`",
                    ),
                )
            )
        else:
            # Intermediate package — show as a namespace
            child_count = len(set(
                s.module_path.split(".")[prefix_depth]
                for s in project_index.search_module_paths(full_path)
                if len(s.module_path.split(".")) > prefix_depth
            ))
            items.append(
                CompletionItem(
                    label=segment,
                    kind=CompletionItemKind.Module,
                    detail=f"{full_path} ({child_count} children)" if child_count else full_path,
                )
            )

    return items


# ── Leaf Module Symbol Completions ────────────────────────────────────


def _get_leaf_symbol_completions(
    loc, partial: str, symbol_cache: SymbolCache
) -> List[CompletionItem]:
    """Return completions for symbols inside a leaf .py module.

    Shows functions, classes, and variables from the file.
    Skips private names (starting with _).
    """
    symbols = symbol_cache.get(loc.file_path, loc.module_path)
    if symbols.parse_error:
        return []

    items: List[CompletionItem] = []

    for func in symbols.functions:
        if func.name.startswith("_"):
            continue
        if partial and not func.name.lower().startswith(partial.lower()):
            continue
        items.append(
            CompletionItem(
                label=func.name,
                kind=CompletionItemKind.Function,
                detail=func.signature,
                documentation=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=func.get_markdown_doc(loc.module_path),
                ),
            )
        )

    for cls in symbols.classes:
        if cls.name.startswith("_"):
            continue
        if partial and not cls.name.lower().startswith(partial.lower()):
            continue
        items.append(
            CompletionItem(
                label=cls.name,
                kind=CompletionItemKind.Class,
                detail=f"class {cls.name}",
                documentation=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=cls.get_markdown_doc(loc.module_path),
                ),
            )
        )

    for var in symbols.variables:
        if var.name.startswith("_"):
            continue
        if partial and not var.name.lower().startswith(partial.lower()):
            continue
        detail = var.type_hint or ""
        if var.value_repr:
            detail = f"{detail} = {var.value_repr}" if detail else f"= {var.value_repr}"
        items.append(
            CompletionItem(
                label=var.name,
                kind=CompletionItemKind.Variable,
                detail=detail or "variable",
            )
        )

    return items


def _get_class_member_completions(
    cls, partial: str, module_path: str
) -> List[CompletionItem]:
    """Return completions for members of a class inside a leaf module.

    Shows methods (excluding most dunder methods) and class variables.
    """
    items: List[CompletionItem] = []

    for method in cls.methods:
        # Skip dunder methods except __init__
        if method.name.startswith("__") and method.name != "__init__":
            continue
        if partial and not method.name.lower().startswith(partial.lower()):
            continue
        items.append(
            CompletionItem(
                label=method.name,
                kind=CompletionItemKind.Method,
                detail=method.signature,
                documentation=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=method.get_markdown_doc(f"{module_path}.{cls.name}"),
                ),
            )
        )

    for var_name in cls.class_variables:
        if partial and not var_name.lower().startswith(partial.lower()):
            continue
        items.append(
            CompletionItem(
                label=var_name,
                kind=CompletionItemKind.Field,
                detail=f"{cls.name}.{var_name}",
            )
        )

    return items


# ── Expression Function Completions ──────────────────────────────────


def _get_expression_completions(
    document: TextDocument,
    position: CompletionParams.position,
) -> CompletionList:
    """Return completions for Ignition expression language functions."""
    from .expression_functions import EXPRESSION_FUNCTIONS

    context = get_completion_context(document, position)
    items: List[CompletionItem] = []

    for name, info in EXPRESSION_FUNCTIONS.items():
        if context and not name.lower().startswith(context.lower()):
            continue
        items.append(
            CompletionItem(
                label=name,
                kind=CompletionItemKind.Function,
                detail=info["signature"],
                documentation=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=(
                        f"**{info['signature']}**\n\n"
                        f"{info['description']}\n\n"
                        f"*Category: {info['category']}*  \n"
                        f"*Returns: {info['return_type']}*"
                    ),
                ),
                insert_text=info.get("snippet", name + "($1)$0"),
                insert_text_format=InsertTextFormat.Snippet,
            )
        )

    return CompletionList(is_incomplete=False, items=items)


# ── Java Class Completions ───────────────────────────────────────────


def _get_java_completions(context, java_loader: JavaAPILoader) -> List[CompletionItem]:
    """Route Java completion by context type."""
    from .java_scope import JavaContextType

    if context.type == JavaContextType.IMPORT_PACKAGE:
        return _get_java_package_completions(context, java_loader)
    elif context.type == JavaContextType.IMPORT_CLASS:
        return _get_java_class_import_completions(context, java_loader)
    elif context.type == JavaContextType.CLASS_MEMBER:
        return _get_java_member_completions(context, instance=True)
    elif context.type == JavaContextType.STATIC_MEMBER:
        return _get_java_member_completions(context, instance=False)
    elif context.type == JavaContextType.CONSTRUCTOR:
        return _get_java_constructor_completions(context)
    return []


def _get_java_package_completions(context, java_loader: JavaAPILoader) -> List[CompletionItem]:
    """Offer sub-packages for 'from java.' or 'from java.net.'."""
    subs = java_loader.get_sub_packages(context.package)
    items = []
    for sub in subs:
        if context.partial and not sub.lower().startswith(context.partial.lower()):
            continue
        items.append(
            CompletionItem(
                label=sub,
                kind=CompletionItemKind.Module,
                detail=f"{context.package}.{sub}",
            )
        )
    return items


def _get_java_class_import_completions(context, java_loader: JavaAPILoader) -> List[CompletionItem]:
    """Offer classes for 'from java.net import '."""
    classes = java_loader.get_package_classes(context.package)
    items = []
    for cls in classes:
        if context.partial and not cls.name.lower().startswith(context.partial.lower()):
            continue
        items.append(
            CompletionItem(
                label=cls.name,
                kind=CompletionItemKind.Class,
                detail=cls.full_name,
                documentation=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=cls.description,
                ),
            )
        )
    return items


def _get_java_member_completions(context, instance: bool = True) -> List[CompletionItem]:
    """Offer methods and fields for a class instance or static access."""
    cls = context.java_class
    items = []

    if instance:
        # Instance access: show instance methods
        for m in cls.methods:
            if context.partial and not m.name.lower().startswith(context.partial.lower()):
                continue
            items.append(
                CompletionItem(
                    label=m.name,
                    kind=CompletionItemKind.Method,
                    detail=m.signature,
                    documentation=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=m.description,
                    ),
                    insert_text=m.get_completion_snippet(),
                    insert_text_format=InsertTextFormat.Snippet,
                    deprecated=m.deprecated,
                )
            )
    else:
        # Static access: show static methods first, then instance methods
        for m in cls.static_methods:
            if context.partial and not m.name.lower().startswith(context.partial.lower()):
                continue
            items.append(
                CompletionItem(
                    label=m.name,
                    kind=CompletionItemKind.Method,
                    detail=f"(static) {m.signature}",
                    documentation=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=m.description,
                    ),
                    insert_text=m.get_completion_snippet(),
                    insert_text_format=InsertTextFormat.Snippet,
                    deprecated=m.deprecated,
                )
            )
        for m in cls.methods:
            if context.partial and not m.name.lower().startswith(context.partial.lower()):
                continue
            items.append(
                CompletionItem(
                    label=m.name,
                    kind=CompletionItemKind.Method,
                    detail=m.signature,
                    documentation=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=m.description,
                    ),
                    insert_text=m.get_completion_snippet(),
                    insert_text_format=InsertTextFormat.Snippet,
                    deprecated=m.deprecated,
                )
            )

    # Static fields (e.g., Integer.MAX_VALUE, Math.PI)
    for f in cls.fields:
        if f.static:
            if context.partial and not f.name.lower().startswith(context.partial.lower()):
                continue
            items.append(
                CompletionItem(
                    label=f.name,
                    kind=CompletionItemKind.Field,
                    detail=f"{f.type} (static)",
                    documentation=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=f.description,
                    ),
                )
            )

    return items


def _get_java_constructor_completions(context) -> List[CompletionItem]:
    """Offer constructor parameter snippets for 'ClassName('."""
    cls = context.java_class
    items = []
    for i, ctor in enumerate(cls.constructors):
        snippet_parts = []
        for j, p in enumerate(ctor.params, 1):
            snippet_parts.append(f"${{{j}:{p['name']}}}")
        snippet = ", ".join(snippet_parts) if snippet_parts else ""

        items.append(
            CompletionItem(
                label=ctor.signature,
                kind=CompletionItemKind.Constructor,
                detail=f"{cls.name} constructor",
                documentation=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=ctor.description,
                ),
                insert_text=snippet + ")$0" if snippet else ")$0",
                insert_text_format=InsertTextFormat.Snippet,
                sort_text=f"0{i}",
            )
        )
    return items
