import { expect, test } from "bun:test";

import {
  defineHarnessViews,
} from "../../custom_components/llm_gateway/frontend/voice-harness-view-registry";

const render = () => "";

test("defines views in stable order", () => {
  const views = defineHarnessViews([
    { id: "later", labelKey: "tab.config", icon: "mdi:cog", order: 20, render },
    { id: "first", labelKey: "tab.runs", icon: "mdi:play", order: 10, render },
    { id: "tie", labelKey: "tab.memory", icon: "mdi:database", order: 10, render },
  ]);

  expect(views.map((entry) => entry.id)).toEqual(["first", "tie", "later"]);
});

test("rejects duplicate and malformed definitions", () => {
  expect(() =>
    defineHarnessViews([
      { id: "runs", labelKey: "tab.runs", icon: "mdi:play", order: 10, render },
      { id: "runs", labelKey: "tab.config", icon: "mdi:cog", order: 20, render },
    ]),
  ).toThrow("already defined");
  // @ts-expect-error exercising runtime validation
  expect(() => defineHarnessViews(null)).toThrow(TypeError);
  // @ts-expect-error exercising runtime validation
  expect(() => defineHarnessViews([null])).toThrow(TypeError);
  // @ts-expect-error exercising runtime validation
  expect(() => defineHarnessViews([{ labelKey: "tab.runs", icon: "mdi:play", render }])).toThrow("id");
  // @ts-expect-error exercising runtime validation
  expect(() => defineHarnessViews([{ id: "x", icon: "mdi:play", render }])).toThrow("labelKey");
  // @ts-expect-error exercising runtime validation
  expect(() => defineHarnessViews([{ id: "x", labelKey: "tab.runs", render }])).toThrow("icon");
  // @ts-expect-error exercising runtime validation
  expect(() => defineHarnessViews([{ id: "x", labelKey: "tab.runs", icon: "mdi:play" }])).toThrow("render");
});

test("accepts an optional visibility predicate", () => {
  const [view] = defineHarnessViews([{
    id: "conditional",
    labelKey: "tab.satellite",
    icon: "mdi:microphone",
    order: 10,
    render,
    visible: (panel) => panel.enabled,
  }]);

  expect(view.visible?.({ enabled: true })).toBe(true);
  expect(view.visible?.({ enabled: false })).toBe(false);
});
