# Ignition for Zed

Zed extension for **[Ignition by Inductive Automation](https://inductiveautomation.com/)**.

It registers [`ignition-lsp`](https://pypi.org/project/ignition-lsp/) — the same
language server behind the Neovim and VS Code plugins — for Python and JSON
files inside an Ignition project.

## Features

- **System API completions** — 14 `system.*` modules (239+ functions) with parameter signatures
- **Java/Jython completions** — 26 packages (146 classes)
- **Project script completions** — `project.*` and `shared.*` modules, with inheritance
- **Hover documentation** — system APIs, Java classes, and project scripts
- **Go-to-definition** — API definitions and cross-file script references
- **Diagnostics** — via `ignition-lint`
- **Workspace symbols** — navigate the project script hierarchy
- **Script decode/encode** — edit Python embedded in JSON resources (see below)

## Installation

Install **Ignition** from Zed's extensions view (`zed: extensions`).

On first use in an Ignition project the extension looks for `ignition-lsp` on
your `$PATH`; if it isn't there, it creates a virtualenv in its own working
directory and `pip install`s the server. Python 3.8+ must be available.

To manage the server yourself instead, install it and point Zed at it:

```sh
pip install ignition-lsp
```

```json
{
  "lsp": {
    "ignition-lsp": {
      "binary": {
        "path": "/path/to/venv/bin/ignition-lsp"
      }
    }
  }
}
```

## Activation

The extension attaches only to worktrees with a `project.json` at the root —
that is what makes a directory an Ignition project. **Open the Ignition project
folder itself**, not a parent directory containing several projects. Without
that marker the extension declines to start, so Python and JSON files in your
other projects are left alone.

## Editing embedded scripts

Ignition stores Python inside JSON resource files as encoded strings. Zed has no
virtual-document API, so the round trip goes through a real file on disk:

1. Put the cursor on a line holding an encoded script in a JSON resource.
2. Run **Ignition: Decode …** from the code action menu (`editor: toggle code actions`).
   The script is decoded into `.ignition-scripts/` at the project root and opened,
   with full LSP support.
3. Edit it as ordinary Python.
4. Run **Ignition: Save … back to JSON** from the code action menu. The script is
   re-encoded and written back into the exact line it came from.

The header comment at the top of a decoded file records where it came from —
leave it in place; it is what the save action reads. It also fingerprints the
script as it was at decode time: if the source JSON changes underneath you, the
save is refused rather than applied to whatever now sits on that line, and you
decode again. Add `.ignition-scripts/` to your `.gitignore`.

## Settings

```json
{
  "lsp": {
    "ignition-lsp": {
      "settings": {
        "version": "8.1"
      }
    }
  }
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `version` | `"8.1"` | Ignition platform version used for API completions |

A `{ "ignition": { "version": "8.1" } }` shape is also accepted, so settings
copied from the Neovim plugin work unchanged.

## Development

```sh
rustup target add wasm32-wasip2
cargo build --target wasm32-wasip2 --release
```

Then in Zed: `zed: extensions` → **Install Dev Extension** → choose this
directory (`packages/ignition-zed`).

## Compatibility

Built against `zed_extension_api` 0.7, which requires Zed 0.205 or newer.
