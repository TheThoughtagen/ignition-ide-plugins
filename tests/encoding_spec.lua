-- Tests for Ignition encoding/decoding functionality
-- Uses shared test vectors from tests/fixtures/encoding_test_vectors.json
-- so that Lua and Python implementations are cross-validated.
--
-- Run with: nvim --headless -u tests/minimal_init.lua -c "PlenaryBustedFile tests/encoding_spec.lua"

local encoding = require('ignition.encoding')
local eq = assert.are.equal

-- Load shared test vectors
local function load_vectors()
  local path = vim.fn.fnamemodify('tests/fixtures/encoding_test_vectors.json', ':p')
  local f = io.open(path, 'r')
  if not f then
    error('Could not open test vectors: ' .. path)
  end
  local content = f:read('*a')
  f:close()
  return vim.json.decode(content)
end

local vectors = load_vectors()

-- ── Standard Escapes ────────────────────────────────────────────────

describe('Encoding standard escapes', function()
  for _, case in ipairs(vectors.standard_escapes) do
    it('encodes ' .. case.name, function()
      eq(case.encoded, encoding.encode_script(case.decoded))
    end)
  end
end)

describe('Decoding standard escapes', function()
  for _, case in ipairs(vectors.standard_escapes) do
    it('decodes ' .. case.name, function()
      eq(case.decoded, encoding.decode_script(case.encoded))
    end)
  end
end)

-- ── Unicode Escapes ─────────────────────────────────────────────────

describe('Encoding unicode escapes', function()
  for _, case in ipairs(vectors.unicode_escapes) do
    it('encodes ' .. case.name, function()
      eq(case.encoded, encoding.encode_script(case.decoded))
    end)
  end
end)

describe('Decoding unicode escapes', function()
  for _, case in ipairs(vectors.unicode_escapes) do
    it('decodes ' .. case.name, function()
      eq(case.decoded, encoding.decode_script(case.encoded))
    end)
  end
end)

-- ── Round Trip ──────────────────────────────────────────────────────

describe('Encoding round-trip', function()
  for _, case in ipairs(vectors.round_trip) do
    it('round-trips ' .. case.name, function()
      local encoded = encoding.encode_script(case.text)
      local decoded = encoding.decode_script(encoded)
      eq(case.text, decoded)
    end)
  end
end)

-- ── Decode Edge Cases ───────────────────────────────────────────────

describe('Decoding edge cases', function()
  for _, case in ipairs(vectors.decode_edge_cases) do
    it('handles ' .. case.name, function()
      eq(case.decoded, encoding.decode_script(case.encoded))
    end)
  end
end)

-- ── Script Detection ────────────────────────────────────────────────

describe('Script detection', function()
  for _, case in ipairs(vectors.detection) do
    it((case.is_encoded and 'detects' or 'rejects') .. ' ' .. case.name, function()
      eq(case.is_encoded, encoding.is_encoded_script(case.text))
    end)
  end
end)
