/**
 * Pure logic for parsing Perspective view.json into component trees.
 *
 * No VS Code dependency — testable in plain Node.
 */

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

export interface ComponentNode {
  name: string;
  type: string;
  shortType: string;
  hasScripts: boolean;
  children: ComponentNode[];
}

/**
 * Check if parsed JSON is a Perspective view (root.type starts with "ia.").
 */
export function isPerspectiveView(data: unknown): boolean {
  if (!data || typeof data !== "object") {
    return false;
  }
  const obj = data as Record<string, unknown>;
  const root = obj.root;
  if (!root || typeof root !== "object") {
    return false;
  }
  const rootType = (root as Record<string, unknown>).type;
  return typeof rootType === "string" && rootType.startsWith("ia.");
}

/**
 * Parse a Perspective view.json string into a component tree.
 *
 * Returns the root ComponentNode, or undefined if the JSON is not
 * a valid Perspective view.
 */
export function parseViewJson(text: string): ComponentNode | undefined {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return undefined;
  }

  if (!isPerspectiveView(data)) {
    return undefined;
  }

  return walkComponent((data as Record<string, unknown>).root as Record<string, unknown>);
}

/**
 * Recursively walk a component and its children, building the tree.
 */
export function walkComponent(component: Record<string, unknown>): ComponentNode {
  const meta = (component.meta as Record<string, unknown>) ?? {};
  const name = (meta.name as string) ?? "(unnamed)";
  const compType = (component.type as string) ?? "";
  const shortType = compType.replace(/^ia\./, "");
  const hasScripts = detectScripts(component);

  const children: ComponentNode[] = [];
  const childArray = component.children;
  if (Array.isArray(childArray)) {
    for (const child of childArray) {
      if (child && typeof child === "object") {
        children.push(walkComponent(child as Record<string, unknown>));
      }
    }
  }

  return { name, type: compType, shortType, hasScripts, children };
}

/**
 * Check if a component has any scripts in its events.
 */
export function detectScripts(component: Record<string, unknown>): boolean {
  const events = component.events;
  if (!events || typeof events !== "object") {
    return false;
  }
  for (const [key, val] of Object.entries(events as Record<string, unknown>)) {
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

/**
 * Flatten a component tree into a list (depth-first, respecting expansion).
 */
export function flattenTree(
  node: ComponentNode,
  isExpanded: (node: ComponentNode) => boolean = () => true
): ComponentNode[] {
  const result: ComponentNode[] = [];
  function recurse(n: ComponentNode): void {
    result.push(n);
    if (isExpanded(n)) {
      for (const child of n.children) {
        recurse(child);
      }
    }
  }
  recurse(node);
  return result;
}
