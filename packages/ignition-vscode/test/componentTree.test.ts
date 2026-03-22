import { describe, it, expect } from "vitest";
import {
  isPerspectiveView,
  parseViewJson,
  walkComponent,
  detectScripts,
  flattenTree,
} from "../src/lib/componentTree.js";

describe("isPerspectiveView", () => {
  it("returns true for valid Perspective view", () => {
    expect(isPerspectiveView({ root: { type: "ia.container.flex" } })).toBe(true);
  });

  it("returns false for non-ia root type", () => {
    expect(isPerspectiveView({ root: { type: "custom.component" } })).toBe(false);
  });

  it("returns false for missing root", () => {
    expect(isPerspectiveView({ other: "data" })).toBe(false);
  });

  it("returns false for null", () => {
    expect(isPerspectiveView(null)).toBe(false);
  });

  it("returns false for non-object", () => {
    expect(isPerspectiveView("string")).toBe(false);
  });

  it("returns false for root without type", () => {
    expect(isPerspectiveView({ root: { meta: { name: "test" } } })).toBe(false);
  });
});

describe("parseViewJson", () => {
  it("parses a simple view", () => {
    const json = JSON.stringify({
      root: {
        type: "ia.container.flex",
        meta: { name: "root" },
      },
    });
    const result = parseViewJson(json);
    expect(result).toBeDefined();
    expect(result!.name).toBe("root");
    expect(result!.type).toBe("ia.container.flex");
    expect(result!.shortType).toBe("container.flex");
  });

  it("parses nested children", () => {
    const json = JSON.stringify({
      root: {
        type: "ia.container.flex",
        meta: { name: "root" },
        children: [
          {
            type: "ia.input.button",
            meta: { name: "MyButton" },
          },
          {
            type: "ia.display.label",
            meta: { name: "MyLabel" },
          },
        ],
      },
    });
    const result = parseViewJson(json);
    expect(result!.children).toHaveLength(2);
    expect(result!.children[0].name).toBe("MyButton");
    expect(result!.children[1].name).toBe("MyLabel");
  });

  it("returns undefined for invalid JSON", () => {
    expect(parseViewJson("not json")).toBeUndefined();
  });

  it("returns undefined for non-Perspective JSON", () => {
    expect(parseViewJson('{"key": "value"}')).toBeUndefined();
  });

  it("handles component without meta.name", () => {
    const json = JSON.stringify({
      root: { type: "ia.container.flex" },
    });
    const result = parseViewJson(json);
    expect(result!.name).toBe("(unnamed)");
  });
});

describe("detectScripts", () => {
  it("detects script key in events", () => {
    const component = {
      type: "ia.input.button",
      events: { onActionPerformed: { script: "print('hello')" } },
    };
    expect(detectScripts(component)).toBe(true);
  });

  it("detects nested script key", () => {
    const component = {
      type: "ia.input.button",
      events: {
        dom: {},
        component: { onActionPerformed: "code" },
      },
    };
    // onActionPerformed is a sub-key of "component"
    expect(detectScripts(component)).toBe(true);
  });

  it("returns false for no events", () => {
    expect(detectScripts({ type: "ia.display.label" })).toBe(false);
  });

  it("returns false for empty events", () => {
    expect(detectScripts({ type: "ia.display.label", events: {} })).toBe(false);
  });

  it("returns false for non-script event keys", () => {
    expect(
      detectScripts({
        type: "ia.display.label",
        events: { dom: {}, component: {} },
      })
    ).toBe(false);
  });
});

describe("walkComponent", () => {
  it("builds node with correct fields", () => {
    const node = walkComponent({
      type: "ia.container.flex",
      meta: { name: "Container1" },
    });
    expect(node.name).toBe("Container1");
    expect(node.type).toBe("ia.container.flex");
    expect(node.shortType).toBe("container.flex");
    expect(node.hasScripts).toBe(false);
    expect(node.children).toHaveLength(0);
  });

  it("recursively walks children", () => {
    const node = walkComponent({
      type: "ia.container.flex",
      meta: { name: "root" },
      children: [
        {
          type: "ia.input.button",
          meta: { name: "Button1" },
          children: [
            {
              type: "ia.display.icon",
              meta: { name: "Icon" },
            },
          ],
        },
      ],
    });
    expect(node.children).toHaveLength(1);
    expect(node.children[0].name).toBe("Button1");
    expect(node.children[0].children).toHaveLength(1);
    expect(node.children[0].children[0].name).toBe("Icon");
  });
});

describe("flattenTree", () => {
  it("flattens a simple tree depth-first", () => {
    const root = walkComponent({
      type: "ia.container.flex",
      meta: { name: "root" },
      children: [
        { type: "ia.input.button", meta: { name: "A" } },
        {
          type: "ia.container.flex",
          meta: { name: "B" },
          children: [
            { type: "ia.display.label", meta: { name: "C" } },
          ],
        },
      ],
    });

    const flat = flattenTree(root);
    expect(flat.map((n) => n.name)).toEqual(["root", "A", "B", "C"]);
  });

  it("respects expansion state", () => {
    const root = walkComponent({
      type: "ia.container.flex",
      meta: { name: "root" },
      children: [
        {
          type: "ia.container.flex",
          meta: { name: "collapsed" },
          children: [
            { type: "ia.display.label", meta: { name: "hidden" } },
          ],
        },
      ],
    });

    const flat = flattenTree(root, (n) => n.name !== "collapsed");
    expect(flat.map((n) => n.name)).toEqual(["root", "collapsed"]);
  });
});
