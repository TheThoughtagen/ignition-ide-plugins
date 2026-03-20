"""Script symbol extraction via AST parsing.

Parses project .py files to extract functions, classes, and variables.
Used by completions, hover, and go-to-definition to provide symbol-level
IntelliSense for project scripts (e.g., core.networking.callables.tagChangeEvent).
"""

import ast
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Data Classes ─────────────────────────────────────────────────────


@dataclass
class ScriptFunction:
    """A function definition extracted from a project script."""

    name: str
    line_number: int  # 1-based
    signature: str  # e.g., "def helper(tagPath, value=None)"
    params: List[str]  # Parameter names (excludes self/cls)
    docstring: Optional[str] = None
    returns: Optional[str] = None  # Return type annotation as string
    is_method: bool = False
    decorators: List[str] = field(default_factory=list)

    def get_completion_snippet(self) -> str:
        """Generate an LSP snippet with ${1:param} placeholders."""
        if not self.params:
            return f"{self.name}()$0"
        # Only include required params (those without =... defaults) in snippets
        required = [p for p in self.params if "=" not in p]
        if not required:
            return f"{self.name}()$0"
        parts = []
        for i, param in enumerate(required, 1):
            parts.append(f"${{{i}:{param}}}")
        return f"{self.name}({', '.join(parts)})$0"

    def get_markdown_doc(self, module_path: str = "") -> str:
        """Generate hover markdown with signature, docstring, params."""
        lines = []
        qual = f"{module_path}.{self.name}" if module_path else self.name
        lines.append(f"**{qual}**")
        lines.append("")
        lines.append(f"```python\n{self.signature}\n```")
        if self.docstring:
            lines.append("")
            lines.append(self.docstring)
        return "\n".join(lines)


@dataclass
class ScriptClass:
    """A class definition extracted from a project script."""

    name: str
    line_number: int  # 1-based
    docstring: Optional[str] = None
    bases: List[str] = field(default_factory=list)
    methods: List[ScriptFunction] = field(default_factory=list)
    class_variables: List[str] = field(default_factory=list)

    def get_markdown_doc(self, module_path: str = "") -> str:
        """Generate hover markdown with class name, bases, method list."""
        lines = []
        qual = f"{module_path}.{self.name}" if module_path else self.name
        lines.append(f"**{qual}** (class)")
        lines.append("")
        base_str = ", ".join(self.bases) if self.bases else ""
        lines.append(f"```python\nclass {self.name}({base_str})\n```")
        if self.docstring:
            lines.append("")
            lines.append(self.docstring)
        if self.methods:
            names = [f"`{m.name}`" for m in self.methods if not m.name.startswith("__") or m.name == "__init__"]
            if names:
                lines.append("")
                lines.append(f"**Methods:** {', '.join(names)}")
        if self.class_variables:
            lines.append("")
            lines.append(f"**Attributes:** {', '.join(f'`{v}`' for v in self.class_variables)}")
        return "\n".join(lines)


@dataclass
class ScriptVariable:
    """A top-level assignment extracted from a project script."""

    name: str
    line_number: int  # 1-based
    type_hint: Optional[str] = None
    value_repr: Optional[str] = None


@dataclass
class ModuleSymbols:
    """All symbols extracted from one .py file."""

    file_path: str
    module_path: str
    functions: List[ScriptFunction] = field(default_factory=list)
    classes: List[ScriptClass] = field(default_factory=list)
    variables: List[ScriptVariable] = field(default_factory=list)
    parse_error: Optional[str] = None
    _file_mtime: float = 0.0


# ── Py2 Preprocessing ───────────────────────────────────────────────


def _preprocess_py2(source: str) -> str:
    """Transform common Python 2 constructs so ast.parse() succeeds.

    Ignition uses Jython (Python 2). This handles the most common
    incompatibilities without a full Py2 parser.
    """
    # print >>stream, args  ->  print(args, file=stream)
    source = re.sub(
        r"^(\s*)print[ \t]*>>[ \t]*(\S+)[ \t]*,[ \t]*(.+)$",
        r"\1print(\3, file=\2)",
        source,
        flags=re.MULTILINE,
    )
    # print >>stream  (no args)  ->  print(file=stream)
    source = re.sub(
        r"^(\s*)print[ \t]*>>[ \t]*(\S+)[ \t]*$",
        r"\1print(file=\2)",
        source,
        flags=re.MULTILINE,
    )
    # print args  ->  print(args)
    source = re.sub(
        r"^(\s*)print\b[ \t]+(?!>>)(?!\()(.+)$",
        r"\1print(\2)",
        source,
        flags=re.MULTILINE,
    )
    # except Type, var:  ->  except Type as var:
    source = re.sub(
        r"^(\s*except[ \t]+[\w.]+)[ \t]*,[ \t]*(\w+)[ \t]*:",
        r"\1 as \2:",
        source,
        flags=re.MULTILINE,
    )
    # raise Type, value  ->  raise Type(value)
    source = re.sub(
        r"^(\s*raise[ \t]+[\w.]+)[ \t]*,[ \t]*(.+)$",
        r"\1(\2)",
        source,
        flags=re.MULTILINE,
    )
    return source


# ── AST Extraction ───────────────────────────────────────────────────


def _node_to_str(node: ast.AST) -> str:
    """Convert an AST node to source string."""
    return ast.unparse(node)


def _extract_function(node: ast.FunctionDef) -> ScriptFunction:
    """Extract a ScriptFunction from an ast.FunctionDef node."""
    # Parameter names (skip self/cls for methods)
    # Mark params with defaults using "= ..." suffix for stub generation
    all_param_names = [arg.arg for arg in node.args.args]
    num_defaults = len(node.args.defaults)
    num_params = len(all_param_names)
    all_params = []
    for i, name in enumerate(all_param_names):
        # defaults are right-aligned: last num_defaults params have defaults
        if i >= num_params - num_defaults:
            all_params.append(f"{name}=...")
        else:
            all_params.append(name)
    is_method = len(all_param_names) > 0 and all_param_names[0] in ("self", "cls")
    params = all_params[1:] if is_method else all_params

    # Build signature
    sig = f"def {node.name}({', '.join(all_params)})"
    returns_str = None
    if node.returns:
        returns_str = _node_to_str(node.returns)
        sig += f" -> {returns_str}"

    # Decorators
    decorators = []
    for dec in node.decorator_list:
        decorators.append(_node_to_str(dec))

    return ScriptFunction(
        name=node.name,
        line_number=node.lineno,
        signature=sig,
        params=params,
        docstring=ast.get_docstring(node),
        returns=returns_str,
        is_method=is_method,
        decorators=decorators,
    )


def _extract_class(node: ast.ClassDef) -> ScriptClass:
    """Extract a ScriptClass from an ast.ClassDef node."""
    bases = [_node_to_str(b) for b in node.bases]

    methods = []
    class_variables = []

    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func = _extract_function(item)
            func.is_method = True
            methods.append(func)
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    class_variables.append(target.id)

    return ScriptClass(
        name=node.name,
        line_number=node.lineno,
        docstring=ast.get_docstring(node),
        bases=bases,
        methods=methods,
        class_variables=class_variables,
    )


def extract_symbols(file_path: str, module_path: str = "") -> ModuleSymbols:
    """Parse a .py file and extract all top-level symbols.

    Returns ModuleSymbols with functions, classes, and variables.
    On parse error, returns a ModuleSymbols with parse_error set.
    """
    result = ModuleSymbols(file_path=file_path, module_path=module_path)

    try:
        mtime = os.path.getmtime(file_path)
        result._file_mtime = mtime
    except OSError:
        result.parse_error = f"File not found: {file_path}"
        return result

    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError) as e:
        result.parse_error = str(e)
        return result

    # Preprocess Py2 syntax before parsing
    source = _preprocess_py2(source)

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        result.parse_error = str(e)
        return result

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.functions.append(_extract_function(node))
        elif isinstance(node, ast.ClassDef):
            result.classes.append(_extract_class(node))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    value_repr = None
                    try:
                        value_repr = _node_to_str(node.value)
                        # Truncate long values
                        if len(value_repr) > 60:
                            value_repr = value_repr[:57] + "..."
                    except Exception:
                        pass
                    result.variables.append(
                        ScriptVariable(
                            name=target.id,
                            line_number=node.lineno,
                            value_repr=value_repr,
                        )
                    )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            type_hint = _node_to_str(node.annotation) if node.annotation else None
            value_repr = None
            if node.value:
                try:
                    value_repr = _node_to_str(node.value)
                    if len(value_repr) > 60:
                        value_repr = value_repr[:57] + "..."
                except Exception:
                    pass
            result.variables.append(
                ScriptVariable(
                    name=node.target.id,
                    line_number=node.lineno,
                    type_hint=type_hint,
                    value_repr=value_repr,
                )
            )

    return result


# ── Cache ────────────────────────────────────────────────────────────


class SymbolCache:
    """Mtime-based cache for ModuleSymbols.

    Re-extracts symbols only when the file's mtime has changed.
    """

    def __init__(self):
        self._cache: Dict[str, ModuleSymbols] = {}

    def get(self, file_path: str, module_path: str = "") -> ModuleSymbols:
        """Return cached symbols if file hasn't changed, else re-extract."""
        try:
            current_mtime = os.path.getmtime(file_path)
        except OSError:
            return extract_symbols(file_path, module_path)

        cached = self._cache.get(file_path)
        if cached is not None and cached._file_mtime == current_mtime:
            return cached

        symbols = extract_symbols(file_path, module_path)
        self._cache[file_path] = symbols
        return symbols

    def invalidate(self, file_path: str) -> None:
        """Remove a specific file from the cache."""
        self._cache.pop(file_path, None)

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()
