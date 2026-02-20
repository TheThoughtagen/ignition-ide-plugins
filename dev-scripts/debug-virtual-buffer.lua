-- Debug virtual buffer LSP attachment
-- Run after creating a virtual buffer with :IgnitionDecode
-- Usage: :luafile dev-scripts/debug-virtual-buffer.lua

local bufnr = vim.api.nvim_get_current_buf()

print('=== Virtual Buffer Debug ===\n')

print('Buffer Info:')
print('  bufnr:', bufnr)
print('  name:', vim.api.nvim_buf_get_name(bufnr))
print('  filetype:', vim.bo[bufnr].filetype)
print('  buftype:', vim.bo[bufnr].buftype)
print()

-- Check if it's a virtual doc
local virtual_doc = require('ignition.virtual_doc')
local is_virtual = virtual_doc.is_virtual_doc(bufnr)
print('Virtual Doc:', is_virtual)
if is_virtual then
  local metadata = virtual_doc.get_metadata(bufnr)
  print('  Source file:', metadata.source_file)
  print('  Script key:', metadata.script_key)
  print('  Line:', metadata.line_num)
end
print()

-- Check LSP config
local config = vim.lsp.config.ignition_lsp
if config then
  print('LSP Config:')
  print('  cmd:', vim.inspect(config.cmd))
  print('  root_markers:', vim.inspect(config.root_markers))
  print('  filetypes:', vim.inspect(config.filetypes))
else
  print('✗ No LSP config found')
end
print()

-- Check for root
local root = vim.fs.root(bufnr, 'project.json')
print('Root Detection:')
print('  project.json root:', root or '(not found)')
print()

-- Check attached clients
local clients = vim.lsp.get_clients({ bufnr = bufnr })
print('Attached Clients:', #clients)
for _, client in ipairs(clients) do
  print('  -', client.name, '(id:', client.id .. ')')
  print('    root_dir:', client.config.root_dir)
end
print()

-- Try manual start
print('Attempting manual LSP start...')
local lsp = require('ignition.lsp')
local client_id = lsp.start_lsp_for_buffer(bufnr)
if client_id then
  print('✓ LSP started, client ID:', client_id)

  vim.defer_fn(function()
    local new_clients = vim.lsp.get_clients({ bufnr = bufnr })
    print('\nAfter 2 seconds:')
    if #new_clients > 0 then
      print('✓ LSP is active')
      for _, client in ipairs(new_clients) do
        print('  -', client.name)
      end
    else
      print('✗ LSP failed to stay active')
      print('\nCheck logs:')
      print('  tail -f /tmp/ignition-lsp.log')
    end
  end, 2000)
else
  print('✗ Failed to start LSP')
  print('\nPossible reasons:')
  print('  1. No project.json found (LSP requires Ignition project)')
  print('  2. LSP command not found')
  print('  3. Wrong filetype')
end
print()
