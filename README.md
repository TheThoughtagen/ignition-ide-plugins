# ignition.nvim
[![Release](https://github.com/TheThoughtagen/ignition-nvim/actions/workflows/release.yml/badge.svg)](https://github.com/TheThoughtagen/ignition-nvim/actions/workflows/release.yml)

A comprehensive Neovim plugin providing development support for **Ignition by Inductive Automation** projects.

## Features

- **Automatic Script Decoding/Encoding**: Seamlessly work with Python scripts embedded in JSON configurations
- **Comprehensive LSP Integration**: Full code intelligence for Ignition development
  - **System API completions** — All 14 `system.*` modules (239+ functions)
  - **Java/Jython completions** — 26 packages (146 classes) covering standard Java libraries and Ignition SDK
  - **Project script completions** — `project.*` and `shared.*` modules with inheritance support
  - **Perspective JSON completions** — Component types, props, and event handlers for view.json files
  - **Hover documentation** — Inline docs for system APIs, Java classes, and project scripts
  - **Go-to-definition** — Navigate to API definitions and cross-file script references
  - **Diagnostics** — Integration with ignition-lint for code quality checks
- **Gateway Backup Management**: Direct integration with Kindling for `.gwbk` file handling
- **Project Navigation**: Workspace symbols and efficient navigation through Ignition project hierarchies
- **File Type Detection**: Automatic recognition of Ignition file formats

## Architecture

This plugin uses a hybrid approach:
- **Lua Plugin**: Core functionality, file handlers, commands, and UI integration
- **Python LSP Server**: Advanced code intelligence and project analysis

## Documentation

- **User Guide**: See `docs/` directory or [online documentation](https://whiskeyhouse.github.io/ignition-nvim)
- **Vim Help**: `:help ignition-nvim`
- **Developer Guide**: [CLAUDE.md](CLAUDE.md)
- **Claude Code Plugin**: [claude-code-plugin/README.md](claude-code-plugin/README.md)
- **Claude Code Templates**: [templates/README.md](templates/README.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

## Installation

### Using [lazy.nvim](https://github.com/folke/lazy.nvim)

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
          version = "8.1", -- Your Ignition version
        },
      },
    },
    kindling = {
      enabled = true,
      -- path = '/path/to/kindling', -- Optional: specify Kindling path
    },
    decoder = {
      auto_decode = true,
      auto_encode = true,
    },
  },
}
```

### Using [packer.nvim](https://github.com/wbthomason/packer.nvim)

```lua
use {
  'whiskeyhouse/ignition-nvim',
  requires = { 'neovim/nvim-lspconfig' },
  config = function()
    require('ignition').setup()
  end,
}
```

## LSP Server Installation

The Python LSP server provides advanced code intelligence features. With lazy.nvim, it is
installed automatically via the `build` step. To install manually:

```bash
# Install from PyPI (uses TestPyPI for ignition-lint-toolkit beta)
pip install --extra-index-url https://test.pypi.org/simple/ ignition-lsp

# Or install from source (inside the plugin directory)
cd lsp
pip install -e .
```

## Commands

### Script Management
- `:IgnitionDecode` - Decode embedded Python scripts (interactive selection if multiple)
- `:IgnitionDecodeAll` - Decode all scripts in current buffer
- `:IgnitionEncode` - Encode scripts back to JSON format (from virtual buffer)
- `:IgnitionListScripts` - Show all scripts in current buffer in floating window

### Integration
- `:IgnitionOpenKindling [file]` - Open `.gwbk` file with Kindling
- `:IgnitionInfo` - Show plugin information and status

### Default Keymaps (in Ignition files)
- `<localleader>id` - Decode scripts
- `<localleader>ia` - Decode all scripts
- `<localleader>il` - List all scripts
- `<localleader>ie` - Encode scripts back to JSON
- `<localleader>ii` - Show plugin info
- `<localleader>ik` - Open in Kindling (`.gwbk` files only)

## Usage

### Decoding Scripts

When you open an Ignition JSON file containing embedded Python scripts, the plugin will automatically detect them and notify you.

**Single Script:**
```
:IgnitionDecode
```
or press `<localleader>id` to decode the script into a new split window with full Python syntax highlighting and editing capabilities.

**Multiple Scripts:**
If the file contains multiple scripts, you'll be presented with an interactive selection menu showing a preview of each script.

**All Scripts:**
```
:IgnitionDecodeAll
```
or press `<localleader>ia` to decode all scripts at once.

### Editing and Saving

1. Edit the decoded Python script in the virtual buffer with full LSP support
2. Save the buffer (`:w` or `<leader>w`) to automatically encode and update the original JSON file
3. The source JSON file will be marked as modified - save it to persist changes

### Script Encoding Method

The plugin uses the same encoding method as Ignition Flint:
- Standard JSON string escaping (`\"`, `\\n`, `\\t`, etc.)
- Unicode escapes for special characters (`<` → `\u003c`, `>` → `\u003e`, `&` → `\u0026`, `=` → `\u003d`, `'` → `\u0027`)
- **Not base64** - scripts remain partially human-readable in JSON

Reference: [ignition-flint encoding](https://github.com/keith-gamble/ignition-flint/blob/master/src/utils/textEncoding.ts)

## Configuration

Default configuration:

```lua
{
  lsp = {
    enabled = true,
    auto_start = true,
    cmd = nil, -- Auto-detected
    settings = {
      ignition = {
        version = "8.1",
        sdk_path = nil,
      },
    },
  },
  kindling = {
    enabled = true,
    path = nil, -- Auto-detected
  },
  decoder = {
    auto_decode = true,
    auto_encode = true,
    create_scratch_buffer = true,
  },
  ui = {
    show_notifications = true,
    show_statusline = true,
  },
}
```

## Supported File Types

- `.gwbk` - Gateway Backup files
- `.proj` - Ignition Project files
- `resource.json` - Resource definitions with embedded scripts
- `tags.json` - Tag configurations
- `data.json` - Data structures

## Requirements

- Neovim >= 0.8.0
- Python >= 3.8 (for LSP server)
- [nvim-lspconfig](https://github.com/neovim/nvim-lspconfig) (optional, for LSP features)
- [Kindling](https://github.com/paul-griffith/kindling) (optional, for `.gwbk` support)

## Development Status

This plugin is under active development. See our [Linear project](https://linear.app/whiskey-house-eandt/project/ignition-neovim-plugin-8b7522ece7b1) for current progress.

### Roadmap

- [x] Basic project structure
- [x] File type detection for Ignition files
- [x] Script decoder/encoder implementation
- [x] Virtual document system for editing scripts
- [x] Auto-detection of embedded scripts
- [x] Interactive script selection
- [x] LSP server with Ignition API completion (14 modules, 239 functions)
- [x] Project indexing and navigation (workspace symbols, cross-file completions)
- [x] Go-to-definition for system.* and project scripts
- [x] Kindling integration for .gwbk files
- [x] Comprehensive testing suite (162 Python + 107 Lua tests)
- [x] Full documentation (Docusaurus, Vim help, guides)
- [x] CI workflow (GitHub Actions)

## Claude Code Integration

Give Claude Code full Ignition awareness — API reference, expression language, and auto-linting — so it writes correct Ignition scripts out of the box.

**Option A: Plugin** (global, works across all projects)

```bash
claude plugin add --from whiskeyhouse/ignition-nvim --path claude-code-plugin
```

**Option B: Templates** (per-project, check into your repo)

```bash
# From your Ignition project root
curl -sL https://raw.githubusercontent.com/whiskeyhouse/ignition-nvim/main/templates/setup.sh | bash
```

Both include auto-lint hooks and the full `system.*` + expression function reference. See [claude-code-plugin/README.md](claude-code-plugin/README.md) and [templates/README.md](templates/README.md) for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Testing guidelines
- Code style requirements
- Pull request process

For current tasks and priorities, check the [GitHub issues](https://github.com/whiskeyhouse/ignition-nvim/issues).

## License

MIT License - see LICENSE file for details

## Acknowledgments

Inspired by [Ignition Flint](https://marketplace.visualstudio.com/items?itemName=Keith-gamble.ignition-flint) for VS Code.
