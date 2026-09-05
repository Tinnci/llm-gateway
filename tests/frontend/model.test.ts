import { describe, expect, test } from "bun:test";

import { harnessOverview, runOutcome, runTone } from "../../custom_components/llm_gateway/frontend/voice-harness-model";

test("semantic outcome distinguishes clarification from execution failure", () => {
  expect(runOutcome({ status: "ok", route: { terminal_outcome: "failed" } })).toBe("failed");
  expect(runOutcome({ status: "ok", terminal_outcome: "clarify", outcome: "clarify" })).toBe("clarification");
  expect(runOutcome({ status: "ok", outcome: "not_answered", failure_stage: "ambiguous_target" })).toBe("clarification");
  expect(runTone({ status: "ok", outcome: "not_answered" })).toBe("bad");
  expect(runTone({ status: "cancelled" })).toBe("warning");
  expect(runTone({ status: "ok", outcome: "answered" })).toBe("ok");
});

describe("Voice Harness overview projection", () => {
  test("combines run, provider, and diagnostic signals", () => {
    const overview = harnessOverview(
      [
        {
          model_providers: { config_error: "invalid provider" },
          provider_health: [{ failures: 2 }, { failures: 0 }],
          traces: {
            records: [
              { latency_ms: 200, status: "ok" },
              { latency_ms: 400, status: "error" },
            ],
          },
          voice_runs: [{ status: "running" }],
        },
      ],
      [
        { id: "audio", status: "warning" },
        { id: "network", status: "ok" },
      ],
    );

    expect(overview).toEqual({
      averageLatency: 300,
      diagnosticIssues: 1,
      entryCount: 1,
      providerIssues: 2,
      recentErrors: 1,
      running: 1,
    });
  });

  test("returns a stable empty projection", () => {
    expect(harnessOverview([], [])).toEqual({
      averageLatency: 0,
      diagnosticIssues: 0,
      entryCount: 0,
      providerIssues: 0,
      recentErrors: 0,
      running: 0,
    });
  });
});
