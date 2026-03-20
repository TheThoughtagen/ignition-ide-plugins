import * as vscode from "vscode";
import { getClient } from "./lspClient";
import { getConfig } from "./config";

interface ScriptInfo {
  key: string;
  line: number;
  content: string;
  context: string;
  decodedPreview: string;
}

/**
 * Provides CodeLens annotations above embedded scripts in Ignition JSON files.
 *
 * Each script gets a clickable "Edit Script (context)" lens that opens
 * the decoded script in a virtual document tab.
 */
export class IgnitionCodeLensProvider implements vscode.CodeLensProvider {
  private _onDidChangeCodeLenses = new vscode.EventEmitter<void>();
  readonly onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;

  async provideCodeLenses(
    document: vscode.TextDocument,
    _token: vscode.CancellationToken
  ): Promise<vscode.CodeLens[]> {
    const config = getConfig();
    if (!config.codeLensEnabled) {
      return [];
    }

    // Only provide CodeLens for JSON files in Ignition projects
    if (!document.fileName.endsWith(".json")) {
      return [];
    }

    const client = getClient();
    if (!client) {
      return [];
    }

    try {
      const scripts: ScriptInfo[] = await client.sendRequest(
        "ignition/findScripts",
        { uri: document.uri.toString() }
      );

      return scripts.map((script) => {
        // CodeLens appears on the line containing the script (0-based)
        const range = new vscode.Range(script.line - 1, 0, script.line - 1, 0);

        return new vscode.CodeLens(range, {
          title: `$(edit) Edit Script (${script.context})`,
          command: "ignition.openScript",
          arguments: [document.uri.toString(), script.key, script.line],
          tooltip: script.decodedPreview || "Open decoded script",
        });
      });
    } catch {
      return [];
    }
  }

  refresh(): void {
    this._onDidChangeCodeLenses.fire();
  }

  dispose(): void {
    this._onDidChangeCodeLenses.dispose();
  }
}
