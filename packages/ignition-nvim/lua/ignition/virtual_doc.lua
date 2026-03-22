-- Virtual document system for managing decoded scripts
-- Tracks the relationship between scratch buffers and source JSON files

local M = {}

-- Storage for virtual document metadata
-- Key: virtual buffer number
-- Value: { source_bufnr, source_file, script_key, line_num, original_content }
M.virtual_docs = {}

-- Create a new virtual document for a decoded script
function M.create_virtual_doc(source_bufnr, script_info)
  -- Set buffer name to indicate it's a virtual document
  local source_file = vim.api.nvim_buf_get_name(source_bufnr)
  local source_filename = vim.fn.fnamemodify(source_file, ':t')
  -- Use context if available for a more descriptive buffer name.
  -- Replace '/' with '>' to prevent Neovim from resolving the name as a
  -- filesystem path (e.g., "MyTag/Expression" would be treated as a subdir).
  local display_key = (script_info.context or script_info.key):gsub('/', '>')
  local virtual_name = string.format('[Ignition:%s:%s:L%d]', source_filename, display_key, script_info.line)

  -- Check if a virtual doc with this identity already exists
  -- Note: vim.fn.bufnr() treats [] as glob patterns, so we search our own table instead
  -- Identity = source buffer + script key + line number (prevents collisions between
  -- multiple eventScript entries in tag files)
  for bufnr, metadata in pairs(M.virtual_docs) do
    if vim.api.nvim_buf_is_valid(bufnr)
      and metadata.source_bufnr == source_bufnr
      and metadata.script_key == script_info.key
      and metadata.line_num == script_info.line then
      return bufnr
    end
  end

  -- Create a scratch buffer
  local virtual_bufnr = vim.api.nvim_create_buf(false, true)

  -- Set buffer options (filetype is set AFTER metadata so the FileType
  -- autocmd can access virtual_doc metadata when it fires synchronously)
  local is_expression = script_info.key == 'expression'
  vim.api.nvim_buf_set_option(virtual_bufnr, 'buftype', 'acwrite')
  vim.api.nvim_buf_set_option(virtual_bufnr, 'swapfile', false)

  -- Set the buffer name
  vim.api.nvim_buf_set_name(virtual_bufnr, virtual_name)

  -- Store metadata BEFORE setting filetype so the FileType autocmd
  -- in lsp.lua can resolve root_dir from meta.source_file
  M.virtual_docs[virtual_bufnr] = {
    source_bufnr = source_bufnr,
    source_file = source_file,
    script_key = script_info.key,
    line_num = script_info.line,
    original_content = script_info.content,
    line_text = script_info.line_text,
  }

  -- Set up autocommand for saving
  vim.api.nvim_create_autocmd('BufWriteCmd', {
    buffer = virtual_bufnr,
    callback = function()
      M.save_virtual_doc(virtual_bufnr)
    end,
    desc = 'Encode and save Ignition script back to JSON',
  })

  -- Set up autocommand for closing
  vim.api.nvim_create_autocmd('BufWipeout', {
    buffer = virtual_bufnr,
    callback = function()
      M.cleanup_virtual_doc(virtual_bufnr)
    end,
    desc = 'Clean up virtual document metadata',
  })

  -- Set filetype last — this fires the FileType autocmd which handles
  -- LSP attachment via lsp.lua (no separate vim.schedule needed)
  vim.api.nvim_buf_set_option(virtual_bufnr, 'filetype', is_expression and 'ignition_expr' or 'python')

  return virtual_bufnr
end

-- Save a virtual document back to its source
function M.save_virtual_doc(virtual_bufnr)
  local metadata = M.virtual_docs[virtual_bufnr]
  if not metadata then
    vim.notify('No source file found for this buffer', vim.log.levels.ERROR, {
      title = 'Ignition.nvim',
    })
    return false
  end

  -- Get the decoded content from the virtual buffer
  local decoded_lines = vim.api.nvim_buf_get_lines(virtual_bufnr, 0, -1, false)
  local decoded_content = table.concat(decoded_lines, '\n')

  -- Encode the content
  local encoding = require('ignition.encoding')
  local encoded_content = encoding.encode_script(decoded_content)

  -- Update the source buffer
  local json_parser = require('ignition.json_parser')
  local source_bufnr = metadata.source_bufnr

  -- Check if source buffer still exists
  if not vim.api.nvim_buf_is_valid(source_bufnr) then
    vim.notify(
      'Source buffer no longer exists. Cannot save.',
      vim.log.levels.ERROR,
      { title = 'Ignition.nvim' }
    )
    return false
  end

  -- Get the current line
  local line_text = vim.api.nvim_buf_get_lines(source_bufnr, metadata.line_num - 1, metadata.line_num, false)[1]

  -- Replace the script content
  local new_line = json_parser.replace_script_in_line(line_text, metadata.script_key, encoded_content)

  -- Update the source buffer
  vim.api.nvim_buf_set_lines(source_bufnr, metadata.line_num - 1, metadata.line_num, false, { new_line })

  -- Mark source buffer as modified
  vim.api.nvim_buf_set_option(source_bufnr, 'modified', true)

  -- Mark virtual buffer as unmodified
  vim.api.nvim_buf_set_option(virtual_bufnr, 'modified', false)

  vim.notify(
    string.format('Saved %s to %s', metadata.script_key, vim.fn.fnamemodify(metadata.source_file, ':t')),
    vim.log.levels.INFO,
    { title = 'Ignition.nvim' }
  )

  return true
end

-- Clean up virtual document metadata
function M.cleanup_virtual_doc(virtual_bufnr)
  M.virtual_docs[virtual_bufnr] = nil
end

-- Check if a buffer is a virtual document
function M.is_virtual_doc(bufnr)
  return M.virtual_docs[bufnr] ~= nil
end

-- Get metadata for a virtual document
function M.get_metadata(bufnr)
  return M.virtual_docs[bufnr]
end

-- Get all virtual documents for a source buffer
function M.get_virtual_docs_for_source(source_bufnr)
  local docs = {}
  for virtual_bufnr, metadata in pairs(M.virtual_docs) do
    if metadata.source_bufnr == source_bufnr then
      table.insert(docs, {
        bufnr = virtual_bufnr,
        metadata = metadata,
      })
    end
  end
  return docs
end

-- Close all virtual documents for a source buffer
function M.close_virtual_docs_for_source(source_bufnr)
  local docs = M.get_virtual_docs_for_source(source_bufnr)
  for _, doc in ipairs(docs) do
    if vim.api.nvim_buf_is_valid(doc.bufnr) then
      vim.api.nvim_buf_delete(doc.bufnr, { force = false })
    end
  end
end

return M
