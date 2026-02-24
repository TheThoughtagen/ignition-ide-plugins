-- LSP diagnostic script
-- Run: :luafile dev-scripts/diagnose-lsp.lua
-- Or from shell: nvim -u dev-scripts/diagnose-lsp.lua /path/to/ignition/project/resource.json

print('=== Ignition LSP Diagnostics ===\n')

-- 1. Check Neovim version
print('1. Neovim Version')
print('   ' .. vim.fn.execute('version'):match('NVIM v[0-9.]+'))
local has_011 = vim.fn.has('nvim-0.11') == 1
print('   Neovim 0.11+: ' .. (has_011 and '✓ Yes' or '✗ No (REQUIRED)'))
print()

-- 2. Check if plugin is loaded
print('2. Plugin Status')
local ok, ignition = pcall(require, 'ignition')
if ok then
  print('   ✓ Plugin loaded')
  print('   Config: ' .. vim.inspect(ignition.config, { depth = 2 }))
else
  print('   ✗ Plugin not loaded')
  print('   Error: ' .. ignition)
  print('\n   Load plugin first:')
  print('   :luafile dev-scripts/load-plugin.lua')
  return
end
print()

-- 3. Check LSP server availability
print('3. LSP Server')
local lsp_module = require('ignition.lsp')
local cmd = lsp_module.find_lsp_server()
if cmd then
  print('   ✓ Server found: ' .. table.concat(cmd, ' '))
else
  print('   ✗ Server not found')
  print('   Run: cd lsp && python3 -m venv venv && venv/bin/pip install -e .')
  return
end
print()

-- 4. Check current buffer
print('4. Current Buffer')
local bufnr = vim.api.nvim_get_current_buf()
local bufname = vim.api.nvim_buf_get_name(bufnr)
local ft = vim.bo[bufnr].filetype

print('   File: ' .. (bufname ~= '' and bufname or '(no file)'))
print('   Filetype: ' .. (ft ~= '' and ft or '(empty)'))
print('   Expected: ignition or python')
print()

-- 5. Check for project.json (root marker)
print('5. Ignition Project Root')
local cwd = vim.fn.getcwd()
local root = vim.fs.root(bufnr, 'project.json')
print('   CWD: ' .. cwd)
if root then
  print('   ✓ Found project.json at: ' .. root)
else
  print('   ✗ No project.json found (LSP won\'t start without it)')
  print('   Navigate to an Ignition project directory first')
end
print()

-- 6. Check active LSP clients
print('6. Active LSP Clients')
local clients = vim.lsp.get_clients({ bufnr = bufnr })
if #clients > 0 then
  print('   ✓ ' .. #clients .. ' client(s) attached:')
  for _, client in ipairs(clients) do
    print('      - ' .. client.name .. ' (id: ' .. client.id .. ')')
  end
else
  print('   ✗ No LSP clients attached')

  if ft == 'ignition' or ft == 'python' then
    if root then
      print('\n   Attempting to start LSP...')
      local success, result = pcall(function()
        local config = vim.lsp.config.ignition_lsp
        if config then
          return vim.lsp.start(config, { bufnr = bufnr })
        end
      end)

      if success and result then
        print('   ✓ LSP started! Client ID: ' .. result)

        vim.defer_fn(function()
          print('\n   Waiting 2 seconds...')
          local new_clients = vim.lsp.get_clients({ bufnr = bufnr })
          if #new_clients > 0 then
            print('   ✓ LSP is now active')
            print('\n   Try completions: Type "system." or "project."')
          else
            print('   ✗ LSP failed to stay active')
            print('   Check logs: tail -f /tmp/ignition-lsp.log')
          end
        end, 2000)
      else
        print('   ✗ Failed to start: ' .. tostring(result))
      end
    else
      print('   Reason: No project.json found')
    end
  else
    print('   Reason: Wrong filetype (need ignition or python)')
  end
end
print()

-- 7. Quick test
print('7. Quick Fix')
print('   If LSP isn\'t working:')
print('   1. Navigate to an Ignition project directory (cd /path/to/project)')
print('   2. Open a resource.json or .py file')
print('   3. Check :LspInfo')
print('   4. Type "system." and wait for completions')
print()
print('   Logs:')
print('   - LSP server: /tmp/ignition-lsp.log')
print('   - Neovim LSP: ~/.local/state/nvim/lsp.log')
print()
