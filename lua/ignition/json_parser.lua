-- JSON parser for finding Ignition scripts
-- Parses Ignition JSON files to locate embedded scripts

local M = {}
local encoding = require('ignition.encoding')

-- Common JSON keys that contain scripts in Ignition
M.SCRIPT_KEYS = {
  'script',         -- General script fields
  'code',           -- Transform scripts
  'eventScript',    -- Event handler scripts
  'transform',      -- Script transforms
  'onActionPerformed', -- Button actions (Perspective)
  'onChange',       -- Value change scripts
  'onStartup',      -- Startup scripts
  'onShutdown',     -- Shutdown scripts
  'expression',     -- Tag expressions and perspective binding expressions
}

-- Parse buffer to find all script locations
-- Returns array of script info: { key, line, col, content, path }
function M.find_scripts(bufnr)
  bufnr = bufnr or vim.api.nvim_get_current_buf()
  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
  local scripts = {}

  for line_num, line_text in ipairs(lines) do
    -- Look for script keys with quoted string values
    for _, key in ipairs(M.SCRIPT_KEYS) do
      -- Find the key pattern first
      local key_pattern = string.format('"(%s)":%s*"', vim.pesc(key), '%s')
      local key_start, key_end, captured_key = line_text:find(key_pattern)

      if key_start and captured_key then
        -- Now extract the string value, handling escaped quotes
        local script_content = M.extract_json_string_value(line_text, key_end + 1)

        if script_content and script_content ~= '' then
          -- Check if this looks like an encoded script
          if encoding.is_encoded_script(script_content) then
            local script_entry = {
              key = captured_key,
              line = line_num,
              col = key_start,
              content = script_content,
              line_text = line_text,
            }

            -- For eventScript entries, compute tag context (tag name + event name)
            if captured_key == 'eventScript' then
              script_entry.context = M.get_tag_context(lines, line_num)
            elseif captured_key == 'expression' then
              script_entry.context = M.get_expression_context(lines, line_num)
            end

            table.insert(scripts, script_entry)
          end
        end
      end
    end
  end

  return scripts
end

-- Extract a JSON string value starting at position, handling escaped characters
-- Returns the string content (without quotes)
function M.extract_json_string_value(text, start_pos)
  local i = start_pos
  local result = {}

  while i <= #text do
    local char = text:sub(i, i)
    local next_char = text:sub(i + 1, i + 1)

    if char == '\\' and next_char ~= '' then
      -- Escape sequence - include both the backslash and next character
      table.insert(result, char)
      table.insert(result, next_char)
      i = i + 2 -- Skip both characters
    elseif char == '"' then
      -- Unescaped quote - end of string
      return table.concat(result)
    else
      -- Regular character
      table.insert(result, char)
      i = i + 1
    end
  end

  -- String didn't close properly
  return nil
end

-- Extract script content from a specific line
function M.extract_script_from_line(line_text, key)
  local key_pattern = string.format('"(%s)":%s*"', vim.pesc(key), '%s')
  local key_start, key_end, captured_key = line_text:find(key_pattern)

  if key_start and captured_key then
    return M.extract_json_string_value(line_text, key_end + 1)
  end

  return nil
end

-- Replace script content in a line
function M.replace_script_in_line(line_text, key, new_content)
  -- Find the key and the start of the string value
  local key_pattern = string.format('"(%s)":%s*"', vim.pesc(key), '%s')
  local key_start, key_end = line_text:find(key_pattern)

  if not key_start then
    return line_text
  end

  -- Find the end of the old string value
  local old_content_start = key_end + 1
  local old_value = M.extract_json_string_value(line_text, old_content_start)

  if not old_value then
    return line_text
  end

  -- Calculate positions
  local old_content_end = old_content_start + #old_value
  local before = line_text:sub(1, old_content_start - 1)
  local after = line_text:sub(old_content_end + 1) -- Skip the closing quote

  -- Reconstruct the line with new content
  return before .. new_content .. '"' .. after
end

-- Get tag context for an eventScript entry
-- Scans backward from the script line to find the event name and tag name
-- Returns a string like "MyTag/valueChanged" or falls back to "Event Script"
function M.get_tag_context(lines, script_line_num)
  local event_name = nil
  local tag_name = nil

  -- Scan backward from the eventScript line
  for i = script_line_num - 1, math.max(1, script_line_num - 20), -1 do
    local line = lines[i]
    if line then
      -- Look for the event name key (e.g., "valueChanged":)
      if not event_name then
        local event = line:match('"(%w+)"%s*:%s*{')
        if event and event ~= 'eventScripts' then
          event_name = event
        end
      end

      -- Look for the tag name (e.g., "name": "MyTag")
      if not tag_name then
        local name = line:match('"name"%s*:%s*"([^"]*)"')
        if name then
          tag_name = name
        end
      end

      -- Found both, stop scanning
      if event_name and tag_name then
        break
      end
    end
  end

  if tag_name and event_name then
    return tag_name .. '/' .. event_name
  elseif tag_name then
    return tag_name .. '/Event Script'
  elseif event_name then
    return event_name
  end

  return nil
end

-- Get expression context for an expression entry
-- Scans backward from the expression line to find the tag name
-- Returns a string like "MyTag/Expression" or falls back to nil
function M.get_expression_context(lines, script_line_num)
  for i = script_line_num - 1, math.max(1, script_line_num - 15), -1 do
    local line = lines[i]
    if line then
      local name = line:match('"name"%s*:%s*"([^"]*)"')
      if name then
        return name .. '/Expression'
      end
    end
  end
  return nil
end

-- Get context information for a script
-- Returns a human-readable description of where the script is
function M.get_script_context(script_info)
  -- Use pre-computed context if available (e.g., from tag context detection)
  if script_info.context then
    return script_info.context
  end

  local key = script_info.key
  local contexts = {
    script = 'Script',
    code = 'Transform Code',
    eventScript = 'Event Script',
    transform = 'Script Transform',
    onActionPerformed = 'Action Script',
    onChange = 'Change Script',
    onStartup = 'Startup Script',
    onShutdown = 'Shutdown Script',
    expression = 'Expression',
  }

  return contexts[key] or ('Script (' .. key .. ')')
end

-- Check if buffer contains any Ignition scripts
function M.has_scripts(bufnr)
  local scripts = M.find_scripts(bufnr)
  return #scripts > 0
end

-- Get statistics about scripts in buffer
function M.get_script_stats(bufnr)
  local scripts = M.find_scripts(bufnr)
  local stats = {
    count = #scripts,
    by_type = {},
    total_length = 0,
  }

  for _, script in ipairs(scripts) do
    local key = script.key
    stats.by_type[key] = (stats.by_type[key] or 0) + 1
    stats.total_length = stats.total_length + #script.content
  end

  return stats
end

return M
