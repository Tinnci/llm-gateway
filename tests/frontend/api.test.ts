import { describe, expect, test } from "bun:test";

import {
  parseHarnessStatus,
  requestHarnessJson,
} from "../../custom_components/llm_gateway/frontend/voice-harness-api";

const status = {
  editable: {
    max_tokens: { min: 1, max: 100 },
    routing_modes: ["auto"],
    timeouts: { min: 1, max: 30 },
    trace_max_runs: { min: 1, max: 20 },
    trace_retention_hours: { min: 1, max: 48 },
  },
  entries: [{ entry_id: "entry-1", state: "loaded", title: "Gateway" }],
  satellite: { diagnostic_snapshot: { checks: [] } },
};

describe("Voice Harness API boundary", () => {
  test("preserves valid extension fields", () => {
    expect(parseHarnessStatus(status)).toEqual(status);
  });

  test("rejects a malformed status envelope", () => {
    expect(() => parseHarnessStatus({ editable: {}, entries: [] })).toThrow(
      "Invalid Voice Harness status response",
    );
  });

  test("uses the Home Assistant API transport when available", async () => {
    const calls: unknown[][] = [];
    const result = await requestHarnessJson(
      {
        callApi: async (...args) => {
          calls.push(args);
          return { ok: true };
        },
      },
      "POST",
      "llm_gateway/harness/evaluate",
      { user: "hello" },
    );
    expect(result).toEqual({ ok: true });
    expect(calls).toEqual([
      ["POST", "llm_gateway/harness/evaluate", { user: "hello" }],
    ]);
  });
});
