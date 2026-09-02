import { expect, test } from "bun:test";

import {
  harnessViews,
  registerHarnessView,
  resetHarnessViews,
} from "../../custom_components/llm_gateway/frontend/voice-harness-view-registry";

const render = () => "";

test("registers views in stable order and returns detached snapshots", () => {
  resetHarnessViews();
  registerHarnessView({ id: "later", labelKey: "tab.config", icon: "mdi:cog", order: 20, render });
  registerHarnessView({ id: "first", labelKey: "tab.runs", icon: "mdi:play", order: 10, render });
  registerHarnessView({ id: "tie", labelKey: "tab.memory", icon: "mdi:database", order: 10, render });

  const snapshot = harnessViews();
  expect(snapshot.map((entry) => entry.id)).toEqual(["first", "tie", "later"]);
  snapshot[0].id = "changed";
  expect(harnessViews()[0].id).toBe("first");
});

test("disposer removes only its registration", () => {
  resetHarnessViews();
  const disposeFirst = registerHarnessView({
    id: "first",
    labelKey: "tab.runs",
    icon: "mdi:play",
    order: 10,
    render,
  });
  registerHarnessView({
    id: "second",
    labelKey: "tab.config",
    icon: "mdi:cog",
    order: 20,
    render,
  });

  disposeFirst();
  expect(harnessViews().map((entry) => entry.id)).toEqual(["second"]);
});

test("rejects duplicate and malformed registrations", () => {
  resetHarnessViews();
  registerHarnessView({ id: "runs", labelKey: "tab.runs", icon: "mdi:play", order: 10, render });

  expect(() =>
    registerHarnessView({ id: "runs", labelKey: "tab.config", icon: "mdi:cog", order: 20, render }),
  ).toThrow("already registered");
  // @ts-expect-error exercising runtime validation
  expect(() => registerHarnessView(null)).toThrow(TypeError);
  // @ts-expect-error exercising runtime validation
  expect(() => registerHarnessView({ labelKey: "tab.runs", icon: "mdi:play", render })).toThrow("id");
  // @ts-expect-error exercising runtime validation
  expect(() => registerHarnessView({ id: "x", icon: "mdi:play", render })).toThrow("labelKey");
  // @ts-expect-error exercising runtime validation
  expect(() => registerHarnessView({ id: "x", labelKey: "tab.runs", render })).toThrow("icon");
  // @ts-expect-error exercising runtime validation
  expect(() => registerHarnessView({ id: "x", labelKey: "tab.runs", icon: "mdi:play" })).toThrow("render");
  expect(harnessViews()).toHaveLength(1);
});

test("accepts an optional visibility predicate", () => {
  resetHarnessViews();
  registerHarnessView({
    id: "conditional",
    labelKey: "tab.satellite",
    icon: "mdi:microphone",
    order: 10,
    render,
    visible: (panel) => panel.enabled,
  });

  const [view] = harnessViews();
  expect(view.visible?.({ enabled: true })).toBe(true);
  expect(view.visible?.({ enabled: false })).toBe(false);
});
