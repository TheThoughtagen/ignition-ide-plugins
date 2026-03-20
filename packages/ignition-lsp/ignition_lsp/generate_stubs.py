"""Generate static .pyi stub files for Ignition system.* API.

Reads api_db/*.json and produces stubs/system/__init__.pyi and
stubs/system/{module}.pyi so Pyright/Pylance can type-check Ignition scripts.

Run:  python -m ignition_lsp.generate_stubs
"""

import json
import re
from pathlib import Path

API_DB = Path(__file__).parent / "api_db"
STUBS_DIR = Path(__file__).parent / "stubs"

# Map Ignition type annotations to Python typing equivalents
TYPE_MAP = {
    "String": "str",
    "string": "str",
    "int": "int",
    "Integer": "int",
    "float": "float",
    "Float": "float",
    "Double": "float",
    "double": "float",
    "boolean": "bool",
    "Boolean": "bool",
    "bool": "bool",
    "None": "None",
    "void": "None",
    "Object": "Any",
    "object": "Any",
    "Function": "Callable[..., Any]",
    "Callable": "Callable[..., Any]",
    "Dictionary": "dict[str, Any]",
    "Dict": "dict[str, Any]",
    "PyDictionary": "dict[str, Any]",
    "PySequence": "list[Any]",
    "Dataset": "Any",
    "BasicDataset": "Any",
    "QualifiedValue": "Any",
    "QualityCode": "Any",
    "TagPath": "str",
    "Color": "Any",
    "Date": "Any",
    "JComponent": "Any",
    "JFrame": "Any",
    "WindowUtilities": "Any",
}


def _convert_type(raw: str) -> str:
    """Convert an Ignition type string to a Python type annotation."""
    if not raw:
        return "Any"

    # Handle List[X] / List
    m = re.match(r"List\[(.+)\]", raw)
    if m:
        inner = _convert_type(m.group(1))
        return f"list[{inner}]"
    if raw == "List":
        return "list[Any]"

    # Handle String | List[String] union types
    if "|" in raw:
        parts = [_convert_type(p.strip()) for p in raw.split("|")]
        return " | ".join(parts)

    return TYPE_MAP.get(raw, raw)


def _generate_module_stub(api_file: Path) -> tuple[str, str, str]:
    """Generate a .pyi stub from an api_db JSON file.

    Returns (module_name, submodule_name, stub_content).
    e.g. ("system.tag", "tag", "def readBlocking(...) -> ...: ...")
    """
    data = json.loads(api_file.read_text(encoding="utf-8"))
    module = data["module"]  # e.g. "system.tag"
    submodule = module.split(".")[-1]  # e.g. "tag"

    lines = [
        f'"""Type stubs for {module} — auto-generated from api_db."""',
        "",
        "from typing import Any, Callable, Optional",
        "",
    ]

    for func in data.get("functions", []):
        # Build parameter list
        params = []
        for p in func.get("params", []):
            ptype = _convert_type(p.get("type", "Any"))
            pname = p["name"]
            if p.get("optional"):
                default = p.get("default", "None")
                # Clean up default values for valid Python syntax
                if default in ("None", "null", ""):
                    params.append(f"{pname}: {ptype} = None")
                elif default.lstrip("-").isdigit() or default in ("True", "False"):
                    params.append(f"{pname}: {ptype} = {default}")
                elif default.lstrip("-").replace(".", "", 1).isdigit():
                    params.append(f"{pname}: {ptype} = {default}")
                else:
                    # String default — quote it
                    params.append(f'{pname}: {ptype} = "{default}"')
            else:
                params.append(f"{pname}: {ptype}")

        param_str = ", ".join(params)

        # Return type
        ret = func.get("returns", {})
        ret_type = _convert_type(ret.get("type", "Any"))

        # Docstring
        desc = func.get("description", "")

        lines.append(f"def {func['name']}({param_str}) -> {ret_type}:")
        if desc:
            lines.append(f'    """{desc}"""')
        lines.append("    ...")
        lines.append("")

    return module, submodule, "\n".join(lines)


def generate_all() -> None:
    """Generate all system.* stubs from api_db."""
    system_dir = STUBS_DIR / "system"
    system_dir.mkdir(parents=True, exist_ok=True)

    submodules = []

    for api_file in sorted(API_DB.glob("system_*.json")):
        module, submodule, content = _generate_module_stub(api_file)
        stub_path = system_dir / f"{submodule}.pyi"
        stub_path.write_text(content, encoding="utf-8")
        submodules.append(submodule)
        print(f"  {module} -> stubs/system/{submodule}.pyi")

    # Generate system/__init__.pyi that re-exports submodules
    init_lines = [
        '"""Type stubs for Ignition system module — auto-generated from api_db."""',
        "",
    ]
    for sub in sorted(submodules):
        init_lines.append(f"from . import {sub} as {sub}")
    init_lines.append("")

    (system_dir / "__init__.pyi").write_text(
        "\n".join(init_lines), encoding="utf-8"
    )
    print(f"  system/__init__.pyi ({len(submodules)} submodules)")


if __name__ == "__main__":
    print("Generating system.* stubs from api_db...")
    generate_all()
    print("Done.")
