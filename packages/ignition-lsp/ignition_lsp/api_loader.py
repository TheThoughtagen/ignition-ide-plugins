"""API Loader - Loads and indexes Ignition API definitions."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class APIFunction:
    """Represents a single Ignition API function."""

    def __init__(self, data: Dict, module: str):
        self.name = data["name"]
        self.module = module
        self.full_name = f"{module}.{self.name}"
        self.signature = data["signature"]
        self.params = data.get("params", [])
        self.returns = data.get("returns", {})
        self.description = data["description"]
        self.long_description = data.get("long_description", "")
        self.scope = data.get("scope", [])
        self.deprecated = data.get("deprecated", False)
        self.since = data.get("since", "8.0")
        self.docs_url = data.get("docs_url", "")
        self.examples = data.get("examples", [])

    def get_markdown_doc(self) -> str:
        """Generate Markdown documentation for hover."""
        lines = []

        # Header
        lines.append(f"**{self.full_name}**")
        lines.append("")

        # Signature
        lines.append("```python")
        lines.append(f"{self.full_name}({self._format_params()})")
        if self.returns.get("type"):
            lines.append(f"  -> {self.returns['type']}")
        lines.append("```")
        lines.append("")

        # Description
        lines.append(self.description)
        if self.long_description:
            lines.append("")
            lines.append(self.long_description)
        lines.append("")

        # Parameters
        if self.params:
            lines.append("**Parameters:**")
            for param in self.params:
                optional = " (optional)" if param.get("optional") else ""
                default = f" = {param.get('default')}" if param.get("default") else ""
                lines.append(f"- `{param['name']}`: {param['type']}{optional}{default}")
                lines.append(f"  {param['description']}")
            lines.append("")

        # Return value
        if self.returns:
            lines.append("**Returns:**")
            lines.append(f"{self.returns.get('type', 'Any')} - {self.returns.get('description', '')}")
            lines.append("")

        # Scope
        if self.scope:
            lines.append(f"**Scope:** {', '.join(self.scope)}")
            lines.append("")

        # Documentation link
        if self.docs_url:
            lines.append(f"[Documentation]({self.docs_url})")

        return "\n".join(lines)

    def _format_params(self) -> str:
        """Format parameters for signature display."""
        parts = []
        for param in self.params:
            if param.get("optional"):
                default = param.get("default", "None")
                parts.append(f"{param['name']}={default}")
            else:
                parts.append(param['name'])
        return ", ".join(parts)

    def get_completion_snippet(self) -> str:
        """Generate snippet for completion insertion."""
        # Create snippet with numbered placeholders
        parts = []
        for i, param in enumerate(self.params, 1):
            if not param.get("optional"):
                parts.append(f"${{{i}:{param['name']}}}")

        if parts:
            return f"{self.name}({', '.join(parts)})$0"
        else:
            return f"{self.name}()$0"


class IgnitionAPILoader:
    """Loads and indexes Ignition API definitions."""

    def __init__(self, version: str = "8.1"):
        self.version = version
        self.api_db: Dict[str, APIFunction] = {}  # full_name -> APIFunction
        self.modules: Dict[str, List[APIFunction]] = {}  # module -> [functions]
        self._load_all()

    def _load_all(self):
        """Load all API definition files."""
        api_db_dir = Path(__file__).parent / "api_db"

        if not api_db_dir.exists():
            logger.warning(f"API database directory not found: {api_db_dir}")
            return

        # Load all JSON files
        for json_file in api_db_dir.glob("system_*.json"):
            try:
                self._load_module_file(json_file)
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

        logger.info(f"Loaded {len(self.api_db)} functions from {len(self.modules)} modules")

    def _load_module_file(self, file_path: Path):
        """Load a single module API file."""
        with open(file_path) as f:
            data = json.load(f)

        module = data["module"]
        module_version = data.get("version", "8.0+")

        # Check version compatibility
        if not self._is_compatible_version(module_version):
            logger.debug(f"Skipping {module} (requires {module_version}, have {self.version})")
            return

        # Create APIFunction objects
        functions = []
        for func_data in data.get("functions", []):
            func = APIFunction(func_data, module)
            self.api_db[func.full_name] = func
            functions.append(func)

        self.modules[module] = functions
        logger.debug(f"Loaded {len(functions)} functions for {module}")

    def _is_compatible_version(self, required_version: str) -> bool:
        """Check if current version is compatible with required version."""
        # Simple version check - can be enhanced
        if "+" in required_version:
            required_version = required_version.replace("+", "")

        try:
            req_parts = required_version.split(".")
            cur_parts = self.version.split(".")

            for req, cur in zip(req_parts, cur_parts):
                if int(cur) < int(req):
                    return False
        except (ValueError, IndexError):
            return True

        return True

    def get_function(self, full_name: str) -> Optional[APIFunction]:
        """Get function by full name (e.g., 'system.tag.readBlocking')."""
        return self.api_db.get(full_name)

    def get_module_functions(self, module: str) -> List[APIFunction]:
        """Get all functions for a module (e.g., 'system.tag')."""
        return self.modules.get(module, [])

    def get_all_modules(self) -> List[str]:
        """Get list of all loaded modules."""
        return list(self.modules.keys())

    def search_functions(self, prefix: str) -> List[APIFunction]:
        """Search for functions starting with prefix (e.g., 'system.tag.')."""
        results = []
        for full_name, func in self.api_db.items():
            if full_name.startswith(prefix):
                results.append(func)
        return results

    def get_module_from_prefix(self, prefix: str) -> Optional[str]:
        """Determine module from a prefix (e.g., 'system.tag.' -> 'system.tag')."""
        parts = prefix.rstrip(".").split(".")
        if len(parts) >= 2:
            potential_module = ".".join(parts[:2])  # e.g., "system.tag"
            if potential_module in self.modules:
                return potential_module
        return None
