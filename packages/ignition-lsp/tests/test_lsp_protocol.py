"""End-to-end tests that drive the real server over stdio JSON-RPC.

Every other test in this suite calls handler functions directly with a mocked
server. That cannot see anything pygls does between the wire and the handler —
capability advertisement, and the structuring of executeCommand arguments into
each handler's annotated parameter type. A bug there breaks decode/encode for
every client while the mocked tests stay green, so these tests speak the actual
protocol to a subprocess.
"""

import json
import pathlib
import queue
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional

import pytest

from ignition_lsp.encoding import decode
from ignition_lsp.script_files import parse_header

RESOURCE_JSON = (
    "{\n"
    '  "name": "TestView",\n'
    '  "events": {\n'
    '    "onActionPerformed": "def runAction(self, event):\\n'
    "\\tsystem.perspective.navigate(\\u0027/home\\u0027)\\n"
    '\\tprint(\\"done\\")\\n"\n'
    "  }\n"
    "}\n"
)
SCRIPT_LINE = 4
SCRIPT_KEY = "onActionPerformed"


class LspClient:
    """A minimal LSP client: real framing, real JSON-RPC, real subprocess."""

    def __init__(self, command: List[str]) -> None:
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        self._next_id = 0
        self._responses: Dict[int, dict] = {}
        self._server_requests: "queue.Queue[dict]" = queue.Queue()
        self._lock = threading.Lock()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self) -> None:
        stream = self.process.stdout
        assert stream is not None
        while True:
            headers = {}
            while True:
                raw = stream.readline()
                if not raw:
                    return
                line = raw.decode("utf-8").strip()
                if not line:
                    break
                key, _, value = line.partition(":")
                headers[key.strip().lower()] = value.strip()

            length = int(headers.get("content-length", 0))
            if not length:
                continue

            body = b""
            while len(body) < length:
                chunk = stream.read(length - len(body))
                if not chunk:
                    return
                body += chunk

            message = json.loads(body.decode("utf-8"))
            with self._lock:
                if "id" in message and "method" in message:
                    self._server_requests.put(message)  # server -> client request
                elif "id" in message:
                    self._responses[message["id"]] = message

    def _send(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        assert self.process.stdin is not None
        self.process.stdin.write(b"Content-Length: %d\r\n\r\n" % len(data) + data)
        self.process.stdin.flush()

    def notify(self, method: str, params: Any) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def request(self, method: str, params: Any, timeout: float = 30.0) -> dict:
        with self._lock:
            self._next_id += 1
            request_id = self._next_id
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})

        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if request_id in self._responses:
                    return self._responses.pop(request_id)
            # Answer server -> client requests so the server never stalls on us.
            self.drain_server_requests()
            time.sleep(0.01)
        raise TimeoutError(f"No response to {method} within {timeout}s")

    def drain_server_requests(self) -> List[dict]:
        received = []
        while True:
            try:
                request = self._server_requests.get_nowait()
            except queue.Empty:
                return received
            received.append(request)
            self._send({"jsonrpc": "2.0", "id": request["id"], "result": {"success": True}})

    def stop(self) -> None:
        try:
            self.request("shutdown", None, timeout=5)
            self.notify("exit", None)
            self.process.wait(timeout=5)
        except Exception:
            self.process.kill()


@pytest.fixture
def project(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "project.json").write_text('{"name": "TestProject"}', encoding="utf-8")
    views = root / "views" / "Main"
    views.mkdir(parents=True)
    (views / "view.json").write_text(RESOURCE_JSON, encoding="utf-8")
    return root


@pytest.fixture
def client(project: pathlib.Path):
    """A started, initialized server with the project's JSON resource open."""
    lsp = LspClient([sys.executable, "-m", "ignition_lsp.server"])
    try:
        lsp.request(
            "initialize",
            {
                "processId": None,
                "rootUri": project.as_uri(),
                "capabilities": {"window": {"showDocument": {"support": True}}},
            },
        )
        lsp.notify("initialized", {})
        source = project / "views" / "Main" / "view.json"
        lsp.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": source.as_uri(),
                    "languageId": "json",
                    "version": 1,
                    "text": RESOURCE_JSON,
                }
            },
        )
        time.sleep(0.5)  # let the project index settle
        yield lsp
    finally:
        lsp.stop()


def _decode_action(lsp: LspClient, source: pathlib.Path) -> Optional[dict]:
    result = lsp.request(
        "textDocument/codeAction",
        {
            "textDocument": {"uri": source.as_uri()},
            "range": {
                "start": {"line": SCRIPT_LINE - 1, "character": 0},
                "end": {"line": SCRIPT_LINE - 1, "character": 0},
            },
            "context": {"diagnostics": []},
        },
    )
    actions = result.get("result") or []
    return actions[0] if actions else None


class TestServerCapabilities:
    """What the server tells a client it can do."""

    def test_advertises_code_actions_and_commands(self, project: pathlib.Path) -> None:
        lsp = LspClient([sys.executable, "-m", "ignition_lsp.server"])
        try:
            response = lsp.request(
                "initialize",
                {"processId": None, "rootUri": project.as_uri(), "capabilities": {}},
            )
            capabilities = response["result"]["capabilities"]

            assert capabilities.get("codeActionProvider")
            commands = capabilities["executeCommandProvider"]["commands"]
            assert "ignition.decodeScriptToFile" in commands
            assert "ignition.saveScriptToSource" in commands
        finally:
            lsp.stop()


class TestExecuteCommandBinding:
    """Regression guard for the wire-level argument binding.

    pygls structures each executeCommand argument into the handler parameter's
    annotated type. An annotation cattrs cannot structure (a bare ``object``,
    for one) makes every command fail with "Invalid Params" at runtime while
    direct-call tests still pass.
    """

    def test_decode_command_accepts_its_arguments(
        self, client: LspClient, project: pathlib.Path
    ) -> None:
        source = project / "views" / "Main" / "view.json"
        response = client.request(
            "workspace/executeCommand",
            {
                "command": "ignition.decodeScriptToFile",
                "arguments": [{"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY}],
            },
        )

        assert "error" not in response, response.get("error")
        assert response["result"]["success"] is True

    def test_save_command_accepts_its_arguments(
        self, client: LspClient, project: pathlib.Path
    ) -> None:
        source = project / "views" / "Main" / "view.json"
        decoded = client.request(
            "workspace/executeCommand",
            {
                "command": "ignition.decodeScriptToFile",
                "arguments": [{"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY}],
            },
        )
        response = client.request(
            "workspace/executeCommand",
            {
                "command": "ignition.saveScriptToSource",
                "arguments": [{"uri": decoded["result"]["uri"]}],
            },
        )

        assert "error" not in response, response.get("error")
        assert response["result"]["success"] is True


class TestCodeActionsOverTheWire:
    """Code actions as a real client receives them."""

    def test_decode_action_offered_on_script_line(
        self, client: LspClient, project: pathlib.Path
    ) -> None:
        source = project / "views" / "Main" / "view.json"
        action = _decode_action(client, source)

        assert action is not None
        assert action["command"]["command"] == "ignition.decodeScriptToFile"
        assert action["command"]["arguments"][0]["key"] == SCRIPT_KEY

    def test_client_is_asked_to_open_the_sidecar(
        self, client: LspClient, project: pathlib.Path
    ) -> None:
        source = project / "views" / "Main" / "view.json"
        action = _decode_action(client, source)
        client.request(
            "workspace/executeCommand",
            {
                "command": action["command"]["command"],
                "arguments": action["command"]["arguments"],
            },
        )
        time.sleep(0.3)

        methods = [request["method"] for request in client.drain_server_requests()]
        assert "window/showDocument" in methods


class TestRoundTripOverTheWire:
    """The whole decode -> edit -> save cycle, driven as a client would."""

    def _decode(self, client: LspClient, project: pathlib.Path) -> pathlib.Path:
        source = project / "views" / "Main" / "view.json"
        action = _decode_action(client, source)
        assert action is not None
        response = client.request(
            "workspace/executeCommand",
            {
                "command": action["command"]["command"],
                "arguments": action["command"]["arguments"],
            },
        )
        assert response["result"]["success"] is True
        client.drain_server_requests()
        return pathlib.Path(response["result"]["path"])

    def _save(self, client: LspClient, sidecar: pathlib.Path) -> dict:
        return client.request(
            "workspace/executeCommand",
            {
                "command": "ignition.saveScriptToSource",
                "arguments": [{"uri": sidecar.as_uri()}],
            },
        )

    def _encoded_script(self, source: pathlib.Path) -> str:
        line = source.read_text(encoding="utf-8").splitlines()[SCRIPT_LINE - 1]
        return line.split(f'"{SCRIPT_KEY}": "', 1)[1].rsplit('"', 1)[0]

    def test_sidecar_is_written_with_a_valid_header(
        self, client: LspClient, project: pathlib.Path
    ) -> None:
        sidecar = self._decode(client, project)

        assert sidecar.is_file()
        ref = parse_header(sidecar.read_text(encoding="utf-8"))
        assert ref is not None
        assert ref.key == SCRIPT_KEY
        assert ref.line == SCRIPT_LINE

    def test_untouched_round_trip_is_byte_identical(
        self, client: LspClient, project: pathlib.Path
    ) -> None:
        source = project / "views" / "Main" / "view.json"
        original = source.read_text(encoding="utf-8")

        sidecar = self._decode(client, project)
        assert self._save(client, sidecar)["result"]["success"] is True

        assert source.read_text(encoding="utf-8") == original

    def test_edit_lands_in_the_source_correctly_escaped(
        self, client: LspClient, project: pathlib.Path
    ) -> None:
        source = project / "views" / "Main" / "view.json"
        original = source.read_text(encoding="utf-8")
        sidecar = self._decode(client, project)

        text = sidecar.read_text(encoding="utf-8")
        sidecar.write_text(
            text.replace('print("done")', 'print("edited <&> ok")'), encoding="utf-8"
        )
        assert self._save(client, sidecar)["result"]["success"] is True

        updated = source.read_text(encoding="utf-8")
        assert 'print("edited <&> ok")' in decode(self._encoded_script(source))
        # Stored escaped, on one line, and still parseable.
        assert "\\u003c" in updated and "\\u0026" in updated
        assert len(updated.splitlines()) == len(original.splitlines())
        assert json.loads(updated)

    def test_successive_saves_keep_working(self, client: LspClient, project: pathlib.Path) -> None:
        """The header digest must be refreshed after each save."""
        source = project / "views" / "Main" / "view.json"
        sidecar = self._decode(client, project)

        previous = 'print("done")'
        for marker in ("first", "second", "third"):
            replacement = f'print("{marker}")'
            text = sidecar.read_text(encoding="utf-8")
            sidecar.write_text(text.replace(previous, replacement), encoding="utf-8")

            response = self._save(client, sidecar)
            assert response["result"]["success"] is True, response
            assert replacement in decode(self._encoded_script(source))
            previous = replacement

    def test_stale_sidecar_is_refused(self, client: LspClient, project: pathlib.Path) -> None:
        source = project / "views" / "Main" / "view.json"
        sidecar = self._decode(client, project)

        # The source changes underneath the sidecar.
        source.write_text(
            RESOURCE_JSON.replace('print(\\"done\\")', 'print(\\"elsewhere\\")'),
            encoding="utf-8",
        )
        changed = source.read_text(encoding="utf-8")

        response = self._save(client, sidecar)

        assert response["result"]["success"] is False
        assert "changed" in response["result"]["error"].lower()
        assert source.read_text(encoding="utf-8") == changed
