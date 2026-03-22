-- ignition.nvim - Core module
local M = {}

-- Default configuration
M.config = {
  -- LSP server settings
  lsp = {
    enabled = true,
    auto_start = true,
    cmd = nil, -- Will be auto-detected
    settings = {
      ignition = {
        version = "8.1", -- Default Ignition version
        sdk_path = nil,
      },
    },
  },

  -- Kindling integration settings
  kindling = {
    enabled = true,
    path = nil, -- Will be auto-detected
  },

  -- Script decoder settings
  decoder = {
    auto_decode = true,
    auto_encode = true,
    create_scratch_buffer = true,
  },

  -- UI settings
  ui = {
    show_notifications = true,
    show_statusline = true,
  },
}

-- Setup function called by users
function M.setup(opts)
  M.config = vim.tbl_deep_extend('force', M.config, opts or {})

  -- Initialize LSP if enabled
  if M.config.lsp.enabled then
    require('ignition.lsp').setup(M.config.lsp)
  end

  -- Detect Kindling installation
  if M.config.kindling.enabled then
    require('ignition.kindling').detect_installation()
  end
end

-- Show plugin information
function M.info()
  local lines = {
    'Ignition.nvim - Ignition Development Support',
    '',
    'Configuration:',
    '  LSP Enabled: ' .. tostring(M.config.lsp.enabled),
    '  Auto Decode: ' .. tostring(M.config.decoder.auto_decode),
    '  Kindling: ' .. tostring(M.config.kindling.enabled),
    '',
    'Version: 0.1.0',
  }

  vim.notify(table.concat(lines, '\n'), vim.log.levels.INFO, { title = 'Ignition.nvim' })
end

--- JSON-aware indentation for ignition buffers.
--- Called via indentexpr to compute indent for a given line.
---@param lnum number 1-indexed line number
---@return number indent in spaces
function M.json_indent(lnum)
  if lnum <= 1 then
    return 0
  end

  local sw = vim.bo.shiftwidth

  -- Find the previous non-blank line
  local prev_lnum = vim.fn.prevnonblank(lnum - 1)
  if prev_lnum == 0 then
    return 0
  end

  local prev_line = vim.fn.getline(prev_lnum)
  local prev_indent = vim.fn.indent(prev_lnum)

  -- Check if previous line ends with { or [ (opening bracket)
  local trimmed = prev_line:match('^%s*(.-)%s*$')
  local opens = trimmed:match('[%[{]%s*$')

  -- Check if current line starts with } or ] (closing bracket)
  local cur_line = vim.fn.getline(lnum)
  local closes = cur_line:match('^%s*[%]}]')

  if opens and closes then
    -- Previous opens, current closes → same indent as previous
    return prev_indent
  elseif opens then
    -- Previous opens → indent one level
    return prev_indent + sw
  elseif closes then
    -- Current closes → dedent one level
    return math.max(0, prev_indent - sw)
  else
    -- Maintain previous indent
    return prev_indent
  end
end

return M
