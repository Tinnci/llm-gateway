type RunRecord = Record<string, unknown>;
type LiveRun = Record<string, unknown>;

export type RunOutcome = "answered" | "clarification" | "failed" | "cancelled" | "running" | "unknown";

export function runOutcome(record: RunRecord): RunOutcome {
  const route = isRecord(record.route) ? record.route : {};
  const loop = isRecord(record.harness_loop) ? record.harness_loop : isRecord(route.harness_loop) ? route.harness_loop : {};
  const verdict = isRecord(loop.outcome_verdict) ? loop.outcome_verdict : isRecord(route.outcome_verdict) ? route.outcome_verdict : {};
  const status = String(record.terminal_outcome || loop.terminal_outcome || route.terminal_outcome || record.status || "");
  const reason = String(record.failure_stage || loop.stop_reason || verdict.reason || "");
  if (["cancelled", "superseded", "interrupted"].includes(status)) return "cancelled";
  if (["running", "pending"].includes(status)) return "running";
  if (["error", "failed", "stale"].includes(status)) return "failed";
  if (/(ambiguous|missing_requirement|clarif|confirmation)/.test(reason) || ["clarify", "clarification", "confirm", "confirmation"].includes(status) || ["clarify", "clarification"].includes(String(record.outcome || ""))) return "clarification";
  if (status === "blocked" || record.outcome === "not_answered" || verdict.answerable === false || loop.answerable === false) return "failed";
  if (record.outcome === "answered" || verdict.answerable === true || loop.answerable === true || ["complete", "completed", "ok", "success"].includes(status)) return "answered";
  return "unknown";
}

export function runTone(record: RunRecord): "bad" | "ok" | "warning" {
  const outcome = runOutcome(record);
  return outcome === "failed" ? "bad" : outcome === "answered" ? "ok" : "warning";
}

export type RunSummary = {
  avgLatency: number;
  errors: number;
  latestRoute: unknown;
  recorded: number;
  running: number;
};

export type HarnessOverview = {
  averageLatency: number;
  diagnosticIssues: number;
  entryCount: number;
  providerIssues: number;
  recentErrors: number;
  running: number;
};

type HarnessEntryLike = {
  model_providers?: { config_error?: unknown };
  provider_health?: Array<{ failures?: unknown }>;
  traces?: { records?: RunRecord[] };
  voice_runs?: LiveRun[];
};

export type DiagnosticLayerCount = {
  layer: string;
  total: number;
  bad: number;
  warnings: number;
  blocked: number;
  tone: "ok" | "warning" | "bad" | "muted";
};

type SatelliteEntityState = {
  available?: boolean;
  state?: unknown;
  unit?: string;
};

export type AsrEndpointSummary = {
  state: string;
  speechStarted: boolean | null;
  endpointDetected: boolean | null;
  interruptReady: boolean | null;
  terminal: boolean | null;
  reason: string;
  failurePhase: string;
  firstSpeechLatencyMs: number | null;
  endpointLatencyMs: number | null;
  source: string;
};

export function runSummary(records: RunRecord[], liveRuns: LiveRun[]): RunSummary {
  const latencies = records
    .map((record) => Number(record.latency_ms || 0))
    .filter((value) => Number.isFinite(value) && value > 0);
  const avgLatency = latencies.length
    ? Math.round(latencies.reduce((sum, value) => sum + value, 0) / latencies.length)
    : 0;
  const latestRoute = records[0]?.route;
  const latestRouteKind =
    latestRoute && typeof latestRoute === "object"
      ? (latestRoute as Record<string, unknown>).kind
      : latestRoute;
  return {
    avgLatency,
    errors: records.filter((record) => runOutcome(record) === "failed").length,
    latestRoute: latestRouteKind || "",
    recorded: records.length,
    running: liveRuns.filter((run) => run.status === "running").length,
  };
}

export function harnessOverview(
  entries: HarnessEntryLike[],
  diagnosticChecks: Record<string, unknown>[]
): HarnessOverview {
  const records = entries.flatMap((entry) => entry.traces?.records || []);
  const liveRuns = entries.flatMap((entry) => entry.voice_runs || []);
  const summary = runSummary(records, liveRuns);
  const providerIssues = entries.reduce((count, entry) => {
    const configIssue = entry.model_providers?.config_error ? 1 : 0;
    const healthIssues = (entry.provider_health || []).filter(
      (provider) => Number(provider.failures || 0) > 0
    ).length;
    return count + configIssue + healthIssues;
  }, 0);
  const diagnosticIssues = diagnosticChecks.filter(
    (check) => check.status === "error" || check.status === "warning"
  ).length;
  return {
    averageLatency: summary.avgLatency,
    diagnosticIssues,
    entryCount: entries.length,
    providerIssues,
    recentErrors: summary.errors,
    running: summary.running,
  };
}

export function diagnosticLayerCounts(
  checks: Record<string, unknown>[]
): DiagnosticLayerCount[] {
  const layers = new Map<string, Omit<DiagnosticLayerCount, "tone">>();
  for (const check of checks) {
    const layer = String(check.layer || "unknown");
    const current = layers.get(layer) || {
      layer,
      total: 0,
      bad: 0,
      warnings: 0,
      blocked: 0,
    };
    current.total += 1;
    if (check.status === "error") {
      current.bad += 1;
    } else if (check.status === "warning") {
      current.warnings += 1;
    } else if (check.status === "blocked") {
      current.blocked += 1;
    }
    layers.set(layer, current);
  }
  return [...layers.values()].map((layer) => ({
    ...layer,
    tone: layer.bad ? "bad" : layer.warnings ? "warning" : layer.blocked ? "muted" : "ok",
  }));
}

export function diagnosticCheckDetail(
  check: Record<string, unknown>,
  repairLabel: string
): string {
  const evidence = Array.isArray(check.evidence) ? check.evidence : [];
  const depends = Array.isArray(check.depends_on) ? check.depends_on : [];
  return [
    check.layer ? `layer=${check.layer}` : "",
    depends.length ? `depends=${depends.join(",")}` : "",
    ...evidence
      .slice(0, 2)
      .map((item) => (typeof item === "string" ? item : JSON.stringify(item))),
    check.repair_hint ? `${repairLabel}: ${check.repair_hint}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

export function satelliteEntityTone(
  key: string,
  state: SatelliteEntityState | undefined
): "ok" | "warning" | "bad" {
  if (!state?.available) {
    return "bad";
  }
  const value = String(state.state || "").toLowerCase();
  if (key === "voice_paused" || key === "pause_requested") {
    return ["on", "true", "paused"].includes(value) ? "warning" : "ok";
  }
  if (key === "voice_pipeline" || key === "display_awake") {
    return ["on", "true", "ready", "ok"].includes(value) ? "ok" : "warning";
  }
  return "ok";
}

export function satelliteValue(
  state: SatelliteEntityState | undefined,
  missingLabel: string
): string {
  if (!state?.available) {
    return missingLabel;
  }
  return `${state.state}${state.unit ? ` ${state.unit}` : ""}`;
}

export function asrEndpointFromSources(
  ...sources: unknown[]
): AsrEndpointSummary {
  for (const source of sources) {
    if (!isRecord(source)) {
      continue;
    }
    const state = String(source.state || "");
    if (!state) {
      continue;
    }
    return {
      state,
      speechStarted: optionalBoolean(source.speech_started),
      endpointDetected: optionalBoolean(source.endpoint_detected),
      interruptReady: optionalBoolean(source.interrupt_ready),
      terminal: optionalBoolean(source.terminal),
      reason: optionalString(source.reason),
      failurePhase: optionalString(source.failure_phase),
      firstSpeechLatencyMs: optionalNumber(source.first_speech_latency_ms),
      endpointLatencyMs: optionalNumber(source.endpoint_latency_ms),
      source: String(source.source || "native"),
    };
  }
  return {
    state: "",
    speechStarted: null,
    endpointDetected: null,
    interruptReady: null,
    terminal: null,
    reason: "",
    failurePhase: "",
    firstSpeechLatencyMs: null,
    endpointLatencyMs: null,
    source: "",
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function optionalBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") {
    return value;
  }
  return null;
}

function optionalNumber(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function optionalString(value: unknown): string {
  return typeof value === "string" ? value : "";
}
