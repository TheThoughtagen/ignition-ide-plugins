#!/usr/bin/env python3
"""
Scrape Ignition API documentation and generate JSON API definitions.

Usage:
    python scrape_ignition_api.py --module system.tag --version 8.1
    python scrape_ignition_api.py --all --version 8.1
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

# Base URL for Ignition documentation
IGNITION_DOCS_BASE = "https://www.docs.inductiveautomation.com/docs/{version}/appendix/scripting-functions"

# Modules to scrape
MODULES = {
    "system.tag": "system-tag",
    "system.db": "system-db",
    "system.perspective": "system-perspective",
    "system.util": "system-util",
    "system.net": "system-net",
    "system.date": "system-date",
    "system.alarm": "system-alarm",
    "system.security": "system-security",
}


def fetch_url(url: str) -> str:
    """Fetch URL content with user agent."""
    headers = {
        "User-Agent": "Ignition-LSP-API-Scraper/1.0"
    }
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return response.read().decode('utf-8')
    except URLError as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return ""


def parse_function_list(html: str, module: str) -> List[str]:
    """Extract list of function names from module index page."""
    functions = []

    # Look for links to function pages
    # Pattern: href="/docs/8.1/appendix/scripting-functions/system-tag/system-tag-readBlocking"
    pattern = rf'href="[^"]*/{module}/({module}-[^"]+)"'
    matches = re.findall(pattern, html)

    for match in matches:
        # Extract function name from URL slug
        # "system-tag-readBlocking" -> "readBlocking"
        func_name = match.replace(f"{module}-", "")
        if func_name and not func_name.startswith("deprecated"):
            functions.append(func_name)

    return list(set(functions))


def parse_function_details(html: str, func_name: str, module: str) -> Optional[Dict]:
    """Parse function details from function documentation page."""
    # This is a simplified parser - real implementation would be more robust

    # Extract signature
    # Look for code blocks with the function signature
    sig_pattern = rf'{func_name}\([^)]*\)'
    sig_match = re.search(sig_pattern, html)
    signature = sig_match.group(0) if sig_match else f"{func_name}()"

    # Extract description (simplified - would need better HTML parsing)
    # Look for first paragraph after function name
    desc_pattern = rf'<p>([^<]+)</p>'
    desc_matches = re.findall(desc_pattern, html)
    description = desc_matches[0] if desc_matches else f"{module}.{func_name} function"

    return {
        "name": func_name,
        "signature": signature,
        "params": [],  # TODO: Parse parameters from docs
        "returns": {"type": "Any", "description": "Return value"},
        "description": description,
        "scope": ["Gateway", "Vision", "Perspective"],  # Default - would parse from docs
        "deprecated": False,
        "since": "8.0",
        "docs_url": f"https://www.docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/{MODULES[module]}/{MODULES[module]}-{func_name}"
    }


def scrape_module(module: str, version: str = "8.1") -> Dict:
    """Scrape all functions for a module."""
    print(f"Scraping {module} for Ignition {version}...")

    url_slug = MODULES.get(module)
    if not url_slug:
        print(f"Unknown module: {module}", file=sys.stderr)
        return {"module": module, "version": version, "functions": []}

    # Fetch module index page
    index_url = f"{IGNITION_DOCS_BASE.format(version=version)}/{url_slug}"
    print(f"  Fetching: {index_url}")
    html = fetch_url(index_url)

    if not html:
        print(f"  Failed to fetch module page", file=sys.stderr)
        return {"module": module, "version": version, "functions": []}

    # Get list of functions
    function_names = parse_function_list(html, url_slug)
    print(f"  Found {len(function_names)} functions")

    # Fetch details for each function
    functions = []
    for func_name in function_names:
        print(f"    - {func_name}")
        func_url = f"{index_url}/{url_slug}-{func_name}"
        func_html = fetch_url(func_url)

        if func_html:
            func_details = parse_function_details(func_html, func_name, module)
            if func_details:
                functions.append(func_details)

    return {
        "module": module,
        "version": f"{version}+",
        "functions": functions
    }


def save_api_db(data: Dict, output_dir: Path):
    """Save API database to JSON file."""
    module_name = data["module"].replace(".", "_")
    output_file = output_dir / f"{module_name}.json"

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✓ Saved {len(data['functions'])} functions to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Scrape Ignition API documentation")
    parser.add_argument("--module", help="Module to scrape (e.g., system.tag)")
    parser.add_argument("--all", action="store_true", help="Scrape all modules")
    parser.add_argument("--version", default="8.1", help="Ignition version (default: 8.1)")
    parser.add_argument("--output", help="Output directory", default="../ignition_lsp/api_db")

    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / "ignition_lsp" / "api_db"
    if args.output:
        output_dir = Path(args.output)

    output_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        for module in MODULES.keys():
            data = scrape_module(module, args.version)
            save_api_db(data, output_dir)
    elif args.module:
        data = scrape_module(args.module, args.version)
        save_api_db(data, output_dir)
    else:
        parser.print_help()
        sys.exit(1)

    print("\n✓ API scraping complete!")


if __name__ == "__main__":
    main()
