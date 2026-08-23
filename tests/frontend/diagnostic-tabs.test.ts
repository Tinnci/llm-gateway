import { expect, test } from "bun:test";

import {
  diagnosticTabRenderers,
  registerDiagnosticTab,
  resetDiagnosticTabRenderers,
} from "../../custom_components/llm_gateway/frontend/voice-harness-diagnostic-tabs";

const noopRender = () => "";

test("registers tabs in ascending order with stable ties", () => {
  resetDiagnosticTabRenderers();
  registerDiagnosticTab({ id: "raw", labelKey: "runs.diag_raw", order: 60, render: noopRender });
  registerDiagnosticTab({ id: "overview", labelKey: "runs.diag_overview", order: 10, render: noopRender });
  registerDiagnosticTab({ id: "extra", labelKey: "runs.diag_raw", order: 10, render: noopRender });

  expect(diagnosticTabRenderers().map((entry) => entry.id)).toEqual([
    "overview",
    "extra",
    "raw",
  ]);
});

test("entries without an explicit order sort last", () => {
  resetDiagnosticTabRenderers();
  registerDiagnosticTab({ id: "late", labelKey: "runs.diag_raw", render: noopRender });
  registerDiagnosticTab({ id: "first", labelKey: "runs.diag_overview", order: 5, render: noopRender });

  expect(diagnosticTabRenderers().map((entry) => entry.id)).toEqual(["first", "late"]);
});

test("duplicate ids throw instead of silently replacing", () => {
  resetDiagnosticTabRenderers();
  const disposer = registerDiagnosticTab({
    id: "overview",
    labelKey: "runs.diag_overview",
    order: 10,
    render: noopRender,
  });

  expect(() =>
    registerDiagnosticTab({ id: "overview", labelKey: "runs.diag_overview", order: 99, render: noopRender }),
  ).toThrow("already registered");

  // A refused duplicate leaves the current registration serving.
  expect(diagnosticTabRenderers()).toHaveLength(1);
  expect(diagnosticTabRenderers()[0].order).toBe(10);
  disposer();
  expect(diagnosticTabRenderers()).toHaveLength(0);
});

test("malformed entries throw at registration time", () => {
  resetDiagnosticTabRenderers();
  // @ts-expect-error exercising runtime validation
  expect(() => registerDiagnosticTab(null)).toThrow(TypeError);
  // @ts-expect-error exercising runtime validation
  expect(() => registerDiagnosticTab({ labelKey: "k", render: noopRender })).toThrow("non-empty id");
  // @ts-expect-error exercising runtime validation
  expect(() => registerDiagnosticTab({ id: "x", render: noopRender })).toThrow("labelKey");
  // @ts-expect-error exercising runtime validation
  expect(() => registerDiagnosticTab({ id: "x", labelKey: "k" })).toThrow("render");
  expect(diagnosticTabRenderers()).toHaveLength(0);
});
