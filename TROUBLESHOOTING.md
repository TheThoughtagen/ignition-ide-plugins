# Troubleshooting Guide

This guide covers common issues and their solutions when using ignition-nvim.

## Common Issues

### LSP Server Not Starting

**Symptoms:**
- No completions or hover documentation
- `:LspInfo` shows no attached clients

**Diagnosis:**

Check if the LSP server is installed:
```bash
pip list | grep ignition-lsp
```

**Solutions:**

1. **Manual installation:**
   ```bash
   cd lsp
   pip install -e .
   ```

2. **Verify the LSP command:**
   ```vim
   :lua print(vim.inspect(require('ignition').config.lsp.cmd))
   ```

3. **Check LSP logs:**
   ```vim
   :LspLog
   ```

### LSP Not Attaching to Buffer

**Symptoms:**
- LSP server installed but not attaching to Ignition files

**Diagnosis:**

Check LSP attachment status:
```vim
:LspInfo
```

**Solutions:**

1. **Manually start the LSP client:**
   ```vim
   :LspStart
   ```

2. **Verify filetype detection:**
   ```vim
   :set filetype?
   ```
   Should show `filetype=python` or `filetype=ignition`

3. **Check auto_start configuration:**
   ```vim
   :lua print(vim.inspect(require('ignition').config.lsp))
   ```

### "system is not defined" Diagnostics

**Issue:** Other Python LSP clients (Pyright, Pylance, basedpyright) are reporting that `system`, `shared`, or other Ignition built-ins are undefined.

**Root Cause:** Multiple Python LSP clients are attached to the same buffer. The ignition-lsp server understands Ignition's built-ins, but standard Python LSPs don't.

**Diagnosis:**

Check which LSP clients are attached:
```vim
:LspInfo
```

Check diagnostic sources:
```vim
:lua vim.print(vim.diagnostic.get(0))
```

Look for the `source` field on each diagnostic. Expected from ignition-lint:
- `source: "ignition-lint"`
- codes: `JYTHON_*` (like `JYTHON_HARDCODED_LOCALHOST`)

If you see:
- `source: "Pylance"` or `"Pyright"` or `"pyls"` → Another Python LSP is running
- No source field → Coming from Neovim's built-in diagnostics or another plugin

**Solution A - Disable other Python LSPs for Ignition files:**

Add to your Neovim config:
```lua
vim.api.nvim_create_autocmd("FileType", {
  pattern = {"python", "ignition"},
  callback = function()
    -- Only use ignition_lsp for Ignition-related files
    local bufname = vim.api.nvim_buf_get_name(0)
    if bufname:match("Ignition") or vim.bo.filetype == "ignition" then
      -- Stop other Python LSPs
      for _, client in ipairs(vim.lsp.get_active_clients({bufnr = 0})) do
        if client.name ~= "ignition_lsp" and client.name:match("[Pp]y") then
          vim.lsp.stop_client(client.id)
        end
      end
    end
  end,
})
```

**Solution B - Filter diagnostics by source:**

In your Neovim config:
```lua
-- Only show diagnostics from ignition-lint for Ignition files
vim.diagnostic.config({
  virtual_text = {
    source = "if_many",  -- Only show source if multiple
    format = function(diagnostic)
      -- Filter out "not defined" errors for Ignition built-ins
      if diagnostic.message:match("'system' is not defined") or
         diagnostic.message:match("'shared' is not defined") or
         diagnostic.message:match("'self' is not defined") then
        return nil  -- Don't show this diagnostic
      end
      return diagnostic.message
    end,
  },
})
```

### Hover Not Working

**Symptoms:**
- Pressing `K` doesn't show documentation
- No hover popup appears

**Diagnosis:**

Test hover manually:
```vim
:lua vim.lsp.buf.hover()
```

Watch server logs for hover requests:
```bash
tail -f /tmp/ignition-lsp.log
```

Then in Neovim, press `K` (or your hover key) over some code.

**Expected:**
- "Hover requested at..." appears in the log
- Hover popup shows function documentation

**Solutions:**

1. **Verify LSP client is attached:**
   ```vim
   :LspInfo
   ```

2. **Check hover keybinding:**
   The default LSP hover is usually `K` in normal mode. If you've customized your LSP keybindings, verify they're set correctly.

3. **Check for hover capability:**
   ```vim
   :lua vim.print(vim.lsp.get_active_clients()[1].server_capabilities)
   ```
   Look for `hoverProvider = true`

### Virtual Buffers Not Saving

**Symptoms:**
- Saving a virtual buffer doesn't update the source JSON file
- Changes are lost when closing the virtual buffer

**Diagnosis:**

Check if `BufWriteCmd` autocmd is set:
```vim
:autocmd BufWriteCmd
```

Should show an autocmd for the virtual buffer.

**Solutions:**

1. **Verify virtual buffer setup:**
   Check that `virtual_doc.lua` is loaded:
   ```vim
   :lua print(vim.inspect(require('ignition.virtual_doc')))
   ```

2. **Check source JSON file path:**
   The virtual buffer stores metadata about its source. Ensure the source file still exists and is writable.

3. **Manual encode:**
   If auto-save fails, try manually encoding:
   ```vim
   :IgnitionEncode
   ```

4. **Check buffer type:**
   ```vim
   :set buftype?
   ```
   Should show `buftype=acwrite` for virtual buffers.

### Encoding/Decoding Errors

**Symptoms:**
- Round-trip encode/decode doesn't match original
- Special characters corrupted
- Scripts fail to load in Ignition

**Diagnosis:**

The encoding uses Ignition Flint format (NOT base64). Check for:
- Backslash escaping issues
- Unicode escape sequences (`\u003c`, `\u003e`, etc.)
- JSON string escape sequences (`\"`, `\n`, `\t`, etc.)

**Solutions:**

1. **Verify encoding order:**
   Encoding must happen in specific order (backslash first to avoid double-escaping). This is handled by `encoding.lua`.

2. **Check for Lua pattern issues:**
   The encoder uses `string.gsub` with plain flag, NOT Lua patterns. If you see pattern-related errors, check `encoding.lua`.

3. **Test round-trip fidelity:**
   ```lua
   local encoding = require('ignition.encoding')
   local original = "test script"
   local encoded = encoding.encode(original)
   local decoded = encoding.decode(encoded)
   assert(decoded == original)
   ```

4. **Review encoding.lua:**
   If encoding issues persist, the problem may be in the core encoding logic. This is a critical area - consult CLAUDE.md before modifying.

## Debug Commands

Quick reference for diagnostic commands:

| Command | Purpose |
|---------|---------|
| `:LspInfo` | Check LSP client status and attachment |
| `:LspLog` | View LSP client logs |
| `:lua vim.print(vim.diagnostic.get(0))` | Inspect all diagnostics with sources |
| `:lua print(vim.inspect(require('ignition').config))` | Show current plugin configuration |
| `tail -f /tmp/ignition-lsp.log` | Watch LSP server logs in real-time |
| `:set filetype?` | Check current buffer filetype |
| `:autocmd BufWriteCmd` | Check virtual buffer autocmds |

## Getting Help

If you've tried the solutions above and still have issues:

1. **Check this troubleshooting guide** for your specific issue
2. **Search GitHub issues**: https://github.com/TheThoughtagen/ignition-ide-plugins/issues
3. **Enable debug logging** and gather diagnostic info:
   - Run `:LspInfo` and `:LspLog`
   - Check `/tmp/ignition-lsp.log`
   - Note your Neovim version (`:version`)
   - Note your Python version (`python --version`)
4. **Open a new issue** with:
   - Clear description of the problem
   - Steps to reproduce
   - Logs from above commands
   - Minimal configuration that reproduces the issue

See [CONTRIBUTING.md](CONTRIBUTING.md) for more information on reporting issues.
