import { describe, it, expect } from "vitest";
import { buildScriptPath, parseScriptPath } from "../src/lib/scriptUri.js";

describe("buildScriptPath", () => {
  it("encodes source URI as base64url", () => {
    const path = buildScriptPath("file:///home/project/tags.json", "eventScript", 42, 1000);
    expect(path).toMatch(/^\/[A-Za-z0-9_-]+\/eventScript\/42\/1000$/);
  });

  it("includes key and line number", () => {
    const path = buildScriptPath("file:///test.json", "script", 10, 0);
    expect(path).toContain("/script/10/");
  });

  it("handles special characters in source URI", () => {
    const path = buildScriptPath("file:///path/with spaces/file.json", "code", 1, 0);
    const parsed = parseScriptPath(path);
    expect(parsed?.sourceUri).toBe("file:///path/with spaces/file.json");
  });
});

describe("parseScriptPath", () => {
  it("round-trips with buildScriptPath", () => {
    const sourceUri = "file:///home/user/project/resource.json";
    const path = buildScriptPath(sourceUri, "eventScript", 42, 999);
    const result = parseScriptPath(path);

    expect(result).toBeDefined();
    expect(result!.sourceUri).toBe(sourceUri);
    expect(result!.key).toBe("eventScript");
    expect(result!.line).toBe(42);
  });

  it("handles all script key types", () => {
    for (const key of ["script", "eventScript", "expression", "onActionPerformed", "transform"]) {
      const path = buildScriptPath("file:///test.json", key, 1, 0);
      const result = parseScriptPath(path);
      expect(result?.key).toBe(key);
    }
  });

  it("returns undefined for too few segments", () => {
    expect(parseScriptPath("/only-one")).toBeUndefined();
    expect(parseScriptPath("/two/parts")).toBeUndefined();
  });

  it("returns undefined for non-numeric line", () => {
    const encoded = Buffer.from("file:///test.json").toString("base64url");
    expect(parseScriptPath(`/${encoded}/script/notanumber`)).toBeUndefined();
  });

  it("returns undefined for empty path", () => {
    expect(parseScriptPath("")).toBeUndefined();
  });

  it("handles path with timestamp (4 segments)", () => {
    const sourceUri = "file:///test.json";
    const path = buildScriptPath(sourceUri, "code", 5, 1711234567890);
    const result = parseScriptPath(path);
    expect(result!.sourceUri).toBe(sourceUri);
    expect(result!.key).toBe("code");
    expect(result!.line).toBe(5);
  });

  it("handles URIs with unicode characters", () => {
    const sourceUri = "file:///données/fichier.json";
    const path = buildScriptPath(sourceUri, "script", 1, 0);
    const result = parseScriptPath(path);
    expect(result!.sourceUri).toBe(sourceUri);
  });
});
