"""Python Standard Library Loader - Loads and indexes Python 2.7 stdlib module definitions."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)


class PyParam(TypedDict):
    """Type for function/method parameter definitions."""

    name: str
    type: str
    description: str


class PyReturn(TypedDict, total=False):
    """Type for function return value definitions."""

    type: str
    description: str


@dataclass
class PyField:
    """Represents a class field/attribute."""

    name: str
    type: str
    description: str


@dataclass
class PyFunction:
    """Represents a Python function or method."""

    name: str
    signature: str
    params: List[PyParam]
    returns: PyReturn
    description: str
    deprecated: bool = False

    def get_completion_snippet(self) -> str:
        """Generate LSP snippet for completion insertion."""
        parts = []
        for i, param in enumerate(self.params, 1):
            parts.append(f"${{{i}:{param['name']}}}")
        if parts:
            return f"{self.name}({', '.join(parts)})$0"
        return f"{self.name}()$0"

    def get_markdown_doc(self, module_name: str = "") -> str:
        """Generate Markdown documentation for this function."""
        lines = []
        if self.deprecated:
            lines.append("**DEPRECATED**\n")
        prefix = f"{module_name}." if module_name else ""
        lines.append(f"`{prefix}{self.signature}`\n")
        lines.append(self.description)
        if self.params:
            lines.append("\n**Parameters:**")
            for p in self.params:
                lines.append(f"- `{p['name']}`: {p['type']} - {p['description']}")
        ret = self.returns
        if ret and ret.get("type"):
            lines.append(f"\n**Returns:** {ret['type']} - {ret.get('description', '')}")
        return "\n".join(lines)


@dataclass
class PyConstant:
    """Represents a module-level constant."""

    name: str
    type: str
    description: str


@dataclass
class PyClass:
    """Represents a Python class with its members."""

    name: str
    description: str
    constructors: List[PyFunction] = field(default_factory=list)
    methods: List[PyFunction] = field(default_factory=list)
    fields: List[PyField] = field(default_factory=list)

    def get_markdown_doc(self, module_name: str = "") -> str:
        """Generate Markdown documentation for hover."""
        lines = []
        prefix = f"{module_name}." if module_name else ""
        lines.append(f"**{prefix}{self.name}** (class)")
        lines.append("")

        lines.append("```python")
        lines.append(f"class {self.name}")
        lines.append("```")
        lines.append("")
        lines.append(self.description)
        lines.append("")

        if self.constructors:
            lines.append("**Constructors:**")
            for c in self.constructors:
                lines.append(f"- `{c.signature}` - {c.description}")
            lines.append("")

        if self.methods:
            names = [f"`{m.name}`" for m in self.methods[:15]]
            if len(self.methods) > 15:
                names.append("...")
            lines.append(f"**Methods:** {', '.join(names)}")
            lines.append("")

        if self.fields:
            names = [f"`{f.name}`" for f in self.fields[:10]]
            if len(self.fields) > 10:
                names.append("...")
            lines.append(f"**Attributes:** {', '.join(names)}")

        return "\n".join(lines)

    def get_method_markdown(self, method_name: str, module_name: str = "") -> Optional[str]:
        """Generate Markdown documentation for a specific method."""
        for m in self.methods:
            if m.name == method_name:
                lines = []
                prefix = f"{module_name}." if module_name else ""
                lines.append(f"**{prefix}{self.name}.{m.name}**")
                lines.append("")
                lines.append(m.get_markdown_doc())
                return "\n".join(lines)
        return None

    def get_field_markdown(self, field_name: str, module_name: str = "") -> Optional[str]:
        """Generate Markdown documentation for a specific field."""
        for f in self.fields:
            if f.name == field_name:
                prefix = f"{module_name}." if module_name else ""
                lines = []
                lines.append(f"**{prefix}{self.name}.{f.name}**")
                lines.append("")
                lines.append(f"`{f.type}` - {f.description}")
                return "\n".join(lines)
        return None


@dataclass
class PyModule:
    """Represents a Python standard library module."""

    name: str
    description: str
    functions: List[PyFunction] = field(default_factory=list)
    classes: List[PyClass] = field(default_factory=list)
    constants: List[PyConstant] = field(default_factory=list)
    docs_url: str = ""

    def get_markdown_doc(self) -> str:
        """Generate Markdown documentation for hover."""
        lines = []
        lines.append(f"**{self.name}** (module)")
        lines.append("")
        lines.append(self.description)
        lines.append("")

        if self.functions:
            names = [f"`{f.name}`" for f in self.functions[:15]]
            if len(self.functions) > 15:
                names.append("...")
            lines.append(f"**Functions:** {', '.join(names)}")
            lines.append("")

        if self.classes:
            names = [f"`{c.name}`" for c in self.classes[:10]]
            lines.append(f"**Classes:** {', '.join(names)}")
            lines.append("")

        if self.docs_url:
            lines.append(f"[Documentation]({self.docs_url})")

        return "\n".join(lines)


class PylibLoader:
    """Loads and indexes Python stdlib module definitions from pylib_db/ JSON files."""

    def __init__(self) -> None:
        self.modules: Dict[str, PyModule] = {}  # "json" -> PyModule
        self.all_functions: Dict[str, PyFunction] = {}  # "json.loads" -> PyFunction
        self.builtins: Optional[PyModule] = None  # special ref to __builtin__
        self._load_all()

    def _load_all(self) -> None:
        """Load all pylib module definition files."""
        pylib_db_dir = Path(__file__).parent / "pylib_db"

        if not pylib_db_dir.exists():
            logger.warning(f"Pylib database directory not found: {pylib_db_dir}")
            return

        for json_file in sorted(pylib_db_dir.glob("*.json")):
            if json_file.name == "pylib_schema.json":
                continue
            try:
                self._load_module_file(json_file)
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

        # Keep a direct reference to builtins
        self.builtins = self.modules.get("__builtin__")

        logger.info(
            f"Loaded {len(self.modules)} Python stdlib modules "
            f"with {len(self.all_functions)} indexed functions"
        )

    def _load_module_file(self, file_path: Path) -> None:
        """Load a single module JSON file."""
        with open(file_path) as f:
            data = json.load(f)

        module_name = data["module"]

        functions = []
        for func_data in data.get("functions", []):
            func = self._parse_function(func_data)
            functions.append(func)
            self.all_functions[f"{module_name}.{func.name}"] = func

        classes = []
        for cls_data in data.get("classes", []):
            cls = self._parse_class(cls_data)
            classes.append(cls)
            # Index class methods as module.Class.method
            for method in cls.methods:
                self.all_functions[f"{module_name}.{cls.name}.{method.name}"] = method

        constants = []
        for const_data in data.get("constants", []):
            constants.append(PyConstant(
                name=const_data["name"],
                type=const_data["type"],
                description=const_data["description"],
            ))

        module = PyModule(
            name=module_name,
            description=data["description"],
            functions=functions,
            classes=classes,
            constants=constants,
            docs_url=data.get("docs_url", ""),
        )
        self.modules[module_name] = module

        logger.debug(
            f"Loaded module {module_name}: "
            f"{len(functions)} functions, {len(classes)} classes"
        )

    def _parse_function(self, data: Dict[str, Any]) -> PyFunction:
        """Parse a function definition from JSON data."""
        return PyFunction(
            name=data["name"],
            signature=data["signature"],
            params=data.get("params", []),
            returns=data.get("returns", {}),
            description=data["description"],
            deprecated=data.get("deprecated", False),
        )

    def _parse_class(self, data: Dict[str, Any]) -> PyClass:
        """Parse a class definition from JSON data."""
        constructors = []
        for c in data.get("constructors", []):
            constructors.append(PyFunction(
                name=data["name"],
                signature=c["signature"],
                params=c.get("params", []),
                returns={},
                description=c["description"],
            ))

        methods = []
        for m in data.get("methods", []):
            methods.append(PyFunction(
                name=m["name"],
                signature=m["signature"],
                params=m.get("params", []),
                returns=m.get("returns", {}),
                description=m["description"],
                deprecated=m.get("deprecated", False),
            ))

        fields = [
            PyField(name=fd["name"], type=fd["type"], description=fd["description"])
            for fd in data.get("fields", [])
        ]

        return PyClass(
            name=data["name"],
            description=data["description"],
            constructors=constructors,
            methods=methods,
            fields=fields,
        )

    def get_module(self, name: str) -> Optional[PyModule]:
        """Get a module by name (e.g., 'json', 'os.path')."""
        return self.modules.get(name)

    def get_function(self, full_name: str) -> Optional[PyFunction]:
        """Get a function by full name (e.g., 'json.loads')."""
        return self.all_functions.get(full_name)

    def get_all_module_names(self) -> List[str]:
        """Get sorted list of all loaded module names."""
        return sorted(self.modules.keys())

    def search_functions(self, prefix: str) -> List[PyFunction]:
        """Find functions whose full name starts with prefix."""
        results = []
        for full_name, func in self.all_functions.items():
            if full_name.startswith(prefix):
                results.append(func)
        return results
