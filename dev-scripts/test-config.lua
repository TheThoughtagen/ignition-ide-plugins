-- Test configuration for ignition.nvim - Updated for Neovim 0.11.3
-- Run this in Neovim with: :luafile dev-scripts/test-config.lua

print('=== Ignition.nvim Test Configuration ===')

-- Dynamically find plugin root (parent of dev-scripts directory)
local script_path = debug.getinfo(1, 'S').source:sub(2)
local plugin_root = vim.fn.fnamemodify(script_path, ':h:h')

-- Clear any cached modules
package.loaded['ignition'] = nil
package.loaded['ignition.lsp'] = nil
package.loaded['ignition.config'] = nil
package.loaded['ignition.decoder'] = nil
package.loaded['ignition.kindling'] = nil

-- Add plugin to runtimepath
vim.opt.runtimepath:append(plugin_root)

-- Source the plugin
vim.cmd('source ' .. plugin_root .. '/plugin/ignition.lua')

-- Setup ignition
local ok, ignition = pcall(require, 'ignition')
if not ok then
  print('ERROR: Could not load ignition module')
  print(ignition)
  return
end

print('✓ Loaded ignition module (fresh)')

-- Setup with config
ignition.setup({
  lsp = {
    enabled = true,
    auto_start = false, -- We'll start manually for testing
    settings = {
      ignition = {
        version = "8.1",
      },
    },
  },
})

print('✓ Ignition setup complete')
print('LSP command:', vim.inspect(ignition.config.lsp.cmd))

-- Manually start LSP for current buffer
local lsp_module = require('ignition.lsp')
print('✓ Loaded LSP module')

local client_id = lsp_module.start_lsp_for_buffer(0)

if client_id then
  print('✓ LSP started with client ID:', client_id)

  vim.defer_fn(function()
    print('\n=== LSP Status After 2 Seconds ===')
    local clients = vim.lsp.get_clients({ bufnr = 0 })
    print('Active clients on this buffer:')
    for _, client in ipairs(clients) do
      print('  -', client.name, '(id:', client.id .. ')')
    end
    print('\nNow run :LspInfo to see full details')
  end, 2000)
else
  print('✗ Failed to start LSP')
  print('Check the logs:')
  print('  - Server log: /tmp/ignition-lsp.log')
  print('  - Neovim log: ~/.local/state/nvim/lsp.log')
end
