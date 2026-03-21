import * as path from "path";
import * as fs from "fs";
import * as vscode from "vscode";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  TransportKind,
} from "vscode-languageclient/node";
import { getConfig } from "./config";

let client: LanguageClient | undefined;

/**
 * Find the ignition-lsp executable.
 *
 * Search order:
 * 1. User-configured path in settings
 * 2. Extension global storage venv
 * 3. System PATH
 */
async function findLspBinary(
  context: vscode.ExtensionContext
): Promise<string | undefined> {
  const config = getConfig();

  // 1. User-configured path
  if (config.lspPath && fs.existsSync(config.lspPath)) {
    return config.lspPath;
  }

  // 2. Extension global storage venv
  const binDir = process.platform === "win32" ? "Scripts" : "bin";
  const venvBin = path.join(
    context.globalStorageUri.fsPath,
    "venv",
    binDir,
    "ignition-lsp"
  );
  if (fs.existsSync(venvBin)) {
    return venvBin;
  }

  // 3. Check if ignition-lsp is on PATH
  // We try running it with --version to see if it's available
  try {
    const { execFileSync } = require("child_process");
    execFileSync("ignition-lsp", ["--help"], { timeout: 5000 });
    return "ignition-lsp";
  } catch {
    // Not found on PATH
  }

  return undefined;
}

/**
 * Install ignition-lsp into the extension's global storage venv.
 */
async function installLsp(
  context: vscode.ExtensionContext
): Promise<string | undefined> {
  const venvDir = path.join(context.globalStorageUri.fsPath, "venv");

  const answer = await vscode.window.showInformationMessage(
    "Ignition Dev Tools: ignition-lsp is not installed. Install it now?",
    "Install",
    "Cancel"
  );

  if (answer !== "Install") {
    return undefined;
  }

  return vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Installing ignition-lsp...",
      cancellable: false,
    },
    async () => {
      const { execFileSync } = require("child_process");
      try {
        // Ensure global storage directory exists
        fs.mkdirSync(context.globalStorageUri.fsPath, { recursive: true });

        // Create venv
        execFileSync("python3", ["-m", "venv", venvDir], { timeout: 30000 });

        // Install ignition-lsp
        const installBinDir = process.platform === "win32" ? "Scripts" : "bin";
        const pipPath = path.join(venvDir, installBinDir, "pip");
        execFileSync(pipPath, ["install", "ignition-lsp"], { timeout: 120000 });

        const binary = path.join(venvDir, installBinDir, "ignition-lsp");
        if (fs.existsSync(binary)) {
          vscode.window.showInformationMessage(
            "ignition-lsp installed successfully!"
          );
          return binary;
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        vscode.window.showErrorMessage(
          `Failed to install ignition-lsp: ${message}`
        );
      }
      return undefined;
    }
  );
}

export async function startLspClient(
  context: vscode.ExtensionContext
): Promise<LanguageClient | undefined> {
  let binary = await findLspBinary(context);

  if (!binary) {
    binary = await installLsp(context);
    if (!binary) {
      return undefined;
    }
  }

  const serverOptions: ServerOptions = {
    command: binary,
    transport: TransportKind.stdio,
  };

  const config = getConfig();
  const clientOptions: LanguageClientOptions = {
    documentSelector: [
      { scheme: "file", language: "python" },
      { scheme: "file", language: "ignition" },
      { scheme: "file", language: "json" },
      { scheme: "ignition-script", language: "python" },
      { scheme: "ignition-script", language: "plaintext" },
    ],
    synchronize: {
      fileEvents: vscode.workspace.createFileSystemWatcher("**/*.{py,json}"),
      configurationSection: "ignition",
    },
    initializationOptions: {
      ignition: {
        diagnostics: { enabled: config.diagnosticsEnabled },
        version: config.ignitionVersion,
      },
    },
  };

  client = new LanguageClient(
    "ignition-lsp",
    "Ignition Language Server",
    serverOptions,
    clientOptions
  );

  try {
    await client.start();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    vscode.window.showErrorMessage(`Failed to start ignition-lsp: ${message}`);
    client = undefined;
    return undefined;
  }
  return client;
}

export function getClient(): LanguageClient | undefined {
  return client;
}

/**
 * Query the LSP for stubs paths and configure Pyright/Pylance.
 *
 * Adds the system.* stubs and project stubs to python.analysis.extraPaths
 * so Pylance provides type hints for Ignition APIs.
 */
export async function configurePyrightStubs(): Promise<void> {
  if (!client) {
    return;
  }

  try {
    const result: { systemStubsPath?: string; projectStubsPath?: string } =
      await client.sendRequest("ignition/stubsInfo", {});

    const extraPaths: string[] = [];
    if (result.systemStubsPath) {
      extraPaths.push(result.systemStubsPath);
    }
    if (result.projectStubsPath) {
      extraPaths.push(result.projectStubsPath);
    }

    if (extraPaths.length === 0) {
      return;
    }

    // Update python.analysis.extraPaths for Pylance
    const pythonConfig = vscode.workspace.getConfiguration("python.analysis");
    const existing = pythonConfig.get<string[]>("extraPaths", []);
    const merged = [...existing];
    let changed = false;

    for (const p of extraPaths) {
      if (!merged.includes(p)) {
        merged.push(p);
        changed = true;
      }
    }

    if (changed) {
      await pythonConfig.update(
        "extraPaths",
        merged,
        vscode.ConfigurationTarget.Workspace
      );
      console.log("Ignition: configured Pylance extraPaths:", merged);
    }
  } catch (err) {
    console.error("Ignition: failed to configure stubs:", err);
  }
}

export async function stopLspClient(): Promise<void> {
  if (client) {
    await client.stop();
    client = undefined;
  }
}
