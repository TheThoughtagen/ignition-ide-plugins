-- Test LSP attachment to virtual buffers
-- Run: :luafile dev-scripts/test-virtual-lsp.lua
-- Then use :IgnitionDecode on a JSON file with scripts

print('=== Testing Virtual Buffer LSP Attachment ===\n')

-- 1. Reload plugin modules
print('1. Reloading plugin modules...')
package.loaded['ignition'] = nil
package.loaded['ignition.lsp'] = nil
package.loaded['ignition.virtual_doc'] = nil
package.loaded['ignition.decoder'] = nil

-- Dynamically find plugin root
local script_path = debug.getinfo(1, 'S').source:sub(2)
local plugin_root = vim.fn.fnamemodify(script_path, ':h:h')

-- Add to runtime path
vim.opt.runtimepath:prepend(plugin_root)

-- Source the plugin
vim.cmd('source ' .. plugin_root .. '/plugin/ignition.lua')

local ok, ignition = pcall(require, 'ignition')
if not ok then
  print('✗ Failed to load plugin')
  return
end

print('✓ Plugin reloaded')
print()

-- 2. Setup with LSP enabled
print('2. Setting up plugin with LSP...')
ignition.setup({
  lsp = {
    enabled = true,
    auto_start = true,
  },
})
print('✓ Plugin configured')
print()

-- 3. Instructions
print('3. Test Instructions:')
print('   a. Open an Ignition JSON file with scripts (e.g., resource.json)')
print('   b. Run :IgnitionDecode')
print('   c. In the virtual buffer, run :LspInfo')
print('   d. Type "system." and check for completions')
print()
print('Expected:')
print('   - :LspInfo should show "ignition_lsp" attached')
print('   - "system." should trigger completions')
print()

-- 4. Add a helper command to check current buffer
vim.api.nvim_create_user_command('CheckLSP', function()
  local bufnr = vim.api.nvim_get_current_buf()
  local clients = vim.lsp.get_clients({ bufnr = bufnr })

  print('\n=== Current Buffer LSP Status ===')
  print('Buffer:', bufnr)
  print('Name:', vim.api.nvim_buf_get_name(bufnr))
  print('Filetype:', vim.bo[bufnr].filetype)
  print('Buftype:', vim.bo[bufnr].buftype)

  if #clients > 0 then
    print('\n✓ LSP clients attached:')
    for _, client in ipairs(clients) do
      print('  -', client.name, '(id:', client.id .. ')')
    end
  else
    print('\n✗ No LSP clients attached')
    print('Attempting to start LSP...')
    local lsp = require('ignition.lsp')
    local client_id = lsp.start_lsp_for_buffer(bufnr)
    if client_id then
      print('✓ Started LSP, client ID:', client_id)
    else
      print('✗ Failed to start LSP')
    end
  end
  print()
end, {})

print('Helper command added: :CheckLSP')
print('Run this in any buffer to check LSP status')
print()
