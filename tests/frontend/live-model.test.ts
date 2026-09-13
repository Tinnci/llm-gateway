import { expect, test } from "bun:test";
import {
  observedMetrics,
  pipelineStages,
  livePipeline,
  pcmWave,
  supportsActionReplay,
  latestConversation,
  conversationFacts,
} from "../../custom_components/llm_gateway/frontend/voice-harness-live-model";

test("recorded action replay is unavailable for model replies and existing forks", () => {
  const action = {
    route_decision: { route: "local_action", next_action: "execute_local" },
  };
  expect(supportsActionReplay(action)).toBe(true);
  expect(
    supportsActionReplay({
      route_decision: { route: "fast", next_action: "answer_with_llm" },
    }),
  ).toBe(false);
  expect(
    supportsActionReplay({ ...action, lineage: { mode: "dry_run" } }),
  ).toBe(false);
  expect(supportsActionReplay({})).toBe(false);
});

test("missing measurements stay unknown and replay does not improve live success", () => {
  const metrics = observedMetrics([
    { status: "ok", latency_ms: 200 },
    { status: "error", latency_ms: 600 },
    { status: "running", latency_ms: null },
    { status: "ok", latency_ms: 1, lineage: { mode: "dry_run" } },
  ]);
  expect(metrics.medianMs).toBe(400);
  expect(metrics.successRate).toBe(50);
  expect(metrics.errorRate).toBe(50);
  expect(observedMetrics([]).medianMs).toBeNull();
  expect(observedMetrics([]).successRate).toBeNull();
});

test("summary-only dry runs cannot replace a real conversation or improve its metrics", () => {
  const real = { run_id: "live", created_at: "2026-09-13T10:00:00Z", status: "error", latency_ms: 400 };
  const replay = { run_id: "fork", created_at: "2026-09-13T11:00:00Z", status: "complete", outcome: "dry_run", terminal_outcome: "dry_run", latency_ms: 1 };
  expect(latestConversation([replay, real])).toBe(real);
  expect(observedMetrics([replay, real]).successRate).toBe(0);
});

test("an answered action and a successful dispatch cannot become device confirmation", () => {
  const facts = conversationFacts({
    status: "complete", task_family: "home_control", assistant_text: "已发送请求。",
    interaction: { dispatches: [{ dispatch_status: "sent", confirmation_status: "unknown" }] },
  });
  expect(facts.evidence).toBe("sent");
  expect(conversationFacts({ status: "complete", task_family: "home_control" }).evidence).toBe("unconfirmed");
  expect(conversationFacts({ status: "complete", assistant_text: "你好" }).evidence).toBe("reply");
  expect(conversationFacts({ status: "complete", terminal_outcome: "partial", task_family: "home_control", interaction: { dispatches: [{ dispatch_status: "sent" }] } }).evidence).toBe("partial");
});

test("a room answer shows its observation source and resolved follow-up intent", () => {
  const facts = conversationFacts({
    status: "complete", user_text: "那客厅呢？", assistant_text: "客厅现在 28.9 度。",
    interaction: { intent_text: "客厅温度是多少？", observations: [{ source: "ha_area_sensor", answerable: true, entities: [{ name: "客厅温度", state: "28.9" }] }] },
  });
  expect(facts.intent).toBe("客厅温度是多少？");
  expect(facts.evidence).toBe("observed");
  expect(facts.sources).toEqual(["客厅温度"]);
});

test("failed dispatch evidence cannot be presented as a sent request", () => {
  const facts = conversationFacts({
    status: "complete", task_family: "home_control",
    interaction: { dispatches: [{ dispatch_status: "failed", confirmation_status: "unknown" }] },
  });
  expect(facts.evidence).toBe("failed");
});

test("room policy acknowledgement remains separate from physical device confirmation", () => {
  const policy = {
    control_scope: "room_comfort", dispatch_status: "sent", confirmation_status: "unknown",
    policy_observation: { matches_request: true, override_suppressed: false },
  };
  const facts = (dispatches: object[]) => conversationFacts({
    status: "complete", task_family: "home_control", interaction: { dispatches },
  });
  expect(facts([policy]).evidence).toBe("policy_saved");
  expect(facts([{ ...policy, policy_observation: { matches_request: false } }]).evidence).toBe("policy_requested");
  expect(facts([{ ...policy, policy_observation: { matches_request: true, override_suppressed: true } }]).evidence).toBe("policy_suppressed");
  expect(facts([{ ...policy, dispatch_status: "failed" }]).evidence).toBe("failed");
  expect(facts([policy, { dispatch_status: "sent", confirmation_status: "unknown" }]).evidence).toBe("sent");
});

test("device confirmation requires every dispatched operation and preserves a missing confirmation", () => {
  const run = { status: "complete", task_family: "home_control" };
  const confirmed = { dispatch_status: "sent", acceptance_status: "accepted", confirmation_status: "confirmed" };
  const accepted = { dispatch_status: "sent", acceptance_status: "accepted", confirmation_status: "unknown" };
  const facts = (dispatches: object[]) => conversationFacts({ ...run, interaction: { dispatches } });
  expect(facts([confirmed]).evidence).toBe("confirmed");
  expect(facts([accepted]).evidence).toBe("accepted");
  expect(facts([confirmed, { dispatch_status: "sent" }]).evidence).toBe("sent");
  expect(facts([confirmed, { ...accepted, confirmation_status: "not_confirmed" }]).evidence).toBe("not_confirmed");
  expect(facts([confirmed, { dispatch_status: "failed" }]).evidence).toBe("partial");
});

test("dispatch and absent playback never become physical confirmation or zero duration", () => {
  const stages = pipelineStages({
    event_stream: [
      {
        type: "gateway/route_decision",
        offset_ms: 90,
        duration_ms: 10,
        status: "ok",
      },
      { type: "satellite/playback_dispatch", offset_ms: 130, status: "sent" },
    ],
  });
  expect(stages.find((stage) => stage.id === "wake")?.durationMs).toBeNull();
  const playback = stages.find((stage) => stage.id === "playback")!;
  expect(playback.status).toBe("sent");
  expect(playback.durationMs).toBeNull();
  expect(playback.events).toHaveLength(1);
});

test("waterfall preserves independent clocks and instantaneous observations", () => {
  const stages = pipelineStages({
    event_stream: [
      {
        type: "satellite/wake_detected",
        offset_ms: -50,
        duration_ms: 0,
        status: "observed",
      },
      { type: "asr/endpoint_detected", offset_ms: 20, status: "observed" },
      { type: "tts/synth_complete", duration_ms: 300, status: "ok" },
    ],
  });
  expect(stages[0].startMs).toBe(-50);
  expect(stages[0].durationMs).toBe(0);
  expect(stages[1].durationMs).toBeNull();
  expect(stages[3].startMs).toBeNull();
  expect(stages[3].durationMs).toBe(300);
});

test("stale capture evidence cannot animate a live microphone", () => {
  const now = Date.parse("2026-09-13T04:00:00Z");
  const states = { voice_pipeline: { available: true, state: "on" } };
  expect(
    livePipeline(
      states,
      { state: "listening", updated_at: "2026-09-13T03:00:00Z" },
      now,
    ).active,
  ).toBe(false);
  expect(
    livePipeline(
      states,
      { state: "listening", updated_at: "2026-09-13T03:59:59Z" },
      now,
    ).active,
  ).toBe(true);
  expect(
    livePipeline(
      states,
      {
        state: "listening",
        created_at: "2026-09-13T03:59:58Z",
        expires_at: "2026-09-13T03:59:59Z",
      },
      now,
    ).active,
  ).toBe(false);
  expect(
    livePipeline(
      { voice_pipeline: { available: true, state: "unavailable" } },
      {},
      now,
    ).phase,
  ).toBe("unknown");
  expect(
    livePipeline({ voice_pipeline: { available: true, state: "off" } }, {}, now)
      .connected,
  ).toBe(false);
  expect(
    livePipeline(
      { ...states, voice_paused: { state: "on" } },
      { state: "listening", updated_at: "2026-09-13T03:59:59Z" },
      now,
    ).active,
  ).toBe(false);
});

test("gateway clocks and nested dispatch status follow the deployed event format", () => {
  const stages = pipelineStages({
    latency_ms: 800,
    event_stream: [
      {
        event_type: "gateway.received",
        source: "llm-gateway",
        monotonic_ms: 0,
        payload: { status: "ok" },
      },
      {
        event_type: "playback.interrupt.requested",
        source: "llm-gateway",
        monotonic_ms: 600,
        payload: { status: "sent" },
      },
      {
        event_type: "asr.endpoint.detected",
        source: "native",
        monotonic_ms: 987654,
        payload: { endpoint_detected: true },
      },
    ],
  });
  expect(stages[2].startMs).toBe(0);
  expect(stages[2].durationMs).toBe(800);
  expect(stages[4].status).toBe("sent");
  expect(stages[1].startMs).toBeNull();
});

test("PCM preview uses the supplied format and rejects incomplete samples", () => {
  const wave = pcmWave(new Uint8Array([0, 0, 255, 127]), 16000, 1);
  const view = new DataView(wave);
  expect(view.getUint32(24, true)).toBe(16000);
  expect(view.getUint32(40, true)).toBe(4);
  expect(view.getUint16(46, true)).toBe(32767);
  expect(() => pcmWave(new Uint8Array(3), 16000, 1)).toThrow();
});

test("PCM preview preserves the satellite's native 22050 Hz playback rate", () => {
  const wave = pcmWave(new Uint8Array([0, 0, 255, 127]), 22050, 1);
  const view = new DataView(wave);
  expect(view.getUint32(24, true)).toBe(22050);
  expect(view.getUint32(28, true)).toBe(44100);
});
