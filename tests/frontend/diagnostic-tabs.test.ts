import { expect, test } from "bun:test";

import {
  defineDiagnosticTabs,
} from "../../custom_components/llm_gateway/frontend/voice-harness-diagnostic-tabs";

const noopRender = () => "";

test("defines tabs in ascending order with stable ties", () => {
  const tabs = defineDiagnosticTabs([
    { id: "raw", labelKey: "runs.diag_raw", order: 60, render: noopRender },
    { id: "overview", labelKey: "runs.diag_overview", order: 10, render: noopRender },
    { id: "extra", labelKey: "runs.diag_raw", order: 10, render: noopRender },
  ]);

  expect(tabs.map((entry) => entry.id)).toEqual([
    "overview",
    "extra",
    "raw",
  ]);
});

test("entries without an explicit order sort last", () => {
  const tabs = defineDiagnosticTabs([
    { id: "late", labelKey: "runs.diag_raw", render: noopRender },
    { id: "first", labelKey: "runs.diag_overview", order: 5, render: noopRender },
  ]);

  expect(tabs.map((entry) => entry.id)).toEqual(["first", "late"]);
});

test("duplicate ids throw instead of silently replacing", () => {
  expect(() =>
    defineDiagnosticTabs([
      { id: "overview", labelKey: "runs.diag_overview", order: 10, render: noopRender },
      { id: "overview", labelKey: "runs.diag_overview", order: 99, render: noopRender },
    ]),
  ).toThrow("already defined");
});

test("malformed entries throw at composition time", () => {
  // @ts-expect-error exercising runtime validation
  expect(() => defineDiagnosticTabs(null)).toThrow(TypeError);
  // @ts-expect-error exercising runtime validation
  expect(() => defineDiagnosticTabs([null])).toThrow(TypeError);
  // @ts-expect-error exercising runtime validation
  expect(() => defineDiagnosticTabs([{ labelKey: "k", render: noopRender }])).toThrow("non-empty id");
  // @ts-expect-error exercising runtime validation
  expect(() => defineDiagnosticTabs([{ id: "x", render: noopRender }])).toThrow("labelKey");
  // @ts-expect-error exercising runtime validation
  expect(() => defineDiagnosticTabs([{ id: "x", labelKey: "k" }])).toThrow("render");
});
