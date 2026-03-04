-- Tests for Ignition JSON parser
-- Run with: nvim --headless -u tests/minimal_init.lua -c "PlenaryBustedFile tests/json_parser_spec.lua"

local json_parser = require('ignition.json_parser')
local eq = assert.are.equal

describe('SCRIPT_KEYS', function()
  it('contains expected script key names', function()
    local keys = {}
    for _, k in ipairs(json_parser.SCRIPT_KEYS) do
      keys[k] = true
    end

    assert.is_true(keys['script'])
    assert.is_true(keys['code'])
    assert.is_true(keys['eventScript'])
    assert.is_true(keys['transform'])
    assert.is_true(keys['onActionPerformed'])
    assert.is_true(keys['onChange'])
    assert.is_true(keys['onStartup'])
    assert.is_true(keys['onShutdown'])
  end)

  it('has at least 8 known script keys', function()
    assert.is_true(#json_parser.SCRIPT_KEYS >= 8)
  end)
end)

describe('extract_json_string_value', function()
  it('extracts a simple string', function()
    local text = 'hello world"rest'
    local result = json_parser.extract_json_string_value(text, 1)
    eq('hello world', result)
  end)

  it('extracts an empty string', function()
    local text = '"rest'
    local result = json_parser.extract_json_string_value(text, 1)
    eq('', result)
  end)

  it('handles escaped quotes inside the string', function()
    local text = 'print(\\"hello\\")","next_key"'
    local result = json_parser.extract_json_string_value(text, 1)
    eq('print(\\"hello\\")', result)
  end)

  it('handles escaped backslashes', function()
    local text = 'path\\\\to\\\\file"rest'
    local result = json_parser.extract_json_string_value(text, 1)
    eq('path\\\\to\\\\file', result)
  end)

  it('handles escaped newlines', function()
    local text = 'line1\\nline2"rest'
    local result = json_parser.extract_json_string_value(text, 1)
    eq('line1\\nline2', result)
  end)

  it('handles Unicode escapes', function()
    local text = 'x \\u003d 5"rest'
    local result = json_parser.extract_json_string_value(text, 1)
    eq('x \\u003d 5', result)
  end)

  it('returns nil for unterminated string', function()
    local text = 'no closing quote here'
    local result = json_parser.extract_json_string_value(text, 1)
    assert.is_nil(result)
  end)

  it('extracts from a mid-string start position', function()
    local text = '  "key": "the value"'
    -- Start after the opening quote of the value (position 11)
    local result = json_parser.extract_json_string_value(text, 11)
    eq('the value', result)
  end)

  it('handles complex encoded script content', function()
    local text = 'logger \\u003d system.util.getLogger(\\"Test\\")\\nlogger.info(\\"Value\\")","next"'
    local result = json_parser.extract_json_string_value(text, 1)
    eq('logger \\u003d system.util.getLogger(\\"Test\\")\\nlogger.info(\\"Value\\")', result)
  end)

  it('handles escaped tab characters', function()
    local text = 'if True:\\n\\treturn 1"rest'
    local result = json_parser.extract_json_string_value(text, 1)
    eq('if True:\\n\\treturn 1', result)
  end)
end)

describe('extract_script_from_line', function()
  it('extracts script content by key name', function()
    local line = '    "script": "print(\\"hello\\")",'
    local result = json_parser.extract_script_from_line(line, 'script')
    eq('print(\\"hello\\")', result)
  end)

  it('extracts code content by key name', function()
    local line = '    "code": "x \\u003d 5",'
    local result = json_parser.extract_script_from_line(line, 'code')
    eq('x \\u003d 5', result)
  end)

  it('returns nil when key is not found', function()
    local line = '    "script": "print(\\"hello\\")"'
    local result = json_parser.extract_script_from_line(line, 'code')
    assert.is_nil(result)
  end)

  it('returns nil for empty line', function()
    local result = json_parser.extract_script_from_line('', 'script')
    assert.is_nil(result)
  end)

  it('handles key with whitespace after colon', function()
    local line = '    "script":  "value"'
    local result = json_parser.extract_script_from_line(line, 'script')
    eq('value', result)
  end)

  it('handles onActionPerformed key', function()
    local line = '  "onActionPerformed": "system.perspective.print(\\"hi\\")\\nreturn True",'
    local result = json_parser.extract_script_from_line(line, 'onActionPerformed')
    eq('system.perspective.print(\\"hi\\")\\nreturn True', result)
  end)
end)

describe('replace_script_in_line', function()
  it('replaces script content in a simple line', function()
    local line = '    "script": "old content",'
    local result = json_parser.replace_script_in_line(line, 'script', 'new content')
    eq('    "script": "new content",', result)
  end)

  it('replaces encoded content with new encoded content', function()
    local line = '    "script": "print(\\"hello\\")",'
    local result = json_parser.replace_script_in_line(line, 'script', 'print(\\"world\\")')
    eq('    "script": "print(\\"world\\")",', result)
  end)

  it('returns original line when key not found', function()
    local line = '    "script": "content",'
    local result = json_parser.replace_script_in_line(line, 'code', 'new')
    eq(line, result)
  end)

  it('preserves surrounding JSON structure', function()
    local line = '  "code": "x \\u003d 1", "other": "value"'
    local result = json_parser.replace_script_in_line(line, 'code', 'y \\u003d 2')
    eq('  "code": "y \\u003d 2", "other": "value"', result)
  end)

  it('handles multiline encoded scripts', function()
    local line = '    "script": "line1\\nline2\\nline3",'
    local result = json_parser.replace_script_in_line(line, 'script', 'a\\nb\\nc')
    eq('    "script": "a\\nb\\nc",', result)
  end)
end)

describe('expression extraction', function()
  it('expression key in SCRIPT_KEYS', function()
    local keys = {}
    for _, k in ipairs(json_parser.SCRIPT_KEYS) do
      keys[k] = true
    end
    assert.is_true(keys['expression'])
  end)

  it('extracts simple expression without encoded patterns', function()
    local line = '    "expression": "{[default]Level} * 100",'
    local result = json_parser.extract_script_from_line(line, 'expression')
    eq('{[default]Level} * 100', result)
  end)

  it('extracts expression with unicode escapes', function()
    local line = '    "expression": "if({Tag}, \\u0027On\\u0027, \\u0027Off\\u0027)",'
    local result = json_parser.extract_script_from_line(line, 'expression')
    eq('if({Tag}, \\u0027On\\u0027, \\u0027Off\\u0027)', result)
  end)
end)

describe('get_expression_context', function()
  it('finds tag name above expression line', function()
    local lines = {
      '  {',
      '    "name": "CalcTag",',
      '    "tagType": "ExpressionTag",',
      '    "expression": "{[default]Level} * 2"',
      '  }',
    }
    local result = json_parser.get_expression_context(lines, 4)
    eq('CalcTag/Expression', result)
  end)

  it('returns nil when no name found', function()
    local lines = {
      '  {',
      '    "expression": "{[default]Level} * 2"',
      '  }',
    }
    local result = json_parser.get_expression_context(lines, 2)
    assert.is_nil(result)
  end)
end)

describe('get_script_context', function()
  it('returns Script for script key', function()
    eq('Script', json_parser.get_script_context({ key = 'script' }))
  end)

  it('returns Transform Code for code key', function()
    eq('Transform Code', json_parser.get_script_context({ key = 'code' }))
  end)

  it('returns Event Script for eventScript key', function()
    eq('Event Script', json_parser.get_script_context({ key = 'eventScript' }))
  end)

  it('returns Action Script for onActionPerformed key', function()
    eq('Action Script', json_parser.get_script_context({ key = 'onActionPerformed' }))
  end)

  it('returns Change Script for onChange key', function()
    eq('Change Script', json_parser.get_script_context({ key = 'onChange' }))
  end)

  it('returns Startup Script for onStartup key', function()
    eq('Startup Script', json_parser.get_script_context({ key = 'onStartup' }))
  end)

  it('returns Shutdown Script for onShutdown key', function()
    eq('Shutdown Script', json_parser.get_script_context({ key = 'onShutdown' }))
  end)

  it('returns Script Transform for transform key', function()
    eq('Script Transform', json_parser.get_script_context({ key = 'transform' }))
  end)

  it('returns fallback for unknown key', function()
    local result = json_parser.get_script_context({ key = 'customKey' })
    eq('Script (customKey)', result)
  end)
end)
