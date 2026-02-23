-- Script decoder/encoder for Ignition embedded Python scripts
local M = {}

local encoding = require('ignition.encoding')
local json_parser = require('ignition.json_parser')
local virtual_doc = require('ignition.virtual_doc')

-- Decode embedded scripts in current buffer
function M.decode_current_buffer()
  local bufnr = vim.api.nvim_get_current_buf()

  -- Check if this is a virtual document already
  if virtual_doc.is_virtual_doc(bufnr) then
    vim.notify('This is already a decoded script', vim.log.levels.WARN, { title = 'Ignition.nvim' })
    return
  end

  -- Find all scripts in the buffer
  local scripts = json_parser.find_scripts(bufnr)

  if #scripts == 0 then
    vim.notify('No Ignition scripts found in this file', vim.log.levels.WARN, {
      title = 'Ignition.nvim',
    })
    return
  end

  -- If only one script, decode it directly
  if #scripts == 1 then
    M.decode_script(bufnr, scripts[1])
    return
  end

  -- Multiple scripts - show selection menu
  local items = {}
  for i, script in ipairs(scripts) do
    local context = json_parser.get_script_context(script)
    local preview = encoding.decode_script(script.content):sub(1, 50)
    if #preview == 50 then
      preview = preview .. '...'
    end
    table.insert(items, string.format('[%d] %s (line %d): %s', i, context, script.line, preview))
  end

  vim.ui.select(items, {
    prompt = 'Select script to decode:',
  }, function(_, idx)
    if idx then
      M.decode_script(bufnr, scripts[idx])
    end
  end)
end

-- Decode a specific script
function M.decode_script(source_bufnr, script_info)
  -- Decode the script content
  local decoded = encoding.decode_script(script_info.content)

  -- Create or get existing virtual document
  local virtual_bufnr = virtual_doc.create_virtual_doc(source_bufnr, script_info)

  -- Check if buffer already existed (has content)
  local existing_lines = vim.api.nvim_buf_get_lines(virtual_bufnr, 0, -1, false)
  local is_existing = #existing_lines > 0 and existing_lines[1] ~= ''

  if is_existing then
    -- Buffer already exists - just focus it
    -- Find if it's already open in a window
    local wins = vim.fn.win_findbuf(virtual_bufnr)
    if #wins > 0 then
      vim.api.nvim_set_current_win(wins[1])
    else
      vim.cmd('split')
      vim.api.nvim_win_set_buf(0, virtual_bufnr)
    end

    local context = json_parser.get_script_context(script_info)
    vim.notify(
      string.format('Focused existing decoded %s', context),
      vim.log.levels.INFO,
      { title = 'Ignition.nvim' }
    )
  else
    -- New buffer - set content
    local decoded_lines = vim.split(decoded, '\n', { plain = true })

    -- Set the content in the virtual buffer
    vim.api.nvim_buf_set_lines(virtual_bufnr, 0, -1, false, decoded_lines)

    -- Mark as unmodified
    vim.api.nvim_buf_set_option(virtual_bufnr, 'modified', false)

    -- Open the virtual buffer in a new split
    vim.cmd('split')
    vim.api.nvim_win_set_buf(0, virtual_bufnr)

    local context = json_parser.get_script_context(script_info)
    vim.notify(
      string.format('Decoded %s from line %d (%d lines)', context, script_info.line, #decoded_lines),
      vim.log.levels.INFO,
      { title = 'Ignition.nvim' }
    )

  end
end

-- Decode all scripts in current buffer
function M.decode_all_scripts()
  local bufnr = vim.api.nvim_get_current_buf()

  -- Find all scripts
  local scripts = json_parser.find_scripts(bufnr)

  if #scripts == 0 then
    vim.notify('No Ignition scripts found in this file', vim.log.levels.WARN, {
      title = 'Ignition.nvim',
    })
    return
  end

  -- Decode each script, returning to source window between each
  local source_win = vim.api.nvim_get_current_win()
  for _, script in ipairs(scripts) do
    M.decode_script(bufnr, script)
    vim.api.nvim_set_current_win(source_win)
  end

  vim.notify(
    string.format('Decoded %d script(s)', #scripts),
    vim.log.levels.INFO,
    { title = 'Ignition.nvim' }
  )
end

-- Encode scripts back to JSON format
function M.encode_current_buffer()
  local bufnr = vim.api.nvim_get_current_buf()

  -- Check if this is a virtual document
  if not virtual_doc.is_virtual_doc(bufnr) then
    vim.notify(
      'This is not a decoded script buffer. Use :IgnitionDecode first.',
      vim.log.levels.WARN,
      { title = 'Ignition.nvim' }
    )
    return
  end

  -- Save the virtual document (this will encode and update source)
  virtual_doc.save_virtual_doc(bufnr)
end

-- List all scripts in current buffer
function M.list_scripts()
  local bufnr = vim.api.nvim_get_current_buf()

  -- Find all scripts
  local scripts = json_parser.find_scripts(bufnr)

  if #scripts == 0 then
    vim.notify('No Ignition scripts found in this file', vim.log.levels.WARN, {
      title = 'Ignition.nvim',
    })
    return
  end

  -- Build display lines
  local lines = { 'Ignition Scripts in ' .. vim.fn.expand('%:t'), '' }

  for i, script in ipairs(scripts) do
    local context = json_parser.get_script_context(script)
    local decoded = encoding.decode_script(script.content)
    local line_count = #vim.split(decoded, '\n', { plain = true })

    table.insert(
      lines,
      string.format('[%d] %s at line %d (%d lines)', i, context, script.line, line_count)
    )
  end

  -- Show in a floating window
  local float_bufnr = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(float_bufnr, 0, -1, false, lines)
  vim.api.nvim_buf_set_option(float_bufnr, 'modifiable', false)
  vim.api.nvim_buf_set_option(float_bufnr, 'buftype', 'nofile')

  local width = 60
  local height = #lines + 2

  local win_id = vim.api.nvim_open_win(float_bufnr, true, {
    relative = 'cursor',
    width = width,
    height = height,
    row = 1,
    col = 0,
    style = 'minimal',
    border = 'rounded',
  })

  -- Close on <Esc> or q
  vim.api.nvim_buf_set_keymap(
    float_bufnr,
    'n',
    '<Esc>',
    '<cmd>close<cr>',
    { silent = true, noremap = true }
  )
  vim.api.nvim_buf_set_keymap(
    float_bufnr,
    'n',
    'q',
    '<cmd>close<cr>',
    { silent = true, noremap = true }
  )
end

-- Check if buffer contains encoded scripts
function M.has_encoded_scripts(bufnr)
  bufnr = bufnr or vim.api.nvim_get_current_buf()
  return json_parser.has_scripts(bufnr)
end

-- Get script statistics for current buffer
function M.get_script_stats(bufnr)
  return json_parser.get_script_stats(bufnr)
end

return M
