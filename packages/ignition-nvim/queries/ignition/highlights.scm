; inherits: json

; Script keys → Special highlight
(pair
  key: (string
    (string_content) @ignition.script_key
    (#any-of? @ignition.script_key
      "script" "code" "eventScript" "transform"
      "onActionPerformed" "onChange" "onStartup" "onShutdown")))

; Component types (ia.*) → Type highlight
(pair
  key: (string (string_content) @_key (#eq? @_key "type"))
  value: (string
    (string_content) @type
    (#match? @type "^ia\\.")))

; Component names (meta.name values) → Label highlight
(pair
  key: (string (string_content) @_key (#eq? @_key "name"))
  value: (string (string_content) @label))

; Module IDs (com.inductiveautomation.*) → Module highlight
(pair
  value: (string
    (string_content) @module
    (#match? @module "^com\\.inductiveautomation\\.")))
