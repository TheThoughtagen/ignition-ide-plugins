-- Complete plugin loader for testing
-- Run: :luafile dev-scripts/load-plugin.lua

print('=== Loading ignition.nvim ===')

-- Dynamically find plugin root (parent of dev-scripts directory)
local script_path = debug.getinfo(1, 'S').source:sub(2)
local plugin_root = vim.fn.fnamemodify(script_path, ':h:h')

-- Add to runtime path
vim.opt.runtimepath:prepend(plugin_root)

-- Add to Lua package path
package.path = package.path .. ';' .. plugin_root .. '/lua/?.lua'
package.path = package.path .. ';' .. plugin_root .. '/lua/?/init.lua'

print('✓ Runtime and package paths configured')

-- Clear any cached modules
for k, _ in pairs(package.loaded) do
  if k:match('^ignition') then
    package.loaded[k] = nil
  end
end

print('✓ Cleared cached modules')

-- Source the plugin commands
vim.cmd('source ' .. plugin_root .. '/plugin/ignition.lua')

print('✓ Sourced plugin commands')

-- Setup ignition
local ok, ignition = pcall(require, 'ignition')
if not ok then
  print('✗ Failed to load ignition:', ignition)
  return
end

print('✓ Loaded ignition module')

ignition.setup({
  lsp = {
    enabled = true,
    auto_start = true,
  },
})

print('✓ Ignition setup complete')
print('')
print('Available commands:')
print('  :IgnitionDecode')
print('  :IgnitionDecodeAll')
print('  :IgnitionListScripts')
print('  :IgnitionEncode')
print('  :IgnitionInfo')
print('')
print('Ready to test!')
