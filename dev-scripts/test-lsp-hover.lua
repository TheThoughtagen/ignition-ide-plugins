#!/usr/bin/env lua
-- Test script to diagnose LSP hover issues
-- Run with: nvim --headless -u dev-scripts/test-lsp-hover.lua

-- Helper to print diagnostics
local function log(msg)
  print("[LSP-HOVER-TEST] " .. msg)
end

-- 1. Check if LSP server is installed
log("Checking LSP server installation...")
local plugin_root = vim.fn.getcwd()
local venv_cmd = plugin_root .. '/lsp/venv/bin/ignition-lsp'
local venv_python = plugin_root .. '/lsp/venv/bin/python'
local server_py = plugin_root .. '/lsp/ignition_lsp/server.py'

if vim.fn.executable(venv_cmd) == 1 then
  log("✓ LSP server found: " .. venv_cmd)
elseif vim.fn.executable(venv_python) == 1 and vim.fn.filereadable(server_py) == 1 then
  log("✓ Dev LSP server found: " .. venv_python .. " " .. server_py)
else
  log("✗ LSP server NOT found!")
  log("  Run: cd lsp && python -m venv venv && source venv/bin/activate && pip install -e .")
  vim.cmd('qa!')
end

-- 2. Check which buffers have LSP attached
log("\nChecking LSP client status...")

vim.cmd('edit tests/fixtures/sample_project/ignition/script-python/example.py')

-- Wait a bit for LSP to attach
vim.wait(2000, function()
  local clients = vim.lsp.get_clients({ bufnr = 0 })
  return #clients > 0
end)

local clients = vim.lsp.get_clients({ bufnr = 0 })
if #clients == 0 then
  log("✗ No LSP clients attached to buffer")
  log("  Trying manual attach...")

  -- Try to manually start LSP
  require('ignition').setup()
  vim.wait(2000, function()
    local c = vim.lsp.get_clients({ bufnr = 0 })
    return #c > 0
  end)

  clients = vim.lsp.get_clients({ bufnr = 0 })
  if #clients == 0 then
    log("✗ Manual attach failed")
    vim.cmd('qa!')
  end
end

log("✓ LSP clients attached:")
for _, client in ipairs(clients) do
  log("  - " .. client.name .. " (id=" .. client.id .. ")")
  log("    root_dir: " .. (client.config.root_dir or "none"))
  log("    capabilities.hoverProvider: " .. tostring(client.server_capabilities.hoverProvider))
end

-- 3. Test hover on a known function
log("\nTesting hover on 'system.tag.readBlocking'...")

-- Insert test content
vim.api.nvim_buf_set_lines(0, 0, -1, false, {
  "# Test hover on SDK functions",
  "result = system.tag.readBlocking(['path1', 'path2'])",
  "",
  "# Test hover on Java classes",
  "from java.util import ArrayList",
  "list = ArrayList()",
  "list.add('test')",
})

-- Position cursor on "readBlocking"
vim.api.nvim_win_set_cursor(0, {2, 20})  -- line 2, col 20 (on "readBlocking")

-- Request hover
local hover_done = false
local params = vim.lsp.util.make_position_params()
vim.lsp.buf_request(0, 'textDocument/hover', params, function(err, result, ctx, config)
  if err then
    log("✗ Hover error: " .. vim.inspect(err))
  elseif result then
    log("✓ Hover result received:")
    if result.contents then
      if type(result.contents) == 'string' then
        log(result.contents)
      elseif result.contents.value then
        log(result.contents.value)
      else
        log(vim.inspect(result.contents))
      end
    end
  else
    log("✗ Hover returned nil")
  end
  hover_done = true
end)

-- Wait for hover response
vim.wait(3000, function()
  return hover_done
end)

if not hover_done then
  log("✗ Hover timed out after 3s")
end

-- 4. Test hover on Java class
log("\nTesting hover on 'ArrayList'...")
vim.api.nvim_win_set_cursor(0, {5, 20})  -- line 5, col 20 (on "ArrayList")

hover_result = nil
params = vim.lsp.util.make_position_params()
vim.lsp.buf_request(0, 'textDocument/hover', params, function(err, result, ctx, config)
  if err then
    log("✗ Hover error: " .. vim.inspect(err))
  elseif result then
    log("✓ Hover result received:")
    if result.contents and result.contents.value then
      log(result.contents.value)
    else
      log(vim.inspect(result.contents))
    end
  else
    log("✗ Hover returned nil")
  end
  hover_result = result
end)

vim.wait(3000, function()
  return hover_result ~= nil
end)

if not hover_result then
  log("✗ Hover timed out after 3s")
end

log("\nTest complete. Check /tmp/ignition-lsp.log for server logs.")
vim.cmd('qa!')
