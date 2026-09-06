"""Map a Perspective view file to the URL that shows it on a Gateway.

Perspective does not address views by path. A browser opens a *page*, and the
project's page configuration maps page URLs to the view each one mounts as its
primary view. So opening "this view" means finding a page that mounts it. A
view used only as an embedded view or a popup is mounted by no page; for those
the best available target is the project's client root, and the caller should
say so.

This module is pure logic: it parses what it is handed and builds strings. The
server reads the files and asks the client to open the result.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

# Where views and page config live inside an Ignition 8.1 project export.
PERSPECTIVE_DIR = "com.inductiveautomation.perspective"
VIEWS_DIR = "views"
PAGE_CONFIG_RELATIVE = f"{PERSPECTIVE_DIR}/page-config/config.json"


def view_path_from_file(project_root: str, view_file: str) -> Optional[str]:
    """The Perspective view path for a view.json, or None if it is not one.

    `<root>/com.inductiveautomation.perspective/views/Tanks/Detail/view.json`
    is the view `Tanks/Detail`. Anything outside the views directory, or not
    named view.json, is not a view.
    """
    try:
        relative = Path(view_file).resolve().relative_to(Path(project_root).resolve())
    except ValueError:
        return None

    parts = relative.parts
    if len(parts) < 4 or parts[0] != PERSPECTIVE_DIR or parts[1] != VIEWS_DIR:
        return None
    if parts[-1] != "view.json":
        return None
    return "/".join(parts[2:-1])


def parse_page_config(text: str) -> Dict[str, str]:
    """Return a mapping of page URL -> primary view path from page config.

    The Gateway writes `{"pages": {"/url": {"viewPath": "Some/View", ...}}}`.
    Malformed or unexpected input yields an empty mapping rather than an error;
    a missing page config is an ordinary state for a project.
    """
    try:
        data = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}

    pages = data.get("pages")
    if not isinstance(pages, dict):
        return {}

    mapping: Dict[str, str] = {}
    for url, page in pages.items():
        if not isinstance(url, str) or not isinstance(page, dict):
            continue
        view_path = page.get("viewPath")
        if isinstance(view_path, str) and view_path:
            mapping[url] = view_path
    return mapping


def find_page_for_view(pages: Dict[str, str], view_path: str) -> Optional[str]:
    """The page URL mounting `view_path`, preferring one without URL params.

    Several pages can mount the same view. A page like `/pumps/:id` cannot be
    opened without knowing the param, so parameter-free pages win; among
    those, the shortest URL is the most likely to be the canonical one.
    """
    matches = [url for url, mounted in pages.items() if mounted == view_path]
    if not matches:
        return None
    return min(matches, key=lambda u: (has_route_params(u), len(u), u))


def has_route_params(page_url: str) -> bool:
    """True when a page URL contains a `:param` segment."""
    return any(segment.startswith(":") for segment in page_url.split("/"))


def client_url(gateway_url: str, project_name: str, page_url: Optional[str] = None) -> str:
    """The Perspective client URL for a project, optionally at a page.

    `page_url` is a page-config URL like `/tanks/:id`; route params are left
    as-is because the caller cannot know their values.
    """
    base = gateway_url.rstrip("/")
    url = f"{base}/data/perspective/client/{quote(project_name, safe='')}"
    if page_url and page_url != "/":
        url += "/" + page_url.lstrip("/")
    return url


def project_name_from_root(project_root: str, project_json: Optional[Dict[str, Any]] = None) -> str:
    """The project's name as the Gateway knows it.

    The directory name is the project name in an Ignition export; project.json
    carries a title and description but not the name. A `name` key is honoured
    if one is present anyway.
    """
    if isinstance(project_json, dict):
        name = project_json.get("name")
        if isinstance(name, str) and name:
            return name
    return Path(project_root).resolve().name
