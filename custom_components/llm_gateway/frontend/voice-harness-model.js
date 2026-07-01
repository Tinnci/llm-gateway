// custom_components/llm_gateway/frontend/voice-harness-model.ts
function runSummary(records, liveRuns) {
  const latencies = records.map((record) => Number(record.latency_ms || 0)).filter((value) => Number.isFinite(value) && value > 0);
  const avgLatency = latencies.length ? Math.round(latencies.reduce((sum, value) => sum + value, 0) / latencies.length) : 0;
  const latestRoute = records[0]?.route;
  const latestRouteKind = latestRoute && typeof latestRoute === "object" ? latestRoute.kind : latestRoute;
  return {
    avgLatency,
    errors: records.filter((record) => record.status === "error" || Array.isArray(record.errors) && record.errors.length > 0).length,
    latestRoute: latestRouteKind || "",
    recorded: records.length,
    running: liveRuns.filter((run) => run.status === "running").length
  };
}
function diagnosticLayerCounts(checks) {
  const layers = new Map;
  for (const check of checks) {
    const layer = String(check.layer || "unknown");
    const current = layers.get(layer) || {
      layer,
      total: 0,
      bad: 0,
      warnings: 0,
      blocked: 0
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
    tone: layer.bad ? "bad" : layer.warnings ? "warning" : layer.blocked ? "muted" : "ok"
  }));
}
function diagnosticCheckDetail(check, repairLabel) {
  const evidence = Array.isArray(check.evidence) ? check.evidence : [];
  const depends = Array.isArray(check.depends_on) ? check.depends_on : [];
  return [
    check.layer ? `layer=${check.layer}` : "",
    depends.length ? `depends=${depends.join(",")}` : "",
    ...evidence.slice(0, 2).map((item) => typeof item === "string" ? item : JSON.stringify(item)),
    check.repair_hint ? `${repairLabel}: ${check.repair_hint}` : ""
  ].filter(Boolean).join(" · ");
}
function satelliteEntityTone(key, state) {
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
function satelliteValue(state, missingLabel) {
  if (!state?.available) {
    return missingLabel;
  }
  return `${state.state}${state.unit ? ` ${state.unit}` : ""}`;
}
function asrEndpointFromSources(...sources) {
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
      source: String(source.source || "native")
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
    source: ""
  };
}
function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function optionalBoolean(value) {
  if (typeof value === "boolean") {
    return value;
  }
  return null;
}
function optionalNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
function optionalString(value) {
  return typeof value === "string" ? value : "";
}
export {
  satelliteValue,
  satelliteEntityTone,
  runSummary,
  diagnosticLayerCounts,
  diagnosticCheckDetail,
  asrEndpointFromSources
};
