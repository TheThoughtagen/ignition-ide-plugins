# LSP Upgraded to v1.0.0

The LSP server has been upgraded from local dev (0.1.0) to published PyPI version (1.0.0).

## What Changed
- **Before:** Editable install from local source (`pip install -e .`)
- **After:** Published package from PyPI (`pip install ignition-lsp`)
- **Version:** 1.0.0
- **Data:** Still has all 239 functions + 146 Java classes

## Restart LSP in Neovim

The LSP client in your Neovim is still running the old version. Restart it:

### Option 1: Restart Neovim
```bash
# Close and reopen Neovim
```

### Option 2: Restart LSP Client Only
```vim
:LspRestart ignition_lsp
```

Or manually:
```vim
:lua vim.lsp.stop_client(vim.lsp.get_clients({name = 'ignition_lsp'}))
" Then reopen the file or run :e
```

### Option 3: Quick Restart Script
```vim
:lua for _, client in ipairs(vim.lsp.get_clients({name = 'ignition_lsp'})) do vim.lsp.stop_client(client.id) end
" Then :e to reload buffer
```

## Verify New Version

After restarting, check `:LspInfo` and look for:
```
Version: v1.0.0
```

## Going Back to Dev Mode

If you want to go back to local development (code changes reflected immediately):

```bash
cd lsp
venv/bin/pip uninstall ignition-lsp
venv/bin/pip install -e .
```

Then restart LSP in Neovim.
