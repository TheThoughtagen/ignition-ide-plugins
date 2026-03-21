import * as vscode from "vscode";
import { ScriptFileSystemProvider } from "./scriptDocProvider";
import { openScript } from "./commands";

/** Script keys that indicate embedded scripts. */
const SCRIPT_KEYS = new Set([
  "script",
  "code",
  "eventScript",
  "transform",
  "onActionPerformed",
  "onChange",
  "onStartup",
  "onShutdown",
  "expression",
]);

interface ComponentNode {
  name: string;
  type: string;
  shortType: string;
  hasScripts: boolean;
  children: ComponentNode[];
}

export class ComponentTreeItem extends vscode.TreeItem {
  constructor(
    public readonly node: ComponentNode,
    public readonly sourceUri: vscode.Uri,
    collapsibleState: vscode.TreeItemCollapsibleState
  ) {
    super(node.name, collapsibleState);

    this.description = node.shortType;
    this.tooltip = `${node.name} (${node.type})`;

    if (node.hasScripts) {
      this.description += "  [scripts]";
      this.contextValue = "componentWithScripts";
    } else {
      this.contextValue = "component";
    }

    // Click navigates to component in source
    this.command = {
      command: "ignition.componentTree.reveal",
      title: "Go to Component",
      arguments: [this],
    };
  }
}

/**
 * Provides a tree view of Perspective component hierarchy.
 *
 * Parses Perspective view.json files and displays the component tree
 * in a sidebar, similar to ignition-nvim's :IgnitionComponentTree.
 */
export class ComponentTreeProvider
  implements vscode.TreeDataProvider<ComponentTreeItem>
{
  private _onDidChangeTreeData = new vscode.EventEmitter<
    ComponentTreeItem | undefined | void
  >();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private rootNode: ComponentNode | undefined;
  private sourceUri: vscode.Uri | undefined;

  refresh(): void {
    this.rootNode = undefined;
    this.sourceUri = undefined;

    const editor = vscode.window.activeTextEditor;
    if (editor && this.isPerspectiveView(editor.document)) {
      this.sourceUri = editor.document.uri;
      this.rootNode = this.parseViewJson(editor.document.getText());
    }

    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: ComponentTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: ComponentTreeItem): ComponentTreeItem[] {
    if (!this.rootNode || !this.sourceUri) {
      return [];
    }

    const children = element ? element.node.children : [this.rootNode];
    return children.map((child) => {
      const state =
        child.children.length > 0
          ? vscode.TreeItemCollapsibleState.Expanded
          : vscode.TreeItemCollapsibleState.None;
      return new ComponentTreeItem(child, this.sourceUri!, state);
    });
  }

  /**
   * Check if a document is a Perspective view.json.
   */
  isPerspectiveView(doc: vscode.TextDocument): boolean {
    if (!doc.fileName.endsWith(".json")) {
      return false;
    }
    try {
      const data = JSON.parse(doc.getText());
      return (
        data?.root?.type &&
        typeof data.root.type === "string" &&
        data.root.type.startsWith("ia.")
      );
    } catch {
      return false;
    }
  }

  /**
   * Parse a Perspective view.json into a component tree.
   */
  private parseViewJson(text: string): ComponentNode | undefined {
    try {
      const data = JSON.parse(text);
      if (!data?.root?.type?.startsWith("ia.")) {
        return undefined;
      }
      return this.walkComponent(data.root);
    } catch {
      return undefined;
    }
  }

  private walkComponent(component: Record<string, unknown>): ComponentNode {
    const meta = (component.meta as Record<string, unknown>) ?? {};
    const name = (meta.name as string) ?? "(unnamed)";
    const compType = (component.type as string) ?? "";
    const shortType = compType.replace(/^ia\./, "");
    const hasScripts = this.detectScripts(component);

    const children: ComponentNode[] = [];
    const childArray = component.children;
    if (Array.isArray(childArray)) {
      for (const child of childArray) {
        if (child && typeof child === "object") {
          children.push(this.walkComponent(child as Record<string, unknown>));
        }
      }
    }

    return { name, type: compType, shortType, hasScripts, children };
  }

  private detectScripts(component: Record<string, unknown>): boolean {
    const events = component.events;
    if (!events || typeof events !== "object") {
      return false;
    }
    for (const [key, val] of Object.entries(
      events as Record<string, unknown>
    )) {
      if (SCRIPT_KEYS.has(key)) {
        return true;
      }
      if (val && typeof val === "object") {
        for (const subKey of Object.keys(val as Record<string, unknown>)) {
          if (SCRIPT_KEYS.has(subKey)) {
            return true;
          }
        }
      }
    }
    return false;
  }

  dispose(): void {
    this._onDidChangeTreeData.dispose();
  }
}

/**
 * Register component tree commands and event handlers.
 */
export function registerComponentTree(
  context: vscode.ExtensionContext,
  provider: ComponentTreeProvider,
  scriptFsProvider: ScriptFileSystemProvider
): void {
  // Reveal component in source editor
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ignition.componentTree.reveal",
      async (item: ComponentTreeItem) => {
        const doc = await vscode.workspace.openTextDocument(item.sourceUri);
        const editor = await vscode.window.showTextDocument(doc, {
          preserveFocus: true,
          viewColumn: vscode.ViewColumn.One,
        });

        // Find the component by name in the source JSON
        const text = doc.getText();
        const pattern = `"name"\\s*:\\s*"${escapeRegex(item.node.name)}"`;
        const match = text.match(new RegExp(pattern));
        if (match && match.index !== undefined) {
          const pos = doc.positionAt(match.index);
          editor.selection = new vscode.Selection(pos, pos);
          editor.revealRange(
            new vscode.Range(pos, pos),
            vscode.TextEditorRevealType.InCenter
          );
        }
      }
    )
  );

  // Decode scripts for a component
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ignition.componentTree.decodeScripts",
      async (item: ComponentTreeItem) => {
        if (!item.node.hasScripts) {
          vscode.window.showInformationMessage(
            "No scripts on this component"
          );
          return;
        }

        // Find the component line and open scripts near it
        const doc = await vscode.workspace.openTextDocument(item.sourceUri);
        const text = doc.getText();
        const pattern = `"name"\\s*:\\s*"${escapeRegex(item.node.name)}"`;
        const match = text.match(new RegExp(pattern));
        if (match && match.index !== undefined) {
          const pos = doc.positionAt(match.index);
          const line = pos.line + 1; // 1-based

          // Find scripts near this component and open them
          const { getClient } = await import("./lspClient.js");
          const client = getClient();
          if (!client) {
            return;
          }

          interface ScriptInfo {
            key: string;
            line: number;
            context: string;
          }

          const scripts: ScriptInfo[] = await client.sendRequest(
            "ignition/findScripts",
            { uri: item.sourceUri.toString() }
          );

          // Find scripts within ~50 lines of the component
          const nearby = scripts.filter(
            (s) => Math.abs(s.line - line) < 50
          );

          for (const script of nearby) {
            await openScript(
              scriptFsProvider,
              item.sourceUri.toString(),
              script.key,
              script.line
            );
          }

          if (nearby.length === 0) {
            vscode.window.showInformationMessage(
              "No scripts found near this component"
            );
          }
        }
      }
    )
  );

  // Refresh on active editor change
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor(() => {
      provider.refresh();
    })
  );

  // Refresh on document save
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(() => {
      provider.refresh();
    })
  );

  // Initial refresh
  provider.refresh();
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
