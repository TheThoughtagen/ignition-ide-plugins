import * as vscode from "vscode";
import { getClient } from "./lspClient";

export const SCHEME = "ignition-script";

interface ScriptMetadata {
  sourceUri: string;
  key: string;
  line: number;
}

export function buildScriptUri(
  sourceUri: string,
  key: string,
  line: number
): vscode.Uri {
  const encodedSource = Buffer.from(sourceUri).toString("base64url");
  // Include timestamp in path to force VS Code to create a fresh document
  // (VS Code caches FileSystemProvider content per URI path)
  const ts = Date.now();
  return vscode.Uri.parse(
    `${SCHEME}:///${encodedSource}/${key}/${line}/${ts}`
  );
}

export function parseScriptUri(uri: vscode.Uri): ScriptMetadata | undefined {
  const parts = uri.path.split("/").filter(Boolean);
  if (parts.length < 3) {
    return undefined;
  }
  const sourceUri = Buffer.from(parts[0], "base64url").toString("utf-8");
  const key = parts[1];
  const line = parseInt(parts[2], 10);
  if (isNaN(line)) {
    return undefined;
  }
  return { sourceUri, key, line };
}

interface ScriptInfo {
  key: string;
  line: number;
  content: string;
  context: string;
  decodedPreview: string;
}

/**
 * Virtual filesystem for decoded Ignition scripts.
 *
 * Always fetches fresh content from the LSP on readFile.
 * ignition/decodeScript returns dedented content + indent prefix.
 * ignition/saveScript accepts the indent prefix to re-indent before encoding.
 */
export class ScriptFileSystemProvider implements vscode.FileSystemProvider {
  private _emitter = new vscode.EventEmitter<vscode.FileChangeEvent[]>();
  readonly onDidChangeFile = this._emitter.event;

  // Store indent prefix per path for save round-trip
  private _indent = new Map<string, string>();

  watch(): vscode.Disposable {
    return new vscode.Disposable(() => {});
  }

  stat(): vscode.FileStat {
    return {
      type: vscode.FileType.File,
      ctime: Date.now(),
      mtime: Date.now(),
      size: 0,
    };
  }

  readDirectory(): [string, vscode.FileType][] {
    return [];
  }

  createDirectory(): void {}

  async readFile(uri: vscode.Uri): Promise<Uint8Array> {
    // Always fetch fresh from LSP — no stale cache issues
    const { text, indent } = await this._decodeFromLsp(uri);
    this._indent.set(uri.path, indent);
    return new TextEncoder().encode(text);
  }

  async writeFile(
    uri: vscode.Uri,
    content: Uint8Array,
    _options: { create: boolean; overwrite: boolean }
  ): Promise<void> {
    const text = new TextDecoder().decode(content);
    const indent = this._indent.get(uri.path) ?? "";
    await this._saveToLsp(uri, text, indent);
    this._emitter.fire([{ type: vscode.FileChangeType.Changed, uri }]);
  }

  delete(uri: vscode.Uri): void {
    this._indent.delete(uri.path);
  }

  rename(): void {}

  async preload(uri: vscode.Uri): Promise<void> {
    // Pre-fetch to warm the indent cache (readFile will fetch content again)
    const { indent } = await this._decodeFromLsp(uri);
    this._indent.set(uri.path, indent);
  }

  private async _decodeFromLsp(
    uri: vscode.Uri
  ): Promise<{ text: string; indent: string }> {
    const meta = parseScriptUri(uri);
    if (!meta) {
      return { text: "# Error: invalid ignition-script URI", indent: "" };
    }

    const client = getClient();
    if (!client) {
      return { text: "# Error: LSP client not connected", indent: "" };
    }

    try {
      const scripts: ScriptInfo[] = await client.sendRequest(
        "ignition/findScripts",
        { uri: meta.sourceUri }
      );

      const target = scripts.find(
        (s) => s.key === meta.key && s.line === meta.line
      );

      if (!target) {
        return {
          text: `# Error: script not found at ${meta.key} line ${meta.line}`,
          indent: "",
        };
      }

      const result: { decoded: string; indent?: string; error?: string } =
        await client.sendRequest("ignition/decodeScript", {
          encoded: target.content,
        });

      if (result.error) {
        vscode.window.showErrorMessage(`Failed to decode script: ${result.error}`);
        return { text: `# Error decoding script: ${result.error}`, indent: "" };
      }

      return { text: result.decoded, indent: result.indent ?? "" };
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      return { text: `# Error decoding script: ${message}`, indent: "" };
    }
  }

  private async _saveToLsp(
    uri: vscode.Uri,
    content: string,
    indent: string
  ): Promise<void> {
    const meta = parseScriptUri(uri);
    if (!meta) {
      vscode.window.showErrorMessage("Cannot save: invalid script URI");
      return;
    }

    const client = getClient();
    if (!client) {
      vscode.window.showErrorMessage("Cannot save: LSP client not connected");
      return;
    }

    try {
      const result: { success: boolean; error?: string } =
        await client.sendRequest("ignition/saveScript", {
          uri: meta.sourceUri,
          line: meta.line,
          key: meta.key,
          decodedContent: content,
          indent: indent,
        });

      if (!result.success) {
        vscode.window.showErrorMessage(
          `Failed to save script: ${result.error}`
        );
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      vscode.window.showErrorMessage(`Error saving script: ${message}`);
    }
  }

  dispose(): void {
    this._emitter.dispose();
  }
}
