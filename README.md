# Ignition Dev Tools

[![CI](https://github.com/TheThoughtagen/ignition-nvim/actions/workflows/ci.yml/badge.svg)](https://github.com/TheThoughtagen/ignition-nvim/actions/workflows/ci.yml)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/WhiskeyHouse.ignition-dev-tools)](https://marketplace.visualstudio.com/items?itemName=WhiskeyHouse.ignition-dev-tools)
[![PyPI](https://img.shields.io/pypi/v/ignition-lsp)](https://pypi.org/project/ignition-lsp/)

Full IDE support for **[Ignition by Inductive Automation](https://inductiveautomation.com/)** — available for both **Neovim** and **VS Code**.

## Features

- **System API completions** — All 14 `system.*` modules (239+ functions) with parameter signatures
- **Java/Jython completions** — 26 packages (146 classes) covering standard Java libraries and Ignition SDK
- **Project script completions** — `project.*` and `shared.*` modules with inheritance support
- **Hover documentation** — Inline docs for system APIs, Java classes, and project scripts
- **Go-to-definition** — Navigate to API definitions and cross-file script references
- **Diagnostics** — Integration with `ignition-lint` for code quality checks
- **Script decode/encode** — Extract embedded Python scripts from JSON into editable buffers with full LSP support, then save them back
- **Project navigation** — Workspace symbols and efficient navigation through Ignition project hierarchies
- **Kindling integration** — Direct support for `.gwbk` gateway backup files

### VS Code Extras

- **CodeLens** — "Edit Script" actions above embedded Python in JSON resource files
- **Project Browser** — Designer-style sidebar with resource types and navigation
- **Tag Browser** — Browse tags from `ignition-git-module` tag exports
- **Component Tree** — Inspect Perspective view component hierarchies
- **Pyright/Pylance stubs** — Type stubs for Ignition APIs

## Installation

### VS Code

Install **[Ignition Dev Tools](https://marketplace.visualstudio.com/items?itemName=WhiskeyHouse.ignition-dev-tools)** from the VS Code Marketplace.

The language server is installed automatically on first activation. No manual setup required.

### Neovim (lazy.nvim)

Minimal (uses defaults from `lazy.lua` — lazy-loads on filetype + commands, auto-installs LSP):

```lua
{ 'TheThoughtagen/ignition-nvim' }
```

With custom options:

```lua
{
  'TheThoughtagen/ignition-nvim',
  opts = {
    lsp = {
      enabled = true,
      auto_start = true,
      settings = {
        ignition = {
          version = "8.1",
        },
      },
    },
    kindling = {
      enabled = true,
    },
    decoder = {
      auto_decode = true,
      auto_encode = true,
    },
  },
}
```

### LSP Server (manual)

Both editors auto-install the LSP, but you can also install it manually:

```bash
pip install --extra-index-url https://test.pypi.org/simple/ ignition-lsp
```

## Monorepo Structure

```
packages/
├── ignition-lsp/        # Python LSP server (shared by both editors)
├── ignition-nvim/       # Neovim plugin (Lua)
└── ignition-vscode/     # VS Code extension (TypeScript)
```

Top-level symlinks (`lua/`, `lsp/`, `ftdetect/`, etc.) allow the repo to work directly as a Neovim plugin when installed via lazy.nvim.

## Commands

### Neovim

| Command | Keymap | Description |
|---------|--------|-------------|
| `:IgnitionDecode` | `<localleader>id` | Decode embedded Python scripts (interactive selection) |
| `:IgnitionDecodeAll` | `<localleader>ia` | Decode all scripts in current buffer |
| `:IgnitionEncode` | `<localleader>ie` | Encode scripts back to JSON format |
| `:IgnitionListScripts` | `<localleader>il` | Show all scripts in floating window |
| `:IgnitionOpenKindling` | `<localleader>ik` | Open `.gwbk` file with Kindling |
| `:IgnitionInfo` | `<localleader>ii` | Show plugin information and status |

### VS Code

Open the Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`) and type "Ignition":

- **Decode Script at Cursor** / **Decode All Scripts in File**
- **List All Scripts in Workspace**
- **Search Resources** / **Copy Qualified Script Path**
- **Format JSON** / **Convert Indentation to Tabs**
- **Open with Kindling**

## Documentation

- **User Guide**: [online documentation](https://whiskeyhouse.github.io/ignition-nvim)
- **Vim Help**: `:help ignition-nvim`
- **VS Code README**: [packages/ignition-vscode/README.md](packages/ignition-vscode/README.md)
- **LSP Server README**: [packages/ignition-lsp/README.md](packages/ignition-lsp/README.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

## Claude Code Integration

Give Claude Code full Ignition awareness — API reference, expression language, and auto-linting — so it writes correct Ignition scripts out of the box.

**Option A: Plugin** (global, works across all projects)

```bash
claude plugin add --from whiskeyhouse/ignition-nvim --path claude-code-plugin
```

**Option B: Templates** (per-project, check into your repo)

```bash
curl -sL https://raw.githubusercontent.com/whiskeyhouse/ignition-nvim/main/templates/setup.sh | bash
```

See [claude-code-plugin/README.md](claude-code-plugin/README.md) and [templates/README.md](templates/README.md) for details.

## Part of the Whiskey House Ignition Developer Toolkit

- **[Ignition Dev Tools](https://github.com/TheThoughtagen/ignition-dev-tools)** — Neovim + VS Code IDE support (this repo)
- **[ignition-lint](https://github.com/TheThoughtagen/ignition-lint)** — Static analysis for Ignition Python scripts
- **[ignition-git-module](https://github.com/bmusson/ignition-git-module)** — Native Git inside Ignition Designer

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
