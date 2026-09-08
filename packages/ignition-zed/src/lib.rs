//! Zed extension for Inductive Automation's Ignition SCADA platform.
//!
//! Registers `ignition-lsp` — the same language server the Neovim and VS Code
//! plugins use — for Python and JSON files inside an Ignition project.
//!
//! Zed has no virtual-document API, so scripts embedded in JSON resources are
//! edited through the server's `ignition.decodeScriptToFile` and
//! `ignition.saveScriptToSource` code actions rather than in-memory buffers.

use zed_extension_api::{
    self as zed, settings::LspSettings, Architecture, LanguageServerId,
    LanguageServerInstallationStatus, Os, Result,
};

/// Console script installed by the `ignition-lsp` package on PyPI.
const SERVER_BINARY: &str = "ignition-lsp";

/// Language server id declared in `extension.toml`. Zed keys user settings
/// (`lsp.ignition-lsp.*`) off this name.
const SERVER_ID: &str = "ignition-lsp";

/// Every Ignition project has a `project.json` at its root. Without it we are
/// not in an Ignition project and must not attach to the worktree's Python and
/// JSON files.
const PROJECT_MARKER: &str = "project.json";

/// Virtualenv created inside the extension's working directory when the server
/// is not already installed.
const VENV_DIR: &str = "ignition-lsp-venv";

/// Default Ignition platform version for API completions.
const DEFAULT_IGNITION_VERSION: &str = "8.1";

struct IgnitionExtension {
    /// Resolved server path, cached so a worktree with many open files does not
    /// re-run binary discovery for each one.
    cached_binary: Option<String>,
}

impl IgnitionExtension {
    /// Whether the worktree is an Ignition project.
    fn is_ignition_project(worktree: &zed::Worktree) -> bool {
        worktree.read_text_file(PROJECT_MARKER).is_ok()
    }

    /// Path to the `pip`/`ignition-lsp` executables inside the managed venv.
    fn venv_bin(name: &str) -> String {
        let (os, _arch): (Os, Architecture) = zed::current_platform();
        match os {
            Os::Windows => format!("{VENV_DIR}/Scripts/{name}.exe"),
            Os::Mac | Os::Linux => format!("{VENV_DIR}/bin/{name}"),
        }
    }

    /// Locate the language server, installing it if necessary.
    ///
    /// Search order mirrors the Neovim and VS Code plugins:
    /// 1. an explicit `lsp.ignition-lsp.binary.path` setting,
    /// 2. a previously resolved path from this session,
    /// 3. a managed virtualenv from an earlier install,
    /// 4. `ignition-lsp` on `$PATH`,
    /// 5. a fresh `pip install` into a managed virtualenv.
    fn server_binary(
        &mut self,
        language_server_id: &LanguageServerId,
        worktree: &zed::Worktree,
    ) -> Result<String> {
        // 1. Explicit override — the escape hatch for project-local venvs and
        //    for anyone who would rather Zed never install anything.
        if let Some(path) = LspSettings::for_worktree(SERVER_ID, worktree)
            .ok()
            .and_then(|settings| settings.binary)
            .and_then(|binary| binary.path)
        {
            return Ok(path);
        }

        if let Some(cached) = &self.cached_binary {
            return Ok(cached.clone());
        }

        // 3. A venv this extension installed previously.
        let venv_server = Self::venv_bin(SERVER_BINARY);
        if std::fs::metadata(&venv_server).is_ok_and(|stat| stat.is_file()) {
            self.cached_binary = Some(venv_server.clone());
            return Ok(venv_server);
        }

        // 4. An `ignition-lsp` the user installed themselves.
        if let Some(path) = worktree.which(SERVER_BINARY) {
            self.cached_binary = Some(path.clone());
            return Ok(path);
        }

        // 5. Install it.
        let path = Self::install(language_server_id, worktree)?;
        self.cached_binary = Some(path.clone());
        Ok(path)
    }

    /// Create a virtualenv in the extension's working directory and pip-install
    /// the language server into it.
    fn install(language_server_id: &LanguageServerId, worktree: &zed::Worktree) -> Result<String> {
        let python = worktree
            .which("python3")
            .or_else(|| worktree.which("python"))
            .ok_or_else(|| {
                format!(
                    "Could not find Python on $PATH. Install Python 3.8+, or install \
                     the server yourself with `pip install {SERVER_BINARY}` and point \
                     Zed at it via `lsp.{SERVER_ID}.binary.path`."
                )
            })?;

        zed::set_language_server_installation_status(
            language_server_id,
            &LanguageServerInstallationStatus::Downloading,
        );

        run(
            zed::process::Command::new(&python)
                .arg("-m")
                .arg("venv")
                .arg(VENV_DIR),
            "create a virtualenv",
        )?;

        run(
            zed::process::Command::new(Self::venv_bin("pip"))
                .arg("install")
                .arg("--upgrade")
                .arg(SERVER_BINARY),
            "install ignition-lsp",
        )?;

        let server = Self::venv_bin(SERVER_BINARY);
        if !std::fs::metadata(&server).is_ok_and(|stat| stat.is_file()) {
            return Err(format!(
                "Installed {SERVER_BINARY} but no executable appeared at {server}."
            ));
        }

        Ok(server)
    }

    /// Settings for the server, merging Zed's `lsp.ignition-lsp.settings` over
    /// this extension's defaults.
    fn ignition_settings(worktree: &zed::Worktree) -> zed::serde_json::Value {
        merge_settings(
            LspSettings::for_worktree(SERVER_ID, worktree)
                .ok()
                .and_then(|settings| settings.settings),
        )
    }
}

/// Merge user-supplied LSP settings over this extension's defaults.
///
/// Split out from `ignition_settings` so the merge rules can be tested without
/// a `Worktree`, which only exists inside the Zed WASM host.
fn merge_settings(user: Option<zed::serde_json::Value>) -> zed::serde_json::Value {
    use zed::serde_json::{Map, Value};

    let mut settings = Map::new();
    settings.insert(
        "version".to_string(),
        Value::String(DEFAULT_IGNITION_VERSION.to_string()),
    );

    if let Some(Value::Object(user)) = user {
        // Accept both `{ "version": ... }` and `{ "ignition": { "version": ... } }`
        // so a config copied from the Neovim plugin works unchanged.
        let user = match user.get("ignition") {
            Some(Value::Object(nested)) => nested.clone(),
            _ => user,
        };
        settings.extend(user);
    }

    Value::Object(settings)
}

/// Run a command, turning a non-zero exit into a readable error.
fn run(mut command: zed::process::Command, what: &str) -> Result<()> {
    let output = command
        .output()
        .map_err(|err| format!("Failed to {what}: {err}"))?;

    if output.status != Some(0) {
        return Err(format!(
            "Failed to {what}: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }

    Ok(())
}

impl zed::Extension for IgnitionExtension {
    fn new() -> Self {
        Self {
            cached_binary: None,
        }
    }

    fn language_server_command(
        &mut self,
        language_server_id: &LanguageServerId,
        worktree: &zed::Worktree,
    ) -> Result<zed::Command> {
        // Declining here keeps the server off every Python and JSON file in
        // projects that have nothing to do with Ignition.
        if !Self::is_ignition_project(worktree) {
            return Err(format!(
                "Not an Ignition project: no {PROJECT_MARKER} at the worktree root. \
                 Open the Ignition project folder itself to enable Ignition support."
            ));
        }

        Ok(zed::Command {
            command: self.server_binary(language_server_id, worktree)?,
            args: Vec::new(),
            env: worktree.shell_env(),
        })
    }

    fn language_server_initialization_options(
        &mut self,
        _language_server_id: &LanguageServerId,
        worktree: &zed::Worktree,
    ) -> Result<Option<zed::serde_json::Value>> {
        use zed::serde_json::{Map, Value};

        // The server reads `ignition_version` from its initialization options;
        // this matches what the Neovim plugin sends.
        let version = Self::ignition_settings(worktree)
            .get("version")
            .and_then(Value::as_str)
            .unwrap_or(DEFAULT_IGNITION_VERSION)
            .to_string();

        let mut options = Map::new();
        options.insert("ignition_version".to_string(), Value::String(version));

        Ok(Some(Value::Object(options)))
    }

    fn language_server_workspace_configuration(
        &mut self,
        _language_server_id: &LanguageServerId,
        worktree: &zed::Worktree,
    ) -> Result<Option<zed::serde_json::Value>> {
        use zed::serde_json::{Map, Value};

        let mut configuration = Map::new();
        configuration.insert("ignition".to_string(), Self::ignition_settings(worktree));

        Ok(Some(Value::Object(configuration)))
    }
}

zed::register_extension!(IgnitionExtension);

#[cfg(test)]
mod tests {
    use super::*;
    use zed_extension_api::serde_json::json;

    #[test]
    fn defaults_when_no_user_settings() {
        assert_eq!(merge_settings(None), json!({"version": "8.1"}));
    }

    #[test]
    fn user_version_overrides_the_default() {
        let merged = merge_settings(Some(json!({"version": "8.0"})));
        assert_eq!(merged["version"], "8.0");
    }

    #[test]
    fn accepts_the_neovim_nested_shape() {
        let merged = merge_settings(Some(json!({"ignition": {"version": "8.0"}})));
        assert_eq!(merged["version"], "8.0");
    }

    #[test]
    fn unknown_keys_are_passed_through() {
        let merged = merge_settings(Some(json!({"somethingElse": true})));
        assert_eq!(merged["version"], "8.1");
        assert_eq!(merged["somethingElse"], true);
    }

    #[test]
    fn nested_shape_passes_through_unknown_keys_too() {
        let merged = merge_settings(Some(json!({"ignition": {"somethingElse": 42}})));
        assert_eq!(merged["version"], "8.1");
        assert_eq!(merged["somethingElse"], 42);
    }

    #[test]
    fn non_object_settings_fall_back_to_defaults() {
        assert_eq!(
            merge_settings(Some(json!("nonsense"))),
            json!({"version": "8.1"})
        );
    }
}
