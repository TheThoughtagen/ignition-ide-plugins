# Ignition Dev Tools

Full IDE support for [Inductive Automation's Ignition](https://inductiveautomation.com/) SCADA platform in Visual Studio Code.

Provides completions, hover documentation, diagnostics, go-to-definition, script decode/encode, and a project browser for Ignition projects — whether you're working with gateway exports, `ignition-git-module` repos, or raw project files.

## Features

### Language Server (ignition-lsp)

- **Completions** for all `system.*` APIs (14 modules, 239+ functions) with parameter signatures
- **Hover documentation** — full API docs inline as you type
- **Diagnostics** — real-time linting for Jython scripts via `ignition-lint`
- **Go-to-definition** — jump to `system.*` function definitions and project scripts
- **Java/Jython completions** — `java.lang`, `java.util`, `javax.swing`, and more
- **Python stdlib completions** — standard library functions available in Jython

The LSP is installed automatically on first activation. No manual setup required.

### Script Editing

- **CodeLens** — "Edit Script" actions appear above embedded Python scripts in JSON resource files
- **Decode/Encode** — extract scripts from Ignition's JSON format into editable Python buffers, then save them back
- **Decode All** — extract every script in a file at once
- **Auto tab conversion** — automatically converts space indentation to tabs (Ignition convention) when opening Python files

### Project Browser

A sidebar view that mirrors the Ignition Designer's project tree:

- Discovers Ignition projects by finding `project.json` files
- Shows resource types: Script Libraries, Perspective Views, Vision Windows, Named Queries, and more
- Click any resource to open its primary file (`code.py`, `view.json`, etc.)
- Supports both standard Ignition project format and `ignition-git-module` format (`com.inductiveautomation.*` directories)

### Tag Browser

Browse tags from `ignition-git-module` tag exports:

- Displays tag providers, folders, and individual tags
- Shows tag metadata: data type, value source, UDT type
- UDT types and instances expand to show member tags
- Right-click to copy the full Ignition tag path (e.g., `[WHK01]WH/Distillery01/Temperature`)

### Component Tree

Inspect Perspective view component hierarchies:

- Open any `view.json` file to see the component tree
- Decode embedded scripts directly from the tree
- Navigate complex nested views visually

### Kindling Integration

- Right-click `.gwbk`, `.modl`, or `.idb` files to open them with [Kindling](https://github.com/paul-griffith/kindling)

## Quick Start

1. **Install** the extension from the VS Code Marketplace
2. **Open** a folder containing an Ignition project (with a `project.json` file)
3. The extension activates automatically and prompts to install the language server
4. Start editing — completions, hover docs, and diagnostics work immediately on Python and JSON files

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `ignition.lsp.path` | `""` | Path to the `ignition-lsp` executable. Leave empty for auto-install. |
| `ignition.ignitionVersion` | `"8.1"` | Ignition platform version for API completions (`8.0` or `8.1`). |
| `ignition.codeLens.enabled` | `true` | Show "Edit Script" CodeLens above embedded scripts in JSON files. |
| `ignition.diagnostics.enabled` | `true` | Enable inline diagnostics for Python scripts. |
| `ignition.autoConvertTabs` | `true` | Auto-convert space indentation to tabs when opening Python files. |
| `ignition.kindling.path` | `""` | Path to the Kindling executable. Leave empty for auto-detection. |

## Commands

Open the Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`) and type "Ignition" to see all available commands:

- **Ignition: Decode Script at Cursor** — extract the script under cursor into an editable buffer
- **Ignition: Decode All Scripts in File** — extract all scripts in the current JSON file
- **Ignition: List All Scripts in Workspace** — find and list all scripts across the project
- **Ignition: Format JSON** — format Ignition JSON files
- **Ignition: Convert Indentation to Tabs** — manually convert spaces to tabs
- **Ignition: Search Resources** — search across project resources
- **Ignition: Copy Qualified Script Path** — copy the full script path for use in Ignition
- **Ignition: Open with Kindling** — open `.gwbk`/`.modl` files with Kindling

## Requirements

- VS Code 1.85 or later
- Python 3.8+ (for automatic LSP installation)

## Part of the Whiskey House Ignition Developer Toolkit

- **[Ignition Dev Tools](https://github.com/TheThoughtagen/ignition-dev-tools)** — VS Code + Neovim IDE support (this extension)
- **[ignition-lint](https://github.com/TheThoughtagen/ignition-lint)** — static analysis for Ignition Python scripts
- **[ignition-git-module](https://github.com/bmusson/ignition-git-module)** — native Git inside Ignition Designer

## License

MIT
