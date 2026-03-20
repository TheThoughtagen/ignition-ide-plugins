-- Filetype plugin for Ignition files
-- This file is sourced when a buffer's filetype is set to 'ignition'

-- Only load once per buffer
if vim.b.did_ftplugin then
  return
end
vim.b.did_ftplugin = 1

-- Save user's existing options to restore on filetype change
vim.b.undo_ftplugin = vim.b.undo_ftplugin or ''

local function set_buf_option_with_undo(option, value)
  local current_value = vim.bo[option]
  vim.bo[option] = value
  vim.b.undo_ftplugin = vim.b.undo_ftplugin
    .. string.format('|setlocal %s=%s', option, vim.inspect(current_value))
end

local function set_win_option_with_undo(option, value)
  local current_value = vim.wo[option]
  vim.wo[option] = value
  vim.b.undo_ftplugin = vim.b.undo_ftplugin
    .. string.format('|setlocal %s=%s', option, vim.inspect(current_value))
end

-- Buffer options for JSON editing (Ignition files are JSON with 2-space indent)
set_buf_option_with_undo('expandtab', true)
set_buf_option_with_undo('tabstop', 2)
set_buf_option_with_undo('shiftwidth', 2)
set_buf_option_with_undo('softtabstop', 2)
set_buf_option_with_undo('textwidth', 0)
set_buf_option_with_undo('commentstring', '// %s')

-- Disable wrapping for long JSON lines
set_win_option_with_undo('wrap', false)

-- Format options
set_buf_option_with_undo('formatoptions', 'croql')

-- JSON-aware indentation: indent after { or [, dedent after } or ]
vim.b.undo_ftplugin = vim.b.undo_ftplugin .. '|setlocal indentexpr<'
vim.bo.indentexpr = 'v:lua.require("ignition").json_indent(v:lnum)'

-- Set up buffer-local keymaps
local keymap_opts = { buffer = true, silent = true, noremap = true }

-- Decode/Encode shortcuts
vim.keymap.set('n', '<localleader>id', '<cmd>IgnitionDecode<cr>', vim.tbl_extend('force', keymap_opts, {
  desc = 'Decode Ignition embedded scripts',
}))

vim.keymap.set('n', '<localleader>ie', '<cmd>IgnitionEncode<cr>', vim.tbl_extend('force', keymap_opts, {
  desc = 'Encode Ignition scripts to JSON',
}))

vim.keymap.set('n', '<localleader>ii', '<cmd>IgnitionInfo<cr>', vim.tbl_extend('force', keymap_opts, {
  desc = 'Show Ignition plugin info',
}))

vim.keymap.set('n', '<localleader>il', '<cmd>IgnitionListScripts<cr>', vim.tbl_extend('force', keymap_opts, {
  desc = 'List all scripts in file',
}))

vim.keymap.set('n', '<localleader>ia', '<cmd>IgnitionDecodeAll<cr>', vim.tbl_extend('force', keymap_opts, {
  desc = 'Decode all scripts in file',
}))

vim.keymap.set('n', '<localleader>it', '<cmd>IgnitionComponentTree<cr>', vim.tbl_extend('force', keymap_opts, {
  desc = 'Toggle component tree sidebar',
}))

vim.keymap.set('n', '<localleader>if', '<cmd>IgnitionFormat<cr>', vim.tbl_extend('force', keymap_opts, {
  desc = 'Format JSON indentation',
}))

-- Open with Kindling (for .gwbk files)
if vim.fn.expand('%:e') == 'gwbk' then
  vim.keymap.set('n', '<localleader>ik', '<cmd>IgnitionOpenKindling<cr>', vim.tbl_extend('force', keymap_opts, {
    desc = 'Open in Kindling',
  }))
end

-- Add undo command for keymaps
vim.b.undo_ftplugin = vim.b.undo_ftplugin .. '|mapclear <buffer>'

-- Show decode hints on lines with encoded scripts/expressions
vim.api.nvim_create_autocmd({ 'BufEnter', 'BufWritePost' }, {
  buffer = 0,
  callback = function()
    local ns = vim.api.nvim_create_namespace('ignition_decode_hints')
    vim.api.nvim_buf_clear_namespace(0, ns, 0, -1)
    local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
    for i, line in ipairs(lines) do
      if line:match('"expression"%s*:%s*"') or line:match('"script"%s*:%s*"') or line:match('"eventScript"%s*:%s*"') then
        if line:find('\\n', 1, true) or line:find('\\u00', 1, true) or line:find('\\t', 1, true) then
          vim.api.nvim_buf_set_extmark(0, ns, i - 1, 0, {
            virt_text = { { '  <localleader>id to decode', 'Comment' } },
            virt_text_pos = 'eol',
          })
        end
      end
    end
  end,
})

-- Check if auto-decode is enabled
local ignition_ok, ignition = pcall(require, 'ignition')
if ignition_ok and ignition.config.decoder.auto_decode then
  -- Check if current buffer has encoded scripts
  local decoder = require('ignition.decoder')
  if decoder.has_encoded_scripts() then
    -- Notify user that scripts are detected
    vim.notify(
      'Ignition scripts detected. Use <localleader>id to decode.',
      vim.log.levels.INFO,
      { title = 'Ignition.nvim' }
    )
  end
end

-- Set up LSP if available and enabled
if ignition_ok and ignition.config.lsp.enabled then
  -- LSP will be auto-started by the lsp.lua module
  vim.defer_fn(function()
    -- Check if LSP is attached
    local clients = (vim.lsp.get_clients or vim.lsp.get_active_clients)({ bufnr = 0 })
    local has_ignition_lsp = false
    for _, client in ipairs(clients) do
      if client.name == 'ignition_lsp' then
        has_ignition_lsp = true
        break
      end
    end

    if not has_ignition_lsp and ignition.config.lsp.auto_start then
      -- Try to start LSP
      pcall(vim.cmd, 'LspStart ignition_lsp')
    end
  end, 100)
end
