import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { execFile, execFileSync } from "child_process";
import { isKindlingFile } from "./lib/projectFiles.js";

const KINDLING_REPO = "https://github.com/paul-griffith/kindling";

/**
 * Find the Kindling executable.
 *
 * Search order:
 * 1. User-configured path in settings
 * 2. Common installation paths (macOS, Linux)
 * 3. System PATH
 */
function findKindling(): string | undefined {
  const configPath = vscode.workspace
    .getConfiguration("ignition")
    .get<string>("kindling.path", "");

  if (configPath && fs.existsSync(configPath)) {
    return configPath;
  }

  // Common paths
  const home = process.env.HOME ?? "";
  const candidates = [
    "/usr/local/bin/kindling",
    "/opt/homebrew/bin/kindling",
    path.join(home, "Applications/Kindling.app/Contents/MacOS/kindling"),
    "/usr/bin/kindling",
    path.join(home, ".local/bin/kindling"),
    "/snap/bin/kindling",
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  // Try PATH lookup (platform-aware)
  try {
    const whichCmd = process.platform === "win32" ? "where" : "which";
    const result = execFileSync(whichCmd, ["kindling"], { timeout: 3000 })
      .toString()
      .trim();
    if (result && fs.existsSync(result)) {
      return result;
    }
  } catch {
    // Not found on PATH
  }

  return undefined;
}

/**
 * Open a file with Kindling.
 */
export async function openWithKindling(fileUri?: vscode.Uri): Promise<void> {
  const filePath = fileUri
    ? fileUri.fsPath
    : vscode.window.activeTextEditor?.document.uri.fsPath;

  if (!filePath) {
    vscode.window.showWarningMessage("No file to open");
    return;
  }

  const ext = path.extname(filePath).toLowerCase();
  if (!isKindlingFile(ext)) {
    vscode.window.showWarningMessage(
      `Kindling doesn't support ${ext} files. Supported: .gwbk, .modl, .idb, .log`
    );
    return;
  }

  const kindlingPath = findKindling();
  if (!kindlingPath) {
    const action = await vscode.window.showWarningMessage(
      "Kindling is not installed. It is required to open .gwbk files.",
      "View on GitHub",
      "Configure Path"
    );

    if (action === "View on GitHub") {
      vscode.env.openExternal(vscode.Uri.parse(KINDLING_REPO));
    } else if (action === "Configure Path") {
      vscode.commands.executeCommand(
        "workbench.action.openSettings",
        "ignition.kindling.path"
      );
    }
    return;
  }

  // Launch Kindling as a detached process
  const child = execFile(kindlingPath, [filePath], { timeout: 0 });
  child.on("error", (err) => {
    vscode.window.showErrorMessage(`Failed to launch Kindling: ${err.message}`);
  });
  child.unref();

  const fileName = path.basename(filePath);
  vscode.window.showInformationMessage(`Opening in Kindling: ${fileName}`);
}
