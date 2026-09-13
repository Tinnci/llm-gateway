import { runOutcome } from "./voice-harness-model";

export type EvidenceRecord = Readonly<Record<string, unknown>>;
export const object = (value: unknown): EvidenceRecord =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as EvidenceRecord)
    : {};
export const records = (value: unknown): EvidenceRecord[] =>
  Array.isArray(value) ? value.map(object) : [];
export const measurement = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;
export const idOf = (value: EvidenceRecord): string =>
  String(value.run_id || value.id || "");
export const speechOf = (value: EvidenceRecord): string =>
  String(
    object(value.speech).final ||
      value.final_speech_text ||
      value.assistant_text ||
      "",
  );

function isLiveRun(record: EvidenceRecord): boolean {
  return object(record.lineage).mode !== "dry_run" &&
    record.terminal_outcome !== "dry_run" && record.outcome !== "dry_run" &&
    object(record.route).kind !== "replay";
}

export function latestConversation(input: readonly EvidenceRecord[]): EvidenceRecord | null {
  return [...input].filter(isLiveRun).sort((a, b) => {
    const time = (run: EvidenceRecord) => Date.parse(String(run.created_at || run.started_at || "")) || 0;
    return time(b) - time(a);
  })[0] || null;
}

export function conversationFacts(run: EvidenceRecord) {
  const facts = object(run.interaction);
  const observations = records(facts.observations);
  const dispatches = records(facts.dispatches);
  const sent = dispatches.filter((dispatch) => dispatch.dispatch_status === "sent");
  const failed = dispatches.some((dispatch) => dispatch.dispatch_status === "failed");
  const allSent = sent.length > 0 && sent.length === dispatches.length;
  const roomPolicy = allSent && sent.every((dispatch) => dispatch.control_scope === "room_comfort");
  const family = String(run.task_family || object(run.route_decision).task_family || "");
  const action = ["home_control", "volume_control"].includes(family) || dispatches.length > 0;
  const outcome = runOutcome(run);
  const terminal = run.terminal_outcome || object(object(run.route).harness_loop).terminal_outcome || object(run.route).terminal_outcome || run.status;
  const evidence = terminal === "partial" || (failed && sent.length > 0) ? "partial"
    : outcome === "running" ? "running"
    : outcome === "clarification" ? "clarification"
    : outcome === "failed" || failed ? "failed"
    : outcome === "cancelled" ? "cancelled"
    : roomPolicy ? sent.every((dispatch) => object(dispatch.policy_observation).matches_request === true)
      ? sent.some((dispatch) => object(dispatch.policy_observation).override_suppressed === true) ? "policy_suppressed" : "policy_saved"
      : "policy_requested"
    : action ? sent.some((dispatch) => dispatch.confirmation_status === "not_confirmed") ? "not_confirmed"
      : allSent && sent.every((dispatch) => dispatch.confirmation_status === "confirmed") ? "confirmed"
      : allSent && sent.every((dispatch) => dispatch.acceptance_status === "accepted") ? "accepted"
      : sent.length ? "sent" : "unconfirmed"
    : observations.some((observation) => observation.answerable === true) ? "observed"
    : outcome === "answered" ? "reply" : "unknown";
  return {
    intent: String(facts.intent_text || run.user_text || object(run.input).text || ""),
    reply: speechOf(run),
    evidence,
    sources: [...new Set(observations.filter((observation) => observation.answerable === true)
      .flatMap((observation) => records(observation.entities))
      .map((entity) => String(entity.name || entity.entity_id || "")).filter(Boolean))],
  };
}

export function supportsActionReplay(record: EvidenceRecord): boolean {
  const decision = object(record.route_decision);
  return (
    decision.route === "local_action" &&
    decision.next_action === "execute_local" &&
    object(record.lineage).mode !== "dry_run"
  );
}

export function observedMetrics(input: readonly EvidenceRecord[]) {
  const live = input.filter(isLiveRun);
  const settled = live.filter((run) =>
    ["answered", "failed", "clarification", "cancelled"].includes(
      runOutcome(run),
    ),
  );
  const timed = settled
    .map((run) => measurement(run.latency_ms))
    .filter((value): value is number => value !== null && value >= 0);
  const sorted = [...timed].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  const ratio = (count: number) =>
    settled.length ? (100 * count) / settled.length : null;
  return {
    count: settled.length,
    medianMs: sorted.length
      ? (sorted[middle] + sorted[Math.floor((sorted.length - 1) / 2)]) / 2
      : null,
    successRate: ratio(
      settled.filter((run) => runOutcome(run) === "answered").length,
    ),
    errorRate: ratio(
      settled.filter((run) => runOutcome(run) === "failed").length,
    ),
    latencies: timed.reverse(),
    outcomes: [...settled]
      .reverse()
      .map((run) => (runOutcome(run) === "answered" ? 1 : 0)),
    errors: [...settled]
      .reverse()
      .map((run) => (runOutcome(run) === "failed" ? 1 : 0)),
  };
}

export const stageIds = [
  "wake",
  "asr",
  "llm",
  "tts",
  "playback",
  "follow_up",
] as const;
export type PipelineStageId = (typeof stageIds)[number];
export type PipelineStage = {
  id: PipelineStageId;
  startMs: number | null;
  durationMs: number | null;
  status: string;
  events: readonly EvidenceRecord[];
};

function eventStage(event: EvidenceRecord): PipelineStageId | null {
  const name = String(
    event.type || event.event_type || event.stage || "",
  ).toLowerCase();
  if (/follow[_./-]?up/.test(name)) return "follow_up";
  if (/wake/.test(name)) return "wake";
  if (/playback|player[._/]|audio[._/]play/.test(name)) return "playback";
  if (/^asr[./]|^stt[./]|recognition|transcript/.test(name)) return "asr";
  if (/^tts[./]|synth/.test(name)) return "tts";
  if (
    /^gateway[./]|^llm[./]|model|provider|route_decision|tool|completion/.test(
      name,
    )
  )
    return "llm";
  return null;
}

function eventStart(event: EvidenceRecord): number | null {
  return measurement(
    event.offset_ms ??
      event.start_ms ??
      event.t_ms ??
      (event.source === "llm-gateway" ? event.monotonic_ms : null),
  );
}

export function pipelineStages(run: EvidenceRecord): PipelineStage[] {
  const events = records(run.event_stream);
  const source = events.length
    ? events
    : records(run.timeline_spans).length
      ? records(run.timeline_spans)
      : records(run.timeline);
  return stageIds.map((id) => {
    const matching = source.filter((event) => eventStage(event) === id);
    const starts = matching
      .map(eventStart)
      .filter((n): n is number => n !== null);
    // Cross-producer monotonic clocks cannot be subtracted. Use recorded spans only.
    const spans = matching.flatMap((event) => {
      const start = eventStart(event);
      const duration = measurement(
        event.duration_ms ?? object(event.payload).duration_ms,
      );
      return duration === null || duration < 0 ? [] : [{ start, duration }];
    });
    const aligned = spans.filter(
      (span): span is { start: number; duration: number } =>
        span.start !== null,
    );
    let durationMs =
      aligned.length && aligned.length === spans.length
        ? Math.max(...aligned.map((span) => span.start + span.duration)) -
          Math.min(...aligned.map((span) => span.start))
        : spans.length === 1
          ? spans[0].duration
          : null;
    if (
      durationMs === null &&
      id === "llm" &&
      matching.some((event) => event.source === "llm-gateway")
    )
      durationMs = measurement(run.latency_ms);
    const statuses = matching.map((event) =>
      String(event.status || object(event.payload).status || "observed"),
    );
    const failure = statuses.find((status) =>
      ["failed", "error", "unsupported", "not_confirmed"].includes(status),
    );
    return {
      id,
      startMs: starts.length ? Math.min(...starts) : null,
      durationMs,
      status: failure || statuses.at(-1) || "missing",
      events: matching,
    };
  });
}

export function livePipeline(
  states: EvidenceRecord,
  display: EvidenceRecord,
  now = Date.now(),
) {
  const pipeline = object(states.voice_pipeline);
  const available =
    pipeline.available === true &&
    ["on", "ready", "ok"].includes(String(pipeline.state));
  const paused = ["on", "paused"].includes(
    String(object(states.voice_paused).state),
  );
  const timestamp =
    display.updated_at || display.created_at || display.timestamp;
  const age = typeof timestamp === "string" ? now - Date.parse(timestamp) : NaN;
  const expiry =
    typeof display.expires_at === "string"
      ? Date.parse(display.expires_at)
      : NaN;
  const fresh =
    Number.isFinite(age) &&
    age >= 0 &&
    age <= 30000 &&
    (!Number.isFinite(expiry) || expiry > now);
  const state = String(display.state || display.phase || "");
  const active =
    available &&
    !paused &&
    fresh &&
    [
      "listening",
      "recording",
      "stt",
      "thinking",
      "processing",
      "searching",
      "speaking",
      "tts",
      "playing",
    ].includes(state);
  return {
    active,
    connected: available,
    phase: paused
      ? "paused"
      : active
        ? state
        : available
          ? "standby"
          : pipeline.state === "off"
            ? "offline"
            : "unknown",
    ageMs: Number.isFinite(age) ? age : null,
  };
}

export function sparkline(
  values: readonly number[],
  width = 180,
  height = 42,
): string {
  if (values.length < 2) return "";
  const min = Math.min(...values);
  const spread = Math.max(...values) - min;
  return values
    .map(
      (value, index) =>
        ((index / (values.length - 1)) * width).toFixed(1) +
        "," +
        (
          height -
          (spread ? (value - min) / spread : 0.5) * (height - 8) -
          4
        ).toFixed(1),
    )
    .join(" ");
}

export const pcmSampleRates: readonly number[] = [8000, 16000, 22050, 24000, 44100, 48000];

export function pcmWave(
  pcm: Uint8Array,
  sampleRate: number,
  channels: number,
): ArrayBuffer {
  if (
    !pcmSampleRates.includes(sampleRate) ||
    ![1, 2].includes(channels) ||
    pcm.byteLength === 0 ||
    pcm.byteLength % (channels * 2)
  ) {
    throw new Error(
      "Use complete 16-bit little-endian PCM samples with the selected rate and channels.",
    );
  }
  const result = new ArrayBuffer(44 + pcm.byteLength);
  const bytes = new Uint8Array(result);
  const view = new DataView(result);
  for (const [offset, text] of [
    [0, "RIFF"],
    [8, "WAVE"],
    [12, "fmt "],
    [36, "data"],
  ] as const)
    bytes.set(new TextEncoder().encode(text), offset);
  view.setUint32(4, 36 + pcm.byteLength, true);
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * channels * 2, true);
  view.setUint16(32, channels * 2, true);
  view.setUint16(34, 16, true);
  view.setUint32(40, pcm.byteLength, true);
  bytes.set(pcm, 44);
  return result;
}
