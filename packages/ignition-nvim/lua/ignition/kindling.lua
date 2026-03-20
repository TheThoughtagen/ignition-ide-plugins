-- Kindling integration for .gwbk files
local M = {}

local kindling_path = nil

-- Known installation URLs for install instructions
local KINDLING_REPO = 'https://github.com/paul-griffith/kindling'

-- Detect Kindling installation
function M.detect_installation()
  local config = require('ignition').config.kindling

  if config.path and vim.fn.executable(config.path) == 1 then
    kindling_path = config.path
    return true
  end

  -- Try common installation paths (macOS + Linux)
  local possible_paths = {
    -- macOS
    '/usr/local/bin/kindling',
    '/opt/homebrew/bin/kindling',
    vim.fn.expand('~/Applications/Kindling.app/Contents/MacOS/kindling'),
    -- Linux
    '/usr/bin/kindling',
    '/usr/local/bin/kindling',
    vim.fn.expand('~/.local/bin/kindling'),
    -- Snap / Flatpak
    '/snap/bin/kindling',
    vim.fn.expand('~/.local/share/flatpak/exports/bin/kindling'),
    -- PATH lookup (last resort — may be slow)
    vim.fn.exepath('kindling'),
  }

  for _, path in ipairs(possible_paths) do
    if path ~= '' and vim.fn.executable(path) == 1 then
      kindling_path = path
      return true
    end
  end

  return false
end

-- Get the cached kindling path (for testing/inspection)
function M.get_path()
  return kindling_path
end

-- Reset cached state (for testing)
function M.reset()
  kindling_path = nil
end

-- Show install instructions when Kindling is not found
function M.show_install_instructions()
  local lines = {
    'Kindling is not installed.',
    '',
    'Kindling is a utility for working with Ignition .gwbk gateway backup files.',
    '',
    'Install from: ' .. KINDLING_REPO,
    '',
    'Or configure a custom path in your setup:',
    '  require("ignition").setup({',
    '    kindling = { path = "/path/to/kindling" }',
    '  })',
  }
  vim.notify(table.concat(lines, '\n'), vim.log.levels.WARN, { title = 'Ignition.nvim' })
end

-- Open file with Kindling
function M.open_with_kindling(file_path)
  if not kindling_path then
    if not M.detect_installation() then
      M.show_install_instructions()
      return
    end
  end

  local file = file_path and file_path ~= '' and vim.fn.expand(file_path) or vim.fn.expand('%:p')

  if vim.fn.filereadable(file) ~= 1 then
    vim.notify('File not found: ' .. file, vim.log.levels.ERROR, { title = 'Ignition.nvim' })
    return
  end

  -- Open Kindling with the file
  vim.fn.jobstart({ kindling_path, file }, {
    detach = true,
    on_exit = function(_, exit_code)
      if exit_code ~= 0 then
        vim.notify(
          'Kindling exited with code ' .. exit_code,
          vim.log.levels.WARN,
          { title = 'Ignition.nvim' }
        )
      end
    end,
  })

  vim.notify('Opening in Kindling: ' .. vim.fn.fnamemodify(file, ':t'), vim.log.levels.INFO, {
    title = 'Ignition.nvim',
  })
end

return M
