# Development Scripts

Utilities for testing and developing ignition-nvim locally.

## Scripts

### `diagnose-lsp.lua`
Comprehensive LSP diagnostics to troubleshoot completion issues.

**Usage:**
```vim
:luafile dev-scripts/diagnose-lsp.lua
```

**What it does:**
- Checks Neovim version (0.11+ required)
- Verifies plugin is loaded
- Checks LSP server availability
- Inspects current buffer filetype
- Searches for project.json root marker
- Lists active LSP clients
- Attempts to start LSP if not running
- Shows relevant log file paths

**Use when:** LSP completions aren't working.

### `load-plugin.lua`
Manually load the plugin in a running Neovim instance for quick testing.

**Usage:**
```vim
:luafile dev-scripts/load-plugin.lua
```

**What it does:**
- Adds plugin to runtime and Lua package paths
- Clears cached modules for hot-reloading
- Sources plugin commands
- Runs `setup()` with default config
- Lists available commands

### `test-config.lua`
Full LSP configuration test with deferred status check.

**Usage:**
```vim
:luafile dev-scripts/test-config.lua
```

**What it does:**
- Clears module cache
- Loads plugin
- Starts LSP server manually (auto_start = false)
- Waits 2 seconds and reports LSP status

### `test-config-simple.lua`
Minimal direct LSP start test using `vim.lsp.start()`.

**Usage:**
```vim
:luafile dev-scripts/test-config-simple.lua
```

**What it does:**
- Bypasses all plugin machinery
- Directly calls `vim.lsp.start()` with venv Python
- Useful for isolating LSP server issues

### `test-direct-start.lua`
Another direct LSP start variant with extended diagnostics.

**Usage:**
```vim
:luafile dev-scripts/test-direct-start.lua
```

**What it does:**
- Checks if Python and server paths exist
- Starts LSP directly with filetypes specified
- Reports client status after 2 seconds

### `test-encoding.lua`
Test encoding/decoding round-trip fidelity.

**Usage:**
```vim
:luafile dev-scripts/test-encoding.lua
```

**What it does:**
- Loads `ignition.encoding` module
- Tests simple newline encoding
- Tests real Ignition script examples
- Inspects current buffer for script values

### `test-install.lua`
Test published package installation from PyPI.

**Usage:**
```bash
nvim -u dev-scripts/test-install.lua
```

**What it does:**
- Sets up isolated lazy.nvim environment
- Installs plugin from GitHub
- Installs `ignition-lsp` from PyPI
- Provides `:IgnitionTestVersions` command to verify versions

**Note:** This is a full Neovim config (`-u` flag), not a `:luafile` script.

### `verify-lint-beta.sh`
Verify ignition-lint-toolkit integration is working correctly.

**Usage:**
```bash
./dev-scripts/verify-lint-beta.sh
```

**What it does:**
- Checks ignition-lint-toolkit installation
- Tests import of JythonValidator
- Runs validation on sample code
- Tests LSP diagnostics integration
- Provides troubleshooting output

**Use when:** Testing the ignition-lint integration or debugging diagnostic issues.

### `start-lsp-manual.sh`
Manually start the LSP server for debugging.

**Usage:**
```bash
./dev-scripts/start-lsp-manual.sh
```

**What it does:**
- Activates the Python venv
- Runs the LSP server directly
- Shows server output in terminal

**Use when:** Debugging LSP server startup issues or viewing raw server logs.

### `test-published.sh`
Automated test of published packages from GitHub + PyPI.

**Usage:**
```bash
./dev-scripts/test-published.sh
```

**What it does:**
- Cleans up previous test installation
- Installs plugin from GitHub
- Installs LSP from PyPI
- Verifies versions
- Tests LSP server executable
- Runs basic LSP initialization test

**Use when:** Verifying packages are correctly published before release.

## Notes

- Most scripts assume you're running from the plugin root directory
- Scripts use dynamic path detection where possible
- Check `/tmp/ignition-lsp.log` for LSP server logs
- Check `~/.local/state/nvim/lsp.log` for Neovim LSP logs
