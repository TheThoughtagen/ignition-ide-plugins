-- Script encoding/decoding utilities for Ignition
-- Based on ignition-flint: https://github.com/keith-gamble/ignition-flint

local M = {}

-- Character replacement map
-- This matches the encoding used by Ignition when storing scripts in JSON
-- Source: ignition-flint/src/utils/textEncoding.ts
M.REPLACEMENT_CHARS = {
  { from = '\\', to = '\\\\' },     -- Backslash (must be first!)
  { from = '"', to = '\\"' },       -- Double quote
  { from = '\t', to = '\\t' },      -- Tab
  { from = '\b', to = '\\b' },      -- Backspace
  { from = '\n', to = '\\n' },      -- Newline
  { from = '\r', to = '\\r' },      -- Carriage return
  { from = '\f', to = '\\f' },      -- Form feed
  { from = '<', to = '\\u003c' },   -- Less than (Unicode escape)
  { from = '>', to = '\\u003e' },   -- Greater than (Unicode escape)
  { from = '&', to = '\\u0026' },   -- Ampersand (Unicode escape)
  { from = '=', to = '\\u003d' },   -- Equals (Unicode escape)
  { from = "'", to = '\\u0027' },   -- Single quote (Unicode escape)
}

-- Encode Python code for storage in JSON
-- Converts special characters to their escaped/Unicode equivalents
function M.encode_script(code)
  if not code or code == '' then
    return ''
  end

  local encoded = code

  -- Apply each character replacement using plain string replacement
  for _, replacement in ipairs(M.REPLACEMENT_CHARS) do
    local search = replacement.from
    local replace = replacement.to

    -- Use simple string replacement (split and join)
    local parts = {}
    local start = 1
    while true do
      local pos = encoded:find(search, start, true) -- true = plain search, no patterns
      if not pos then
        table.insert(parts, encoded:sub(start))
        break
      end
      table.insert(parts, encoded:sub(start, pos - 1))
      table.insert(parts, replace)
      start = pos + #search
    end
    encoded = table.concat(parts)
  end

  return encoded
end

-- Decode script from JSON string format
-- Uses single-pass parsing to correctly distinguish \\t (literal backslash + t)
-- from \t (tab escape). Multi-pass replacement cannot handle this safely.
function M.decode_script(encoded)
  if not encoded or encoded == '' then
    return ''
  end

  -- Map of single-char escapes after backslash
  local escape_map = {
    ['\\'] = '\\',
    ['"']  = '"',
    ['t']  = '\t',
    ['b']  = '\b',
    ['n']  = '\n',
    ['r']  = '\r',
    ['f']  = '\f',
  }

  -- Map of unicode escapes (\uXXXX)
  local unicode_map = {
    ['003c'] = '<',
    ['003e'] = '>',
    ['0026'] = '&',
    ['003d'] = '=',
    ['0027'] = "'",
  }

  local result = {}
  local i = 1
  local len = #encoded

  while i <= len do
    if encoded:sub(i, i) == '\\' and i < len then
      local next_char = encoded:sub(i + 1, i + 1)

      if next_char == 'u' and i + 5 <= len then
        -- Potential unicode escape: \uXXXX
        local code = encoded:sub(i + 2, i + 5)
        if unicode_map[code] then
          table.insert(result, unicode_map[code])
          i = i + 6
        else
          -- Unknown unicode escape, keep as-is
          table.insert(result, '\\')
          i = i + 1
        end
      elseif escape_map[next_char] then
        table.insert(result, escape_map[next_char])
        i = i + 2
      else
        -- Unknown escape, keep backslash
        table.insert(result, '\\')
        i = i + 1
      end
    else
      table.insert(result, encoded:sub(i, i))
      i = i + 1
    end
  end

  return table.concat(result)
end

-- Test if a string appears to be an encoded Ignition script
-- Looks for common encoded patterns
function M.is_encoded_script(text)
  if not text or text == '' then
    return false
  end

  -- Check for common encoded patterns
  local patterns = {
    '\\n',     -- Escaped newlines are very common in scripts
    '\\t',     -- Escaped tabs
    '\\"',     -- Escaped quotes
    '\\u00',   -- Unicode escapes (\u003c, \u003e, \u003d, \u0026, \u0027)
  }

  for _, pattern in ipairs(patterns) do
    if text:find(pattern, 1, true) then
      return true
    end
  end

  return false
end

-- Get encoding statistics (for debugging)
function M.encoding_stats(text)
  local stats = {
    length = #text,
    newlines = 0,
    tabs = 0,
    quotes = 0,
    unicode_escapes = 0,
  }

  for _ in text:gmatch('\\n') do
    stats.newlines = stats.newlines + 1
  end

  for _ in text:gmatch('\\t') do
    stats.tabs = stats.tabs + 1
  end

  for _ in text:gmatch('\\"') do
    stats.quotes = stats.quotes + 1
  end

  for _ in text:gmatch('\\u%d%d%d%d') do
    stats.unicode_escapes = stats.unicode_escapes + 1
  end

  return stats
end

return M
