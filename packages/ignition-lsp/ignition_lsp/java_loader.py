"""Java API Loader - Loads and indexes Java class definitions for Jython support."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class JavaMethod:
    """Represents a Java method or constructor."""

    name: str
    signature: str
    params: List[dict]
    returns: dict
    description: str
    static: bool = False
    deprecated: bool = False

    def get_completion_snippet(self) -> str:
        """Generate LSP snippet for completion insertion."""
        parts = []
        for i, param in enumerate(self.params, 1):
            parts.append(f"${{{i}:{param['name']}}}")
        if parts:
            return f"{self.name}({', '.join(parts)})$0"
        return f"{self.name}()$0"

    def get_markdown_doc(self) -> str:
        """Generate Markdown documentation for this method."""
        lines = []
        if self.deprecated:
            lines.append("**DEPRECATED**\n")
        lines.append(f"`{self.signature}`\n")
        lines.append(self.description)
        if self.params:
            lines.append("\n**Parameters:**")
            for p in self.params:
                lines.append(f"- `{p['name']}`: {p['type']} - {p['description']}")
        ret = self.returns
        if ret and ret.get("type") and ret["type"] != "void":
            lines.append(f"\n**Returns:** {ret['type']} - {ret.get('description', '')}")
        return "\n".join(lines)


@dataclass
class JavaField:
    """Represents a Java field."""

    name: str
    type: str
    description: str
    static: bool = False
    final: bool = False


@dataclass
class JavaClass:
    """Represents a Java class with its members."""

    name: str
    package: str
    full_name: str
    description: str
    constructors: List[JavaMethod] = field(default_factory=list)
    methods: List[JavaMethod] = field(default_factory=list)
    static_methods: List[JavaMethod] = field(default_factory=list)
    fields: List[JavaField] = field(default_factory=list)
    deprecated: bool = False
    docs_url: str = ""

    def get_markdown_doc(self) -> str:
        """Generate Markdown documentation for hover."""
        lines = []
        lines.append(f"**{self.full_name}** (class)")
        lines.append("")

        if self.deprecated:
            lines.append("**DEPRECATED**\n")

        lines.append("```java")
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

        instance_methods = [m for m in self.methods if not m.static]
        if instance_methods:
            names = [f"`{m.name}`" for m in instance_methods[:15]]
            if len(instance_methods) > 15:
                names.append("...")
            lines.append(f"**Methods:** {', '.join(names)}")
            lines.append("")

        if self.static_methods:
            names = [f"`{m.name}`" for m in self.static_methods[:10]]
            if len(self.static_methods) > 10:
                names.append("...")
            lines.append(f"**Static Methods:** {', '.join(names)}")
            lines.append("")

        static_fields = [f for f in self.fields if f.static]
        if static_fields:
            names = [f"`{f.name}`" for f in static_fields[:10]]
            lines.append(f"**Constants:** {', '.join(names)}")
            lines.append("")

        if self.docs_url:
            lines.append(f"[Documentation]({self.docs_url})")

        return "\n".join(lines)

    def get_method_markdown(self, method_name: str) -> Optional[str]:
        """Generate Markdown documentation for a specific method."""
        for m in self.methods + self.static_methods:
            if m.name == method_name:
                lines = []
                header = f"**{self.name}.{m.name}**"
                if m.static:
                    header += " *(static)*"
                lines.append(header)
                lines.append("")
                lines.append(m.get_markdown_doc())
                if self.docs_url:
                    lines.append(f"\n[Documentation]({self.docs_url})")
                return "\n".join(lines)
        return None

    def get_field_markdown(self, field_name: str) -> Optional[str]:
        """Generate Markdown documentation for a specific field."""
        for f in self.fields:
            if f.name == field_name:
                lines = []
                header = f"**{self.name}.{f.name}**"
                if f.static:
                    header += " *(static)*"
                if f.final:
                    header += " *(final)*"
                lines.append(header)
                lines.append("")
                lines.append(f"`{f.type}` - {f.description}")
                return "\n".join(lines)
        return None


class JavaAPILoader:
    """Loads and indexes Java class definitions from java_db/ JSON files."""

    def __init__(self):
        self.classes: Dict[str, JavaClass] = {}  # "java.net.URL" -> JavaClass
        self.packages: Dict[str, List[JavaClass]] = {}  # "java.net" -> [URL, ...]
        self.short_names: Dict[str, List[JavaClass]] = {}  # "URL" -> [java.net.URL]
        self._load_all()

    def _load_all(self):
        """Load all Java API definition files."""
        java_db_dir = Path(__file__).parent / "java_db"

        if not java_db_dir.exists():
            logger.warning(f"Java database directory not found: {java_db_dir}")
            return

        for json_file in sorted(java_db_dir.glob("*.json")):
            if json_file.name == "java_schema.json":
                continue
            try:
                self._load_package_file(json_file)
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

        logger.info(
            f"Loaded {len(self.classes)} Java classes "
            f"from {len(self.packages)} packages"
        )

    def _load_package_file(self, file_path: Path):
        """Load a single package JSON file."""
        with open(file_path) as f:
            data = json.load(f)

        package = data["package"]
        package_classes = []

        for cls_data in data.get("classes", []):
            cls = self._parse_class(cls_data, package)
            full_name = cls.full_name
            self.classes[full_name] = cls
            package_classes.append(cls)

            # Index by short name
            if cls.name not in self.short_names:
                self.short_names[cls.name] = []
            self.short_names[cls.name].append(cls)

        if package not in self.packages:
            self.packages[package] = []
        self.packages[package].extend(package_classes)

        logger.debug(f"Loaded {len(package_classes)} classes for {package}")

    def _parse_class(self, data: dict, package: str) -> JavaClass:
        """Parse a class definition from JSON data."""
        name = data["name"]
        full_name = f"{package}.{name}"

        constructors = []
        for c in data.get("constructors", []):
            constructors.append(JavaMethod(
                name=name,
                signature=c["signature"],
                params=c.get("params", []),
                returns={},
                description=c["description"],
                static=False,
            ))

        methods = []
        static_methods = []
        for m in data.get("methods", []):
            method = JavaMethod(
                name=m["name"],
                signature=m["signature"],
                params=m.get("params", []),
                returns=m.get("returns", {}),
                description=m["description"],
                static=m.get("static", False),
                deprecated=m.get("deprecated", False),
            )
            if method.static:
                static_methods.append(method)
            else:
                methods.append(method)

        fields = []
        for f in data.get("fields", []):
            fields.append(JavaField(
                name=f["name"],
                type=f["type"],
                description=f["description"],
                static=f.get("static", False),
                final=f.get("final", False),
            ))

        return JavaClass(
            name=name,
            package=package,
            full_name=full_name,
            description=data["description"],
            constructors=constructors,
            methods=methods,
            static_methods=static_methods,
            fields=fields,
            deprecated=data.get("deprecated", False),
            docs_url=data.get("docs_url", ""),
        )

    def get_class(self, full_name: str) -> Optional[JavaClass]:
        """Get a class by its fully qualified name (e.g., 'java.net.URL')."""
        return self.classes.get(full_name)

    def get_package_classes(self, package: str) -> List[JavaClass]:
        """Get all classes in a package (e.g., 'java.lang')."""
        return self.packages.get(package, [])

    def get_all_packages(self) -> List[str]:
        """Get list of all loaded package names."""
        return sorted(self.packages.keys())

    def get_sub_packages(self, prefix: str) -> List[str]:
        """Get child package segments for a prefix.

        Example: get_sub_packages("java") -> ["lang", "net", "util", "io", "time"]
        """
        results = set()
        prefix_dot = prefix + "."
        prefix_depth = prefix.count(".") + 1

        for pkg in self.packages:
            if pkg.startswith(prefix_dot) or pkg == prefix:
                parts = pkg.split(".")
                if len(parts) > prefix_depth:
                    results.add(parts[prefix_depth])

        return sorted(results)

    def find_by_short_name(self, short_name: str) -> List[JavaClass]:
        """Find classes by their simple name (e.g., 'URL')."""
        return self.short_names.get(short_name, [])
