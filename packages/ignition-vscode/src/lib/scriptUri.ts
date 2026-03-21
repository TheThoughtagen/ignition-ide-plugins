/**
 * Pure logic for encoding/decoding Ignition script URIs.
 *
 * No VS Code dependency — testable in plain Node.
 *
 * URI format: ignition-script:///{base64url-source}/{key}/{line}/{timestamp}
 */

export const SCHEME = "ignition-script";

export interface ScriptMetadata {
  sourceUri: string;
  key: string;
  line: number;
}

/**
 * Encode a source URI + key + line into a script URI path.
 */
export function buildScriptPath(
  sourceUri: string,
  key: string,
  line: number,
  timestamp?: number
): string {
  const encodedSource = Buffer.from(sourceUri).toString("base64url");
  const ts = timestamp ?? Date.now();
  return `/${encodedSource}/${key}/${line}/${ts}`;
}

/**
 * Parse a script URI path into metadata.
 *
 * Accepts paths like: /base64source/eventScript/42/1711234567890
 * Returns undefined if the path is malformed.
 */
export function parseScriptPath(uriPath: string): ScriptMetadata | undefined {
  const parts = uriPath.split("/").filter(Boolean);
  if (parts.length < 3) {
    return undefined;
  }

  let sourceUri: string;
  try {
    sourceUri = Buffer.from(parts[0], "base64url").toString("utf-8");
  } catch {
    return undefined;
  }

  const key = parts[1];
  const line = parseInt(parts[2], 10);
  if (isNaN(line)) {
    return undefined;
  }

  return { sourceUri, key, line };
}
