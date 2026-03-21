import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";

/** Tag type icons matching the Ignition Designer. */
const TAG_TYPE_ICONS: Record<string, string> = {
  AtomicTag: "symbol-variable",
  Folder: "folder",
  UdtType: "symbol-class",
  UdtInstance: "symbol-object",
  OpcTag: "plug",
};

/** Data type display abbreviations. */
const DATA_TYPE_SHORT: Record<string, string> = {
  Boolean: "bool",
  String: "str",
  Integer: "int",
  Int2: "i16",
  Int4: "i32",
  Int8: "i64",
  Float4: "f32",
  Float8: "f64",
  Document: "doc",
  DateTime: "date",
};

/** Value source display abbreviations. */
const VALUE_SOURCE_SHORT: Record<string, string> = {
  memory: "mem",
  opc: "opc",
  expr: "expr",
  reference: "ref",
  derived: "derived",
  db: "db",
};

export type TagTreeItem = TagProviderItem | TagFolderItem | TagItem;

/**
 * Root tag provider node (e.g., "WHK01", "Gateway", "System").
 */
export class TagProviderItem extends vscode.TreeItem {
  constructor(
    public readonly providerName: string,
    public readonly providerPath: string
  ) {
    super(providerName, vscode.TreeItemCollapsibleState.Collapsed);
    this.contextValue = "tagProvider";
    this.iconPath = new vscode.ThemeIcon("server");
    this.tooltip = providerPath;
  }
}

/**
 * Tag folder node (directory in the tag tree).
 */
export class TagFolderItem extends vscode.TreeItem {
  constructor(
    public readonly folderName: string,
    public readonly folderPath: string
  ) {
    super(folderName, vscode.TreeItemCollapsibleState.Collapsed);
    this.contextValue = "tagFolder";
    this.iconPath = new vscode.ThemeIcon("folder");
    this.tooltip = folderPath;
  }
}

/**
 * Individual tag node (.json file).
 */
export class TagItem extends vscode.TreeItem {
  public readonly tagFilePath: string;
  public readonly tagType: string;

  constructor(
    tagName: string,
    filePath: string,
    tagMeta: { tagType?: string; dataType?: string; valueSource?: string; typeId?: string; hasScripts?: boolean }
  ) {
    const hasChildren = tagMeta.tagType === "UdtType" || tagMeta.tagType === "UdtInstance";
    super(
      tagName,
      hasChildren
        ? vscode.TreeItemCollapsibleState.Collapsed
        : vscode.TreeItemCollapsibleState.None
    );

    this.tagFilePath = filePath;
    this.tagType = tagMeta.tagType ?? "AtomicTag";
    this.contextValue = tagMeta.hasScripts ? "tagWithScripts" : "tag";

    // Icon based on tag type
    this.iconPath = new vscode.ThemeIcon(
      TAG_TYPE_ICONS[this.tagType] ?? "symbol-variable"
    );

    // Description: data type + value source
    const parts: string[] = [];
    if (tagMeta.dataType) {
      parts.push(DATA_TYPE_SHORT[tagMeta.dataType] ?? tagMeta.dataType);
    }
    if (tagMeta.valueSource) {
      parts.push(VALUE_SOURCE_SHORT[tagMeta.valueSource] ?? tagMeta.valueSource);
    }
    if (tagMeta.typeId) {
      parts.push(tagMeta.typeId.split("/").pop() ?? tagMeta.typeId);
    }
    if (tagMeta.hasScripts) {
      parts.push("[scripts]");
    }
    this.description = parts.join("  ");
    this.tooltip = `${tagName} (${this.tagType})${tagMeta.typeId ? `\nType: ${tagMeta.typeId}` : ""}`;

    // Click opens the tag JSON file
    this.command = {
      command: "vscode.open",
      title: "Open Tag",
      arguments: [vscode.Uri.file(filePath)],
    };
  }
}

/**
 * Tree data provider for the Ignition Tag Browser.
 *
 * Reads tag JSON files from the project's tags/ directory
 * (ignition-git-module format: one .json per tag, directories for folders).
 */
export class TagBrowserProvider
  implements vscode.TreeDataProvider<TagTreeItem>
{
  private _onDidChangeTreeData = new vscode.EventEmitter<
    TagTreeItem | undefined | void
  >();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private tagsDir: string | undefined;

  constructor() {
    this.findTagsDir();
  }

  refresh(): void {
    this.findTagsDir();
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: TagTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: TagTreeItem): Promise<TagTreeItem[]> {
    if (!this.tagsDir) {
      return [];
    }

    if (!element) {
      return this.getProviders();
    }

    if (element instanceof TagProviderItem) {
      return this.getTagChildren(element.providerPath);
    }

    if (element instanceof TagFolderItem) {
      return this.getTagChildren(element.folderPath);
    }

    if (element instanceof TagItem) {
      // UDT types/instances can have member tags defined in the JSON
      return this.getUdtMembers(element.tagFilePath);
    }

    return [];
  }

  /**
   * Find the tags/ directory in the workspace.
   */
  private findTagsDir(): void {
    this.tagsDir = undefined;
    const folders = vscode.workspace.workspaceFolders;
    if (!folders) {
      return;
    }

    for (const folder of folders) {
      const tagsPath = path.join(folder.uri.fsPath, "tags");
      if (fs.existsSync(tagsPath) && fs.statSync(tagsPath).isDirectory()) {
        this.tagsDir = tagsPath;
        return;
      }
    }
  }

  /**
   * Get tag providers (top-level directories in tags/).
   */
  private getProviders(): TagProviderItem[] {
    if (!this.tagsDir) {
      return [];
    }
    try {
      const entries = fs
        .readdirSync(this.tagsDir, { withFileTypes: true })
        .filter((e) => e.isDirectory())
        .sort((a, b) => a.name.localeCompare(b.name));

      return entries.map(
        (e) => new TagProviderItem(e.name, path.join(this.tagsDir!, e.name))
      );
    } catch (err) {
      console.warn("Ignition: failed to read tags directory:", err);
      return [];
    }
  }

  /**
   * Get tag children for a directory (folders + tag files).
   */
  private getTagChildren(dirPath: string): TagTreeItem[] {
    const items: TagTreeItem[] = [];
    try {
      const entries = fs
        .readdirSync(dirPath, { withFileTypes: true })
        .sort((a, b) => {
          // Directories first, then files
          if (a.isDirectory() && !b.isDirectory()) { return -1; }
          if (!a.isDirectory() && b.isDirectory()) { return 1; }
          return a.name.localeCompare(b.name);
        });

      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);

        if (entry.isDirectory()) {
          // Skip hidden directories
          if (entry.name.startsWith(".")) {
            continue;
          }
          // _types_ folder gets a special label
          const label = entry.name === "_types_" ? "UDT Definitions" : entry.name;
          items.push(new TagFolderItem(label, fullPath));
        } else if (entry.name.endsWith(".json") && !entry.name.startsWith(".")) {
          // Read tag metadata
          const meta = this.readTagMeta(fullPath);
          if (meta) {
            const tagName = entry.name.replace(/\.json$/, "");
            items.push(new TagItem(tagName, fullPath, meta));
          }
        }
      }
    } catch (err) {
      console.warn(`Ignition: failed to read tags in ${dirPath}:`, err);
    }
    return items;
  }

  /**
   * Read minimal metadata from a tag JSON file.
   */
  private readTagMeta(filePath: string): {
    tagType?: string;
    dataType?: string;
    valueSource?: string;
    typeId?: string;
    hasScripts?: boolean;
  } | undefined {
    try {
      const stat = fs.statSync(filePath);
      if (stat.size > 500_000) {
        return { tagType: "Folder" }; // Large files are likely bulk exports
      }
      const text = fs.readFileSync(filePath, "utf-8");
      const data = JSON.parse(text);
      return {
        tagType: data.tagType,
        dataType: data.dataType,
        valueSource: data.valueSource,
        typeId: data.typeId,
        hasScripts: Array.isArray(data.eventScripts) && data.eventScripts.length > 0,
      };
    } catch {
      return undefined;
    }
  }

  /**
   * Get member tags from a UDT type/instance JSON file.
   */
  private getUdtMembers(filePath: string): TagItem[] {
    try {
      const text = fs.readFileSync(filePath, "utf-8");
      const data = JSON.parse(text);
      const tags = data.tags;
      if (!Array.isArray(tags)) {
        return [];
      }

      return tags
        .filter((t: Record<string, unknown>) => t && typeof t === "object" && t.name)
        .map((t: Record<string, unknown>) => {
          const name = t.name as string;
          return new TagItem(name, filePath, {
            tagType: (t.tagType as string) ?? "AtomicTag",
            dataType: t.dataType as string | undefined,
            valueSource: t.valueSource as string | undefined,
            hasScripts:
              Array.isArray(t.eventScripts) &&
              (t.eventScripts as unknown[]).length > 0,
          });
        });
    } catch (err) {
      console.warn(`Ignition: failed to read UDT members from ${filePath}:`, err);
      return [];
    }
  }

  dispose(): void {
    this._onDidChangeTreeData.dispose();
  }
}

/**
 * Register tag browser commands.
 */
export function registerTagBrowser(
  context: vscode.ExtensionContext,
  provider: TagBrowserProvider
): void {
  // Copy tag path to clipboard
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ignition.tagBrowser.copyPath",
      async (item: TagTreeItem) => {
        let tagPath: string;
        if (item instanceof TagProviderItem) {
          tagPath = `[${item.providerName}]`;
        } else if (item instanceof TagFolderItem) {
          tagPath = deriveTagPath(item.folderPath, provider);
        } else if (item instanceof TagItem) {
          const name = path.basename(item.tagFilePath, ".json");
          const dir = path.dirname(item.tagFilePath);
          tagPath = deriveTagPath(dir, provider) + "/" + name;
        } else {
          return;
        }
        await vscode.env.clipboard.writeText(tagPath);
        vscode.window.showInformationMessage(`Copied: ${tagPath}`);
      }
    )
  );

  // Watch for tag file changes
  const watcher = vscode.workspace.createFileSystemWatcher("**/tags/**/*.json");
  watcher.onDidCreate(() => provider.refresh());
  watcher.onDidDelete(() => provider.refresh());
  context.subscriptions.push(watcher);
}

/**
 * Derive an Ignition tag path from a filesystem path.
 * e.g., /project/tags/WHK01/WH/WHK01/Folder → [WHK01]WH/WHK01/Folder
 */
function deriveTagPath(fsPath: string, provider: TagBrowserProvider): string {
  // Find the tags/ directory in the path
  const tagsIdx = fsPath.indexOf("/tags/");
  if (tagsIdx === -1) {
    return fsPath;
  }
  const relative = fsPath.substring(tagsIdx + 6); // after "/tags/"
  const parts = relative.split(path.sep);
  if (parts.length === 0) {
    return relative;
  }
  const providerName = parts[0];
  const rest = parts.slice(1).join("/");
  return rest ? `[${providerName}]${rest}` : `[${providerName}]`;
}
