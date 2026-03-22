-- Configuration validation and management
local M = {}

-- Configuration schema with types and defaults
M.schema = {
  lsp = {
    type = "table",
    default = {
      enabled = true,
      auto_start = true,
      cmd = nil,
      settings = {
        ignition = {
          version = "8.1",
          sdk_path = nil,
        },
      },
    },
    fields = {
      enabled = { type = "boolean", default = true },
      auto_start = { type = "boolean", default = true },
      cmd = { type = "table", default = nil, optional = true },
      settings = {
        type = "table",
        default = {
          ignition = {
            version = "8.1",
            sdk_path = nil,
          },
        },
      },
    },
  },
  kindling = {
    type = "table",
    default = {
      enabled = true,
      path = nil,
    },
    fields = {
      enabled = { type = "boolean", default = true },
      path = { type = "string", default = nil, optional = true },
    },
  },
  decoder = {
    type = "table",
    default = {
      auto_decode = true,
      auto_encode = true,
      create_scratch_buffer = true,
    },
    fields = {
      auto_decode = { type = "boolean", default = true },
      auto_encode = { type = "boolean", default = true },
      create_scratch_buffer = { type = "boolean", default = true },
    },
  },
  ui = {
    type = "table",
    default = {
      show_notifications = true,
      show_statusline = true,
    },
    fields = {
      show_notifications = { type = "boolean", default = true },
      show_statusline = { type = "boolean", default = true },
    },
  },
  component_tree = {
    type = "table",
    default = {
      width = 40,
      position = 'left',
    },
    fields = {
      width = { type = "number", default = 40 },
      position = { type = "string", default = 'left' },
    },
  },
}

-- Validate configuration against schema
function M.validate(config)
  local errors = {}

  for key, schema_def in pairs(M.schema) do
    if config[key] ~= nil then
      if type(config[key]) ~= schema_def.type then
        table.insert(
          errors,
          string.format(
            "Invalid type for '%s': expected %s, got %s",
            key,
            schema_def.type,
            type(config[key])
          )
        )
      end
    end
  end

  return #errors == 0, errors
end

-- Get default configuration
function M.defaults()
  local defaults = {}
  for key, schema_def in pairs(M.schema) do
    defaults[key] = vim.deepcopy(schema_def.default)
  end
  return defaults
end

return M
