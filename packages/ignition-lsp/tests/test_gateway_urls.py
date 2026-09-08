"""Tests for mapping a view.json to the Perspective client URL that shows it."""

import json
from pathlib import Path

import pytest

from ignition_lsp.gateway_urls import (
    PAGE_CONFIG_RELATIVE,
    client_url,
    find_page_for_view,
    has_route_params,
    parse_page_config,
    project_name_from_root,
    validate_gateway_url,
    view_path_from_file,
)

FIXTURE_PROJECT = Path(__file__).parent / "fixtures" / "perspective_project"


class TestViewPath:
    def test_from_view_json(self) -> None:
        view = (
            FIXTURE_PROJECT / "com.inductiveautomation.perspective/views/Overview/Pumps/view.json"
        )
        assert view_path_from_file(str(FIXTURE_PROJECT), str(view)) == "Overview/Pumps"

    def test_deeply_nested_view(self, tmp_path: Path) -> None:
        view = tmp_path / "com.inductiveautomation.perspective/views/A/B/C/view.json"
        assert view_path_from_file(str(tmp_path), str(view)) == "A/B/C"

    def test_windows_style_separators(self, tmp_path: Path) -> None:
        # Path normalisation must not leave backslashes in the view path.
        view = tmp_path / "com.inductiveautomation.perspective" / "views" / "A" / "B" / "view.json"
        assert view_path_from_file(str(tmp_path), str(view)) == "A/B"

    @pytest.mark.parametrize(
        "relative",
        [
            "com.inductiveautomation.perspective/views/A/resource.json",
            "com.inductiveautomation.perspective/views/A/thumbnail.png",
            "com.inductiveautomation.perspective/page-config/config.json",
            "ignition/script-python/utils/code.py",
            "view.json",
        ],
    )
    def test_non_views_return_none(self, tmp_path: Path, relative: str) -> None:
        assert view_path_from_file(str(tmp_path), str(tmp_path / relative)) is None

    def test_file_outside_root_returns_none(self, tmp_path: Path) -> None:
        other = tmp_path / "other" / "com.inductiveautomation.perspective/views/A/view.json"
        assert view_path_from_file(str(tmp_path / "project"), str(other)) is None


class TestPageConfig:
    def test_parses_fixture(self) -> None:
        text = (FIXTURE_PROJECT / PAGE_CONFIG_RELATIVE).read_text(encoding="utf-8")
        assert parse_page_config(text) == {
            "/": "Overview/Pumps",
            "/pumps/:id": "Overview/Pumps",
            "/settings": "Settings/Main",
        }

    def test_ignores_pages_without_a_view(self) -> None:
        text = json.dumps({"pages": {"/a": {"title": "no view"}, "/b": {"viewPath": "B"}}})
        assert parse_page_config(text) == {"/b": "B"}

    @pytest.mark.parametrize("text", ["{}", '{"pages": []}', '{"pages": null}', "[]"])
    def test_tolerates_odd_shapes(self, text: str) -> None:
        assert parse_page_config(text) == {}

    def test_invalid_json_is_treated_as_no_pages(self) -> None:
        # A broken page config must not stop a view from opening at all.
        assert parse_page_config("{oops") == {}


class TestFindPage:
    PAGES = {
        "/": "Overview/Pumps",
        "/pumps/:id": "Overview/Pumps",
        "/settings": "Settings/Main",
    }

    def test_prefers_shortest_url(self) -> None:
        assert find_page_for_view(self.PAGES, "Overview/Pumps") == "/"

    def test_prefers_pages_without_route_params(self) -> None:
        pages = {"/pumps/:id": "V", "/overview/pumps/all": "V"}
        assert find_page_for_view(pages, "V") == "/overview/pumps/all"

    def test_param_page_is_still_better_than_nothing(self) -> None:
        assert find_page_for_view({"/pumps/:id": "V"}, "V") == "/pumps/:id"

    def test_unmounted_view(self) -> None:
        assert find_page_for_view(self.PAGES, "Popups/Confirm") is None

    def test_route_params(self) -> None:
        assert has_route_params("/pumps/:id")
        assert has_route_params("/a/:b/c")
        assert not has_route_params("/pumps")
        assert not has_route_params("/time/12:30")  # colon inside a segment


class TestClientUrl:
    def test_root_page(self) -> None:
        assert (
            client_url("http://localhost:8088", "demo", "/")
            == "http://localhost:8088/data/perspective/client/demo"
        )

    def test_no_page(self) -> None:
        assert (
            client_url("http://localhost:8088", "demo")
            == "http://localhost:8088/data/perspective/client/demo"
        )

    def test_nested_page(self) -> None:
        assert (
            client_url("https://gw.example.com", "demo", "/pumps/all")
            == "https://gw.example.com/data/perspective/client/demo/pumps/all"
        )

    def test_trailing_slash_on_gateway_is_dropped(self) -> None:
        assert client_url("http://gw:8088/", "demo", "/x") == (
            "http://gw:8088/data/perspective/client/demo/x"
        )

    def test_project_name_is_percent_encoded(self) -> None:
        assert client_url("http://gw", "Demo Plant/1") == (
            "http://gw/data/perspective/client/Demo%20Plant%2F1"
        )


class TestValidateGatewayUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost:8088",
            "http://127.0.0.1:8088/",
            "http://[::1]:8088",
            "http://gateway.plant.local:8088",  # plain HTTP on a LAN is the Ignition default
            "https://gw.example.com",
            "https://gw.example.com/ignition",
            "  http://localhost:8088  ",
        ],
    )
    def test_accepts_web_urls(self, url: str) -> None:
        assert validate_gateway_url(url) is None

    @pytest.mark.parametrize(
        "url, problem",
        [
            ("javascript:alert(1)", "http:// or https://"),
            ("file:///etc/passwd", "http:// or https://"),
            ("ftp://gw:21", "http:// or https://"),
            ("localhost:8088", "http:// or https://"),
            ("gw.example.com", "http:// or https://"),
            ("http://", "host"),
            ("http:///data", "host"),
            ("http://gw:8088?x=1", "query string"),
            ("http://gw:8088#frag", "query string"),
        ],
    )
    def test_rejects_non_web_urls(self, url: str, problem: str) -> None:
        message = validate_gateway_url(url)
        assert message is not None
        assert problem in message


class TestProjectName:
    def test_directory_name(self) -> None:
        assert project_name_from_root(str(FIXTURE_PROJECT)) == "perspective_project"

    def test_trailing_separator(self, tmp_path: Path) -> None:
        assert project_name_from_root(str(tmp_path / "Plant") + "/") == "Plant"
