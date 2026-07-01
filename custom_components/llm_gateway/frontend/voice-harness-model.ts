type RunRecord = Record<string, unknown>;
type LiveRun = Record<string, unknown>;

export type RunSummary = {
  avgLatency: number;
  errors: number;
  latestRoute: unknown;
  recorded: number;
  running: number;
};

export type DiagnosticLayerCount = {
  layer: string;
  total: number;
  bad: number;
  warnings: number;
  tone: "ok" | "warning" | "bad";
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
    errors: records.filter(
      (record) =>
        record.status === "error" ||
        (Array.isArray(record.errors) && record.errors.length > 0)
    ).length,
    latestRoute: latestRouteKind || "",
    recorded: records.length,
    running: liveRuns.filter((run) => run.status === "running").length,
  };
}

export function diagnosticLayerCounts(
  checks: Record<string, unknown>[]
): DiagnosticLayerCount[] {
  const layers = new Map<string, Omit<DiagnosticLayerCount, "tone">>();
  for (const check of checks) {
    const layer = String(check.layer || "unknown");
    const current = layers.get(layer) || { layer, total: 0, bad: 0, warnings: 0 };
    current.total += 1;
    if (check.status === "error") {
      current.bad += 1;
    } else if (check.status === "warning") {
      current.warnings += 1;
    }
    layers.set(layer, current);
  }
  return [...layers.values()].map((layer) => ({
    ...layer,
    tone: layer.bad ? "bad" : layer.warnings ? "warning" : "ok",
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
