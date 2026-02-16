---
sidebar_position: 1
---

# Installation

## Plugin Installation

### lazy.nvim (Recommended)

The simplest install — lazy.nvim auto-discovers the plugin spec from `lazy.lua`:

```lua
{ 'TheThoughtagen/ignition-nvim' }
```

This gives you sensible defaults:
- Lazy-loading on the `ignition` filetype and all commands
- Automatic LSP server installation from PyPI (latest version)
- Version tracking via git tags (automatically updates when new releases are published)

To customize options:

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

### packer.nvim

```lua
use {
  'TheThoughtagen/ignition-nvim',
  config = function()
    require('ignition').setup()
  end,
}
```

After installing, you'll need to manually install the LSP server (see below).

### Manual Installation

Clone the repository into your Neovim packages directory:

```bash
git clone https://github.com/TheThoughtagen/ignition-nvim.git \
  ~/.local/share/nvim/site/pack/plugins/start/ignition-nvim
```

Add the setup call to your `init.lua`:

```lua
require('ignition').setup()
```

## LSP Server Installation

The Python LSP server provides completions, hover docs, and diagnostics for Ignition's `system.*` and Java APIs.

### Automatic (lazy.nvim)

If you're using lazy.nvim with the default spec, the LSP server installs automatically from PyPI via the `build` step. The latest version is automatically downloaded and kept up to date. No extra action needed.

### Manual

Install the latest version from PyPI (uses TestPyPI for ignition-lint-toolkit beta):

```bash
pip install --upgrade --extra-index-url https://test.pypi.org/simple/ ignition-lsp
```

Or for development, install in editable mode from a local checkout:

```bash
cd /path/to/ignition-nvim/lsp
pip install -e .
```

The plugin auto-detects the LSP server location in this order:

1. **Plugin venv** — `lsp/venv/bin/ignition-lsp` (development mode)
2. **System install** — `ignition-lsp` on `$PATH`
3. **System Python** — `python -m ignition_lsp`

## Requirements

- **Neovim** >= 0.11.0 (uses `vim.lsp.start()`)
- **Python** >= 3.8 (for the LSP server)
- **pip** (for installing the LSP server)

### Optional

- [Kindling](https://github.com/paul-griffith/kindling) — for `.gwbk` gateway backup file support
