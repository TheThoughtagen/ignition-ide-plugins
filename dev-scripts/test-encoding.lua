-- Test encoding/decoding directly
-- Run: :luafile dev-scripts/test-encoding.lua

print('=== Testing Encoding/Decoding ===')

-- Dynamically find plugin root (parent of dev-scripts directory)
local script_path = debug.getinfo(1, 'S').source:sub(2)
local plugin_root = vim.fn.fnamemodify(script_path, ':h:h')

package.loaded['ignition.encoding'] = nil
package.path = package.path .. ';' .. plugin_root .. '/lua/?.lua'

local encoding = require('ignition.encoding')

-- Test 1: Simple newline
print('\n--- Test 1: Newline ---')
local test1_decoded = "line1\nline2"
print('Original (decoded):', vim.inspect(test1_decoded))

local test1_encoded = encoding.encode_script(test1_decoded)
print('Encoded:', vim.inspect(test1_encoded))
print('Expected:', vim.inspect('line1\\nline2'))

local test1_redecoded = encoding.decode_script(test1_encoded)
print('Re-decoded:', vim.inspect(test1_redecoded))
print('Match:', test1_decoded == test1_redecoded)

-- Test 2: Real Ignition example (from ignition-lint)
print('\n--- Test 2: Real Ignition Script ---')
-- This is what's literally in the JSON file (as we read it)
local real_encoded = '\\timport json\\n\\turl = \"test\"'
print('Input (encoded):', vim.inspect(real_encoded))
print('Input length:', #real_encoded)

local real_decoded = encoding.decode_script(real_encoded)
print('Decoded:', vim.inspect(real_decoded))
print('Decoded length:', #real_decoded)
print('Should have tab and newline as actual characters')

-- Test 3: Check what we're actually getting from the buffer
print('\n--- Test 3: From Current Buffer ---')
local bufnr = vim.api.nvim_get_current_buf()
local lines = vim.api.nvim_buf_get_lines(bufnr, 8, 9, false)
if #lines > 0 then
  local line = lines[1]
  print('Line 9 from buffer:')
  print('  Length:', #line)
  print('  First 100 chars:', vim.inspect(line:sub(1, 100)))

  -- Try to find the script value
  local script_start = line:find('"script":', 1, true)
  if script_start then
    print('  Found "script" at position:', script_start)
    local value_start = line:find('"', script_start + 10, true)
    if value_start then
      print('  Value starts at:', value_start)
      print('  Next 50 chars:', vim.inspect(line:sub(value_start + 1, value_start + 50)))
    end
  end
end
