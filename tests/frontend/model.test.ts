import { describe, expect, test } from "bun:test";

import { harnessOverview } from "../../custom_components/llm_gateway/frontend/voice-harness-model";

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
