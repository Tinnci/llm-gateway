// node_modules/valibot/dist/index.mjs
var store$4;
var DEFAULT_CONFIG = {
  lang: undefined,
  message: undefined,
  abortEarly: undefined,
  abortPipeEarly: undefined
};
function getGlobalConfig(config$1) {
  if (!config$1 && !store$4)
    return DEFAULT_CONFIG;
  return {
    lang: config$1?.lang ?? store$4?.lang,
    message: config$1?.message,
    abortEarly: config$1?.abortEarly ?? store$4?.abortEarly,
    abortPipeEarly: config$1?.abortPipeEarly ?? store$4?.abortPipeEarly
  };
}
var store$3;
function getGlobalMessage(lang) {
  return store$3?.get(lang);
}
var store$2;
function getSchemaMessage(lang) {
  return store$2?.get(lang);
}
var store$1;
function getSpecificMessage(reference, lang) {
  return store$1?.get(reference)?.get(lang);
}
function _stringify(input) {
  const type = typeof input;
  if (type === "string")
    return `"${input}"`;
  if (type === "number" || type === "bigint" || type === "boolean")
    return `${input}`;
  if (type === "object" || type === "function")
    return (input && Object.getPrototypeOf(input)?.constructor?.name) ?? "null";
  return type;
}
function _addIssue(context, label, dataset, config$1, other) {
  const input = other && "input" in other ? other.input : dataset.value;
  const expected = other?.expected ?? context.expects ?? null;
  const received = other?.received ?? /* @__PURE__ */ _stringify(input);
  const issue = {
    kind: context.kind,
    type: context.type,
    input,
    expected,
    received,
    message: `Invalid ${label}: ${expected ? `Expected ${expected} but r` : "R"}eceived ${received}`,
    requirement: context.requirement,
    path: other?.path,
    issues: other?.issues,
    lang: config$1.lang,
    abortEarly: config$1.abortEarly,
    abortPipeEarly: config$1.abortPipeEarly
  };
  const isSchema = context.kind === "schema";
  const message$1 = other?.message ?? context.message ?? /* @__PURE__ */ getSpecificMessage(context.reference, issue.lang) ?? (isSchema ? /* @__PURE__ */ getSchemaMessage(issue.lang) : null) ?? config$1.message ?? /* @__PURE__ */ getGlobalMessage(issue.lang);
  if (message$1 !== undefined)
    issue.message = typeof message$1 === "function" ? message$1(issue) : message$1;
  if (isSchema)
    dataset.typed = false;
  if (dataset.issues)
    dataset.issues.push(issue);
  else
    dataset.issues = [issue];
}
var _standardCache = /* @__PURE__ */ new WeakMap;
function _getStandardProps(context) {
  let cached = _standardCache.get(context);
  if (!cached) {
    cached = {
      version: 1,
      vendor: "valibot",
      validate(value$1) {
        return context["~run"]({ value: value$1 }, /* @__PURE__ */ getGlobalConfig());
      }
    };
    _standardCache.set(context, cached);
  }
  return cached;
}
function _isValidObjectKey(object$1, key) {
  return Object.prototype.hasOwnProperty.call(object$1, key) && key !== "__proto__" && key !== "prototype" && key !== "constructor";
}
function getFallback(schema, dataset, config$1) {
  return typeof schema.fallback === "function" ? schema.fallback(dataset, config$1) : schema.fallback;
}
function getDefault(schema, dataset, config$1) {
  return typeof schema.default === "function" ? schema.default(dataset, config$1) : schema.default;
}
function array(item, message$1) {
  return {
    kind: "schema",
    type: "array",
    reference: array,
    expects: "Array",
    async: false,
    item,
    message: message$1,
    get "~standard"() {
      return /* @__PURE__ */ _getStandardProps(this);
    },
    "~run"(dataset, config$1) {
      const input = dataset.value;
      if (Array.isArray(input)) {
        dataset.typed = true;
        dataset.value = [];
        for (let key = 0;key < input.length; key++) {
          const value$1 = input[key];
          const itemDataset = this.item["~run"]({ value: value$1 }, config$1);
          if (itemDataset.issues) {
            const pathItem = {
              type: "array",
              origin: "value",
              input,
              key,
              value: value$1
            };
            for (const issue of itemDataset.issues) {
              if (issue.path)
                issue.path.unshift(pathItem);
              else
                issue.path = [pathItem];
              dataset.issues?.push(issue);
            }
            if (!dataset.issues)
              dataset.issues = itemDataset.issues;
            if (config$1.abortEarly) {
              dataset.typed = false;
              break;
            }
          }
          if (!itemDataset.typed)
            dataset.typed = false;
          dataset.value.push(itemDataset.value);
        }
      } else
        _addIssue(this, "type", dataset, config$1);
      return dataset;
    }
  };
}
function looseObject(entries$1, message$1) {
  return {
    kind: "schema",
    type: "loose_object",
    reference: looseObject,
    expects: "Object",
    async: false,
    entries: entries$1,
    message: message$1,
    get "~standard"() {
      return /* @__PURE__ */ _getStandardProps(this);
    },
    "~run"(dataset, config$1) {
      const input = dataset.value;
      if (input && typeof input === "object") {
        dataset.typed = true;
        dataset.value = {};
        for (const key in this.entries) {
          const valueSchema = this.entries[key];
          if (key in input || (valueSchema.type === "exact_optional" || valueSchema.type === "optional" || valueSchema.type === "nullish") && valueSchema.default !== undefined) {
            const value$1 = key in input ? input[key] : /* @__PURE__ */ getDefault(valueSchema);
            const valueDataset = valueSchema["~run"]({ value: value$1 }, config$1);
            if (valueDataset.issues) {
              const pathItem = {
                type: "object",
                origin: "value",
                input,
                key,
                value: value$1
              };
              for (const issue of valueDataset.issues) {
                if (issue.path)
                  issue.path.unshift(pathItem);
                else
                  issue.path = [pathItem];
                dataset.issues?.push(issue);
              }
              if (!dataset.issues)
                dataset.issues = valueDataset.issues;
              if (config$1.abortEarly) {
                dataset.typed = false;
                break;
              }
            }
            if (!valueDataset.typed)
              dataset.typed = false;
            dataset.value[key] = valueDataset.value;
          } else if (valueSchema.fallback !== undefined)
            dataset.value[key] = /* @__PURE__ */ getFallback(valueSchema);
          else if (valueSchema.type !== "exact_optional" && valueSchema.type !== "optional" && valueSchema.type !== "nullish") {
            _addIssue(this, "key", dataset, config$1, {
              input: undefined,
              expected: `"${key}"`,
              path: [{
                type: "object",
                origin: "key",
                input,
                key,
                value: input[key]
              }]
            });
            if (config$1.abortEarly)
              break;
          }
        }
        if (!dataset.issues || !config$1.abortEarly) {
          for (const key in input)
            if (/* @__PURE__ */ _isValidObjectKey(input, key) && !(key in this.entries))
              dataset.value[key] = input[key];
        }
      } else
        _addIssue(this, "type", dataset, config$1);
      return dataset;
    }
  };
}
function number(message$1) {
  return {
    kind: "schema",
    type: "number",
    reference: number,
    expects: "number",
    async: false,
    message: message$1,
    get "~standard"() {
      return /* @__PURE__ */ _getStandardProps(this);
    },
    "~run"(dataset, config$1) {
      if (typeof dataset.value === "number" && !isNaN(dataset.value))
        dataset.typed = true;
      else
        _addIssue(this, "type", dataset, config$1);
      return dataset;
    }
  };
}
function string(message$1) {
  return {
    kind: "schema",
    type: "string",
    reference: string,
    expects: "string",
    async: false,
    message: message$1,
    get "~standard"() {
      return /* @__PURE__ */ _getStandardProps(this);
    },
    "~run"(dataset, config$1) {
      if (typeof dataset.value === "string")
        dataset.typed = true;
      else
        _addIssue(this, "type", dataset, config$1);
      return dataset;
    }
  };
}
function safeParse(schema, input, config$1) {
  const dataset = schema["~run"]({ value: input }, /* @__PURE__ */ getGlobalConfig(config$1));
  return {
    typed: dataset.typed,
    success: !dataset.issues,
    output: dataset.value,
    issues: dataset.issues
  };
}

// custom_components/llm_gateway/frontend/voice-harness-api.ts
var rangeSchema = looseObject({ min: number(), max: number() });
var harnessStatusSchema = looseObject({
  entries: array(looseObject({
    entry_id: string(),
    state: string(),
    title: string()
  })),
  editable: looseObject({
    max_tokens: rangeSchema,
    routing_modes: array(string()),
    timeouts: rangeSchema,
    trace_max_runs: rangeSchema,
    trace_retention_hours: rangeSchema
  })
});
function parseHarnessStatus(input) {
  const result = safeParse(harnessStatusSchema, input);
  if (result.success) {
    return result.output;
  }
  const fields = result.issues.map((issue) => issue.path?.map((item) => String(item.key)).join(".")).filter(Boolean);
  const detail = fields.length ? `: ${[...new Set(fields)].join(", ")}` : "";
  throw new Error(`Invalid Voice Harness status response${detail}`);
}
async function requestHarnessJson(hass, method, path, payload) {
  if (hass?.callApi) {
    try {
      return await hass.callApi(method, path, payload);
    } catch (error) {
      if (!isRecord(error) || !isRecord(error.body))
        throw error;
      const body = error.body;
      throw Object.assign(new Error(typeof body.message === "string" ? body.message : String(error.error || "Home Assistant request failed")), {
        code: typeof body.code === "string" ? body.code : ""
      });
    }
  }
  const response = await fetch(`/api/${path}`, {
    method,
    credentials: "same-origin",
    headers: payload === undefined ? undefined : { "Content-Type": "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload)
  });
  if (response.ok) {
    return await response.json();
  }
  let message = `${response.status} ${response.statusText}`;
  let code = "";
  try {
    const body = await response.json();
    if (isRecord(body)) {
      message = typeof body.message === "string" ? body.message : message;
      code = typeof body.code === "string" ? body.code : "";
    }
  } catch {}
  throw Object.assign(new Error(message), { code });
}
function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// custom_components/llm_gateway/frontend/voice-harness-model.ts
function runOutcome(record) {
  const route = isRecord2(record.route) ? record.route : {};
  const loop = isRecord2(record.harness_loop) ? record.harness_loop : isRecord2(route.harness_loop) ? route.harness_loop : {};
  const verdict = isRecord2(loop.outcome_verdict) ? loop.outcome_verdict : isRecord2(route.outcome_verdict) ? route.outcome_verdict : {};
  const status = String(record.terminal_outcome || loop.terminal_outcome || route.terminal_outcome || record.status || "");
  const reason = String(record.failure_stage || loop.stop_reason || verdict.reason || "");
  if (["cancelled", "superseded", "interrupted"].includes(status))
    return "cancelled";
  if (["running", "pending"].includes(status))
    return "running";
  if (["error", "failed", "stale", "partial"].includes(status))
    return "failed";
  if (/(ambiguous|missing_requirement|clarif|confirmation)/.test(reason) || ["clarify", "clarification", "confirm", "confirmation"].includes(status) || ["clarify", "clarification"].includes(String(record.outcome || "")))
    return "clarification";
  if (status === "blocked" || record.outcome === "not_answered" || verdict.answerable === false || loop.answerable === false)
    return "failed";
  if (record.outcome === "answered" || verdict.answerable === true || loop.answerable === true || ["complete", "completed", "ok", "success"].includes(status))
    return "answered";
  return "unknown";
}
function runTone(record) {
  const outcome = runOutcome(record);
  return outcome === "failed" ? "bad" : outcome === "answered" ? "ok" : "warning";
}
function runSummary(records, liveRuns) {
  const latencies = records.map((record) => Number(record.latency_ms || 0)).filter((value) => Number.isFinite(value) && value > 0);
  const avgLatency = latencies.length ? Math.round(latencies.reduce((sum, value) => sum + value, 0) / latencies.length) : 0;
  const latestRoute = records[0]?.route;
  const latestRouteKind = latestRoute && typeof latestRoute === "object" ? latestRoute.kind : latestRoute;
  return {
    avgLatency,
    errors: records.filter((record) => runOutcome(record) === "failed").length,
    latestRoute: latestRouteKind || "",
    recorded: records.length,
    running: liveRuns.filter((run) => run.status === "running").length
  };
}
function harnessOverview(entries, diagnosticChecks) {
  const records = entries.flatMap((entry) => entry.traces?.records || []);
  const liveRuns = entries.flatMap((entry) => entry.voice_runs || []);
  const summary = runSummary(records, liveRuns);
  const providerIssues = entries.reduce((count, entry) => {
    const configIssue = entry.model_providers?.config_error ? 1 : 0;
    const healthIssues = (entry.provider_health || []).filter((provider) => Number(provider.failures || 0) > 0).length;
    return count + configIssue + healthIssues;
  }, 0);
  const diagnosticIssues = diagnosticChecks.filter((check) => check.status === "error" || check.status === "warning").length;
  return {
    averageLatency: summary.avgLatency,
    diagnosticIssues,
    entryCount: entries.length,
    providerIssues,
    recentErrors: summary.errors,
    running: summary.running
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
    if (!isRecord2(source)) {
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
function isRecord2(value) {
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

// node_modules/@lit/reactive-element/css-tag.js
var t = globalThis;
var e = t.ShadowRoot && (t.ShadyCSS === undefined || t.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype;
var s = Symbol();
var o = new WeakMap;

class n {
  constructor(t2, e2, o2) {
    if (this._$cssResult$ = true, o2 !== s)
      throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t2, this.t = e2;
  }
  get styleSheet() {
    let t2 = this.o;
    const s2 = this.t;
    if (e && t2 === undefined) {
      const e2 = s2 !== undefined && s2.length === 1;
      e2 && (t2 = o.get(s2)), t2 === undefined && ((this.o = t2 = new CSSStyleSheet).replaceSync(this.cssText), e2 && o.set(s2, t2));
    }
    return t2;
  }
  toString() {
    return this.cssText;
  }
}
var r = (t2) => new n(typeof t2 == "string" ? t2 : t2 + "", undefined, s);
var i = (t2, ...e2) => {
  const o2 = t2.length === 1 ? t2[0] : e2.reduce((e3, s2, o3) => e3 + ((t3) => {
    if (t3._$cssResult$ === true)
      return t3.cssText;
    if (typeof t3 == "number")
      return t3;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + t3 + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s2) + t2[o3 + 1], t2[0]);
  return new n(o2, t2, s);
};
var S = (s2, o2) => {
  if (e)
    s2.adoptedStyleSheets = o2.map((t2) => t2 instanceof CSSStyleSheet ? t2 : t2.styleSheet);
  else
    for (const e2 of o2) {
      const o3 = document.createElement("style"), n2 = t.litNonce;
      n2 !== undefined && o3.setAttribute("nonce", n2), o3.textContent = e2.cssText, s2.appendChild(o3);
    }
};
var c = e ? (t2) => t2 : (t2) => t2 instanceof CSSStyleSheet ? ((t3) => {
  let e2 = "";
  for (const s2 of t3.cssRules)
    e2 += s2.cssText;
  return r(e2);
})(t2) : t2;

// node_modules/@lit/reactive-element/reactive-element.js
var { is: i2, defineProperty: e2, getOwnPropertyDescriptor: h, getOwnPropertyNames: r2, getOwnPropertySymbols: o2, getPrototypeOf: n2 } = Object;
var a = globalThis;
var c2 = a.trustedTypes;
var l = c2 ? c2.emptyScript : "";
var p = a.reactiveElementPolyfillSupport;
var d = (t2, s2) => t2;
var u = { toAttribute(t2, s2) {
  switch (s2) {
    case Boolean:
      t2 = t2 ? l : null;
      break;
    case Object:
    case Array:
      t2 = t2 == null ? t2 : JSON.stringify(t2);
  }
  return t2;
}, fromAttribute(t2, s2) {
  let i3 = t2;
  switch (s2) {
    case Boolean:
      i3 = t2 !== null;
      break;
    case Number:
      i3 = t2 === null ? null : Number(t2);
      break;
    case Object:
    case Array:
      try {
        i3 = JSON.parse(t2);
      } catch (t3) {
        i3 = null;
      }
  }
  return i3;
} };
var f = (t2, s2) => !i2(t2, s2);
var b = { attribute: true, type: String, converter: u, reflect: false, useDefault: false, hasChanged: f };
Symbol.metadata ??= Symbol("metadata"), a.litPropertyMetadata ??= new WeakMap;

class y extends HTMLElement {
  static addInitializer(t2) {
    this._$Ei(), (this.l ??= []).push(t2);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t2, s2 = b) {
    if (s2.state && (s2.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t2) && ((s2 = Object.create(s2)).wrapped = true), this.elementProperties.set(t2, s2), !s2.noAccessor) {
      const i3 = Symbol(), h2 = this.getPropertyDescriptor(t2, i3, s2);
      h2 !== undefined && e2(this.prototype, t2, h2);
    }
  }
  static getPropertyDescriptor(t2, s2, i3) {
    const { get: e3, set: r3 } = h(this.prototype, t2) ?? { get() {
      return this[s2];
    }, set(t3) {
      this[s2] = t3;
    } };
    return { get: e3, set(s3) {
      const h2 = e3?.call(this);
      r3?.call(this, s3), this.requestUpdate(t2, h2, i3);
    }, configurable: true, enumerable: true };
  }
  static getPropertyOptions(t2) {
    return this.elementProperties.get(t2) ?? b;
  }
  static _$Ei() {
    if (this.hasOwnProperty(d("elementProperties")))
      return;
    const t2 = n2(this);
    t2.finalize(), t2.l !== undefined && (this.l = [...t2.l]), this.elementProperties = new Map(t2.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(d("finalized")))
      return;
    if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d("properties"))) {
      const t3 = this.properties, s2 = [...r2(t3), ...o2(t3)];
      for (const i3 of s2)
        this.createProperty(i3, t3[i3]);
    }
    const t2 = this[Symbol.metadata];
    if (t2 !== null) {
      const s2 = litPropertyMetadata.get(t2);
      if (s2 !== undefined)
        for (const [t3, i3] of s2)
          this.elementProperties.set(t3, i3);
    }
    this._$Eh = new Map;
    for (const [t3, s2] of this.elementProperties) {
      const i3 = this._$Eu(t3, s2);
      i3 !== undefined && this._$Eh.set(i3, t3);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(s2) {
    const i3 = [];
    if (Array.isArray(s2)) {
      const e3 = new Set(s2.flat(1 / 0).reverse());
      for (const s3 of e3)
        i3.unshift(c(s3));
    } else
      s2 !== undefined && i3.push(c(s2));
    return i3;
  }
  static _$Eu(t2, s2) {
    const i3 = s2.attribute;
    return i3 === false ? undefined : typeof i3 == "string" ? i3 : typeof t2 == "string" ? t2.toLowerCase() : undefined;
  }
  constructor() {
    super(), this._$Ep = undefined, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise((t2) => this.enableUpdating = t2), this._$AL = new Map, this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((t2) => t2(this));
  }
  addController(t2) {
    (this._$EO ??= new Set).add(t2), this.renderRoot !== undefined && this.isConnected && t2.hostConnected?.();
  }
  removeController(t2) {
    this._$EO?.delete(t2);
  }
  _$E_() {
    const t2 = new Map, s2 = this.constructor.elementProperties;
    for (const i3 of s2.keys())
      this.hasOwnProperty(i3) && (t2.set(i3, this[i3]), delete this[i3]);
    t2.size > 0 && (this._$Ep = t2);
  }
  createRenderRoot() {
    const t2 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return S(t2, this.constructor.elementStyles), t2;
  }
  connectedCallback() {
    this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(true), this._$EO?.forEach((t2) => t2.hostConnected?.());
  }
  enableUpdating(t2) {}
  disconnectedCallback() {
    this._$EO?.forEach((t2) => t2.hostDisconnected?.());
  }
  attributeChangedCallback(t2, s2, i3) {
    this._$AK(t2, i3);
  }
  _$ET(t2, s2) {
    const i3 = this.constructor.elementProperties.get(t2), e3 = this.constructor._$Eu(t2, i3);
    if (e3 !== undefined && i3.reflect === true) {
      const h2 = (i3.converter?.toAttribute !== undefined ? i3.converter : u).toAttribute(s2, i3.type);
      this._$Em = t2, h2 == null ? this.removeAttribute(e3) : this.setAttribute(e3, h2), this._$Em = null;
    }
  }
  _$AK(t2, s2) {
    const i3 = this.constructor, e3 = i3._$Eh.get(t2);
    if (e3 !== undefined && this._$Em !== e3) {
      const t3 = i3.getPropertyOptions(e3), h2 = typeof t3.converter == "function" ? { fromAttribute: t3.converter } : t3.converter?.fromAttribute !== undefined ? t3.converter : u;
      this._$Em = e3;
      const r3 = h2.fromAttribute(s2, t3.type);
      this[e3] = r3 ?? this._$Ej?.get(e3) ?? r3, this._$Em = null;
    }
  }
  requestUpdate(t2, s2, i3, e3 = false, h2) {
    if (t2 !== undefined) {
      const r3 = this.constructor;
      if (e3 === false && (h2 = this[t2]), i3 ??= r3.getPropertyOptions(t2), !((i3.hasChanged ?? f)(h2, s2) || i3.useDefault && i3.reflect && h2 === this._$Ej?.get(t2) && !this.hasAttribute(r3._$Eu(t2, i3))))
        return;
      this.C(t2, s2, i3);
    }
    this.isUpdatePending === false && (this._$ES = this._$EP());
  }
  C(t2, s2, { useDefault: i3, reflect: e3, wrapped: h2 }, r3) {
    i3 && !(this._$Ej ??= new Map).has(t2) && (this._$Ej.set(t2, r3 ?? s2 ?? this[t2]), h2 !== true || r3 !== undefined) || (this._$AL.has(t2) || (this.hasUpdated || i3 || (s2 = undefined), this._$AL.set(t2, s2)), e3 === true && this._$Em !== t2 && (this._$Eq ??= new Set).add(t2));
  }
  async _$EP() {
    this.isUpdatePending = true;
    try {
      await this._$ES;
    } catch (t3) {
      Promise.reject(t3);
    }
    const t2 = this.scheduleUpdate();
    return t2 != null && await t2, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending)
      return;
    if (!this.hasUpdated) {
      if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
        for (const [t4, s3] of this._$Ep)
          this[t4] = s3;
        this._$Ep = undefined;
      }
      const t3 = this.constructor.elementProperties;
      if (t3.size > 0)
        for (const [s3, i3] of t3) {
          const { wrapped: t4 } = i3, e3 = this[s3];
          t4 !== true || this._$AL.has(s3) || e3 === undefined || this.C(s3, undefined, i3, e3);
        }
    }
    let t2 = false;
    const s2 = this._$AL;
    try {
      t2 = this.shouldUpdate(s2), t2 ? (this.willUpdate(s2), this._$EO?.forEach((t3) => t3.hostUpdate?.()), this.update(s2)) : this._$EM();
    } catch (s3) {
      throw t2 = false, this._$EM(), s3;
    }
    t2 && this._$AE(s2);
  }
  willUpdate(t2) {}
  _$AE(t2) {
    this._$EO?.forEach((t3) => t3.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t2)), this.updated(t2);
  }
  _$EM() {
    this._$AL = new Map, this.isUpdatePending = false;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t2) {
    return true;
  }
  update(t2) {
    this._$Eq &&= this._$Eq.forEach((t3) => this._$ET(t3, this[t3])), this._$EM();
  }
  updated(t2) {}
  firstUpdated(t2) {}
}
y.elementStyles = [], y.shadowRootOptions = { mode: "open" }, y[d("elementProperties")] = new Map, y[d("finalized")] = new Map, p?.({ ReactiveElement: y }), (a.reactiveElementVersions ??= []).push("2.1.2");

// node_modules/lit-html/lit-html.js
var t2 = globalThis;
var i3 = (t3) => t3;
var s2 = t2.trustedTypes;
var e3 = s2 ? s2.createPolicy("lit-html", { createHTML: (t3) => t3 }) : undefined;
var h2 = "$lit$";
var o3 = `lit$${Math.random().toFixed(9).slice(2)}$`;
var n3 = "?" + o3;
var r3 = `<${n3}>`;
var l2 = document;
var c3 = () => l2.createComment("");
var a2 = (t3) => t3 === null || typeof t3 != "object" && typeof t3 != "function";
var u2 = Array.isArray;
var d2 = (t3) => u2(t3) || typeof t3?.[Symbol.iterator] == "function";
var f2 = `[ 	
\f\r]`;
var v = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g;
var _ = /-->/g;
var m = />/g;
var p2 = RegExp(`>|${f2}(?:([^\\s"'>=/]+)(${f2}*=${f2}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g");
var g = /'/g;
var $ = /"/g;
var y2 = /^(?:script|style|textarea|title)$/i;
var x = (t3) => (i4, ...s3) => ({ _$litType$: t3, strings: i4, values: s3 });
var b2 = x(1);
var w = x(2);
var T = x(3);
var E = Symbol.for("lit-noChange");
var A = Symbol.for("lit-nothing");
var C = new WeakMap;
var P = l2.createTreeWalker(l2, 129);
function V(t3, i4) {
  if (!u2(t3) || !t3.hasOwnProperty("raw"))
    throw Error("invalid template strings array");
  return e3 !== undefined ? e3.createHTML(i4) : i4;
}
var N = (t3, i4) => {
  const s3 = t3.length - 1, e4 = [];
  let n4, l3 = i4 === 2 ? "<svg>" : i4 === 3 ? "<math>" : "", c4 = v;
  for (let i5 = 0;i5 < s3; i5++) {
    const s4 = t3[i5];
    let a3, u3, d3 = -1, f3 = 0;
    for (;f3 < s4.length && (c4.lastIndex = f3, u3 = c4.exec(s4), u3 !== null); )
      f3 = c4.lastIndex, c4 === v ? u3[1] === "!--" ? c4 = _ : u3[1] !== undefined ? c4 = m : u3[2] !== undefined ? (y2.test(u3[2]) && (n4 = RegExp("</" + u3[2], "g")), c4 = p2) : u3[3] !== undefined && (c4 = p2) : c4 === p2 ? u3[0] === ">" ? (c4 = n4 ?? v, d3 = -1) : u3[1] === undefined ? d3 = -2 : (d3 = c4.lastIndex - u3[2].length, a3 = u3[1], c4 = u3[3] === undefined ? p2 : u3[3] === '"' ? $ : g) : c4 === $ || c4 === g ? c4 = p2 : c4 === _ || c4 === m ? c4 = v : (c4 = p2, n4 = undefined);
    const x2 = c4 === p2 && t3[i5 + 1].startsWith("/>") ? " " : "";
    l3 += c4 === v ? s4 + r3 : d3 >= 0 ? (e4.push(a3), s4.slice(0, d3) + h2 + s4.slice(d3) + o3 + x2) : s4 + o3 + (d3 === -2 ? i5 : x2);
  }
  return [V(t3, l3 + (t3[s3] || "<?>") + (i4 === 2 ? "</svg>" : i4 === 3 ? "</math>" : "")), e4];
};

class S2 {
  constructor({ strings: t3, _$litType$: i4 }, e4) {
    let r4;
    this.parts = [];
    let l3 = 0, a3 = 0;
    const u3 = t3.length - 1, d3 = this.parts, [f3, v2] = N(t3, i4);
    if (this.el = S2.createElement(f3, e4), P.currentNode = this.el.content, i4 === 2 || i4 === 3) {
      const t4 = this.el.content.firstChild;
      t4.replaceWith(...t4.childNodes);
    }
    for (;(r4 = P.nextNode()) !== null && d3.length < u3; ) {
      if (r4.nodeType === 1) {
        if (r4.hasAttributes())
          for (const t4 of r4.getAttributeNames())
            if (t4.endsWith(h2)) {
              const i5 = v2[a3++], s3 = r4.getAttribute(t4).split(o3), e5 = /([.?@])?(.*)/.exec(i5);
              d3.push({ type: 1, index: l3, name: e5[2], strings: s3, ctor: e5[1] === "." ? I : e5[1] === "?" ? L : e5[1] === "@" ? z : H }), r4.removeAttribute(t4);
            } else
              t4.startsWith(o3) && (d3.push({ type: 6, index: l3 }), r4.removeAttribute(t4));
        if (y2.test(r4.tagName)) {
          const t4 = r4.textContent.split(o3), i5 = t4.length - 1;
          if (i5 > 0) {
            r4.textContent = s2 ? s2.emptyScript : "";
            for (let s3 = 0;s3 < i5; s3++)
              r4.append(t4[s3], c3()), P.nextNode(), d3.push({ type: 2, index: ++l3 });
            r4.append(t4[i5], c3());
          }
        }
      } else if (r4.nodeType === 8)
        if (r4.data === n3)
          d3.push({ type: 2, index: l3 });
        else {
          let t4 = -1;
          for (;(t4 = r4.data.indexOf(o3, t4 + 1)) !== -1; )
            d3.push({ type: 7, index: l3 }), t4 += o3.length - 1;
        }
      l3++;
    }
  }
  static createElement(t3, i4) {
    const s3 = l2.createElement("template");
    return s3.innerHTML = t3, s3;
  }
}
function M(t3, i4, s3 = t3, e4) {
  if (i4 === E)
    return i4;
  let h3 = e4 !== undefined ? s3._$Co?.[e4] : s3._$Cl;
  const o4 = a2(i4) ? undefined : i4._$litDirective$;
  return h3?.constructor !== o4 && (h3?._$AO?.(false), o4 === undefined ? h3 = undefined : (h3 = new o4(t3), h3._$AT(t3, s3, e4)), e4 !== undefined ? (s3._$Co ??= [])[e4] = h3 : s3._$Cl = h3), h3 !== undefined && (i4 = M(t3, h3._$AS(t3, i4.values), h3, e4)), i4;
}

class R {
  constructor(t3, i4) {
    this._$AV = [], this._$AN = undefined, this._$AD = t3, this._$AM = i4;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t3) {
    const { el: { content: i4 }, parts: s3 } = this._$AD, e4 = (t3?.creationScope ?? l2).importNode(i4, true);
    P.currentNode = e4;
    let h3 = P.nextNode(), o4 = 0, n4 = 0, r4 = s3[0];
    for (;r4 !== undefined; ) {
      if (o4 === r4.index) {
        let i5;
        r4.type === 2 ? i5 = new k(h3, h3.nextSibling, this, t3) : r4.type === 1 ? i5 = new r4.ctor(h3, r4.name, r4.strings, this, t3) : r4.type === 6 && (i5 = new Z(h3, this, t3)), this._$AV.push(i5), r4 = s3[++n4];
      }
      o4 !== r4?.index && (h3 = P.nextNode(), o4++);
    }
    return P.currentNode = l2, e4;
  }
  p(t3) {
    let i4 = 0;
    for (const s3 of this._$AV)
      s3 !== undefined && (s3.strings !== undefined ? (s3._$AI(t3, s3, i4), i4 += s3.strings.length - 2) : s3._$AI(t3[i4])), i4++;
  }
}

class k {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(t3, i4, s3, e4) {
    this.type = 2, this._$AH = A, this._$AN = undefined, this._$AA = t3, this._$AB = i4, this._$AM = s3, this.options = e4, this._$Cv = e4?.isConnected ?? true;
  }
  get parentNode() {
    let t3 = this._$AA.parentNode;
    const i4 = this._$AM;
    return i4 !== undefined && t3?.nodeType === 11 && (t3 = i4.parentNode), t3;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t3, i4 = this) {
    t3 = M(this, t3, i4), a2(t3) ? t3 === A || t3 == null || t3 === "" ? (this._$AH !== A && this._$AR(), this._$AH = A) : t3 !== this._$AH && t3 !== E && this._(t3) : t3._$litType$ !== undefined ? this.$(t3) : t3.nodeType !== undefined ? this.T(t3) : d2(t3) ? this.k(t3) : this._(t3);
  }
  O(t3) {
    return this._$AA.parentNode.insertBefore(t3, this._$AB);
  }
  T(t3) {
    this._$AH !== t3 && (this._$AR(), this._$AH = this.O(t3));
  }
  _(t3) {
    this._$AH !== A && a2(this._$AH) ? this._$AA.nextSibling.data = t3 : this.T(l2.createTextNode(t3)), this._$AH = t3;
  }
  $(t3) {
    const { values: i4, _$litType$: s3 } = t3, e4 = typeof s3 == "number" ? this._$AC(t3) : (s3.el === undefined && (s3.el = S2.createElement(V(s3.h, s3.h[0]), this.options)), s3);
    if (this._$AH?._$AD === e4)
      this._$AH.p(i4);
    else {
      const t4 = new R(e4, this), s4 = t4.u(this.options);
      t4.p(i4), this.T(s4), this._$AH = t4;
    }
  }
  _$AC(t3) {
    let i4 = C.get(t3.strings);
    return i4 === undefined && C.set(t3.strings, i4 = new S2(t3)), i4;
  }
  k(t3) {
    u2(this._$AH) || (this._$AH = [], this._$AR());
    const i4 = this._$AH;
    let s3, e4 = 0;
    for (const h3 of t3)
      e4 === i4.length ? i4.push(s3 = new k(this.O(c3()), this.O(c3()), this, this.options)) : s3 = i4[e4], s3._$AI(h3), e4++;
    e4 < i4.length && (this._$AR(s3 && s3._$AB.nextSibling, e4), i4.length = e4);
  }
  _$AR(t3 = this._$AA.nextSibling, s3) {
    for (this._$AP?.(false, true, s3);t3 !== this._$AB; ) {
      const s4 = i3(t3).nextSibling;
      i3(t3).remove(), t3 = s4;
    }
  }
  setConnected(t3) {
    this._$AM === undefined && (this._$Cv = t3, this._$AP?.(t3));
  }
}

class H {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t3, i4, s3, e4, h3) {
    this.type = 1, this._$AH = A, this._$AN = undefined, this.element = t3, this.name = i4, this._$AM = e4, this.options = h3, s3.length > 2 || s3[0] !== "" || s3[1] !== "" ? (this._$AH = Array(s3.length - 1).fill(new String), this.strings = s3) : this._$AH = A;
  }
  _$AI(t3, i4 = this, s3, e4) {
    const h3 = this.strings;
    let o4 = false;
    if (h3 === undefined)
      t3 = M(this, t3, i4, 0), o4 = !a2(t3) || t3 !== this._$AH && t3 !== E, o4 && (this._$AH = t3);
    else {
      const e5 = t3;
      let n4, r4;
      for (t3 = h3[0], n4 = 0;n4 < h3.length - 1; n4++)
        r4 = M(this, e5[s3 + n4], i4, n4), r4 === E && (r4 = this._$AH[n4]), o4 ||= !a2(r4) || r4 !== this._$AH[n4], r4 === A ? t3 = A : t3 !== A && (t3 += (r4 ?? "") + h3[n4 + 1]), this._$AH[n4] = r4;
    }
    o4 && !e4 && this.j(t3);
  }
  j(t3) {
    t3 === A ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t3 ?? "");
  }
}

class I extends H {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t3) {
    this.element[this.name] = t3 === A ? undefined : t3;
  }
}

class L extends H {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t3) {
    this.element.toggleAttribute(this.name, !!t3 && t3 !== A);
  }
}

class z extends H {
  constructor(t3, i4, s3, e4, h3) {
    super(t3, i4, s3, e4, h3), this.type = 5;
  }
  _$AI(t3, i4 = this) {
    if ((t3 = M(this, t3, i4, 0) ?? A) === E)
      return;
    const s3 = this._$AH, e4 = t3 === A && s3 !== A || t3.capture !== s3.capture || t3.once !== s3.once || t3.passive !== s3.passive, h3 = t3 !== A && (s3 === A || e4);
    e4 && this.element.removeEventListener(this.name, this, s3), h3 && this.element.addEventListener(this.name, this, t3), this._$AH = t3;
  }
  handleEvent(t3) {
    typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, t3) : this._$AH.handleEvent(t3);
  }
}

class Z {
  constructor(t3, i4, s3) {
    this.element = t3, this.type = 6, this._$AN = undefined, this._$AM = i4, this.options = s3;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t3) {
    M(this, t3);
  }
}
var j = { M: h2, P: o3, A: n3, C: 1, L: N, R, D: d2, V: M, I: k, H, N: L, U: z, B: I, F: Z };
var B = t2.litHtmlPolyfillSupport;
B?.(S2, k), (t2.litHtmlVersions ??= []).push("3.3.3");
var D = (t3, i4, s3) => {
  const e4 = s3?.renderBefore ?? i4;
  let h3 = e4._$litPart$;
  if (h3 === undefined) {
    const t4 = s3?.renderBefore ?? null;
    e4._$litPart$ = h3 = new k(i4.insertBefore(c3(), t4), t4, undefined, s3 ?? {});
  }
  return h3._$AI(t3), h3;
};
// node_modules/lit-element/lit-element.js
var s3 = globalThis;

class i4 extends y {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = undefined;
  }
  createRenderRoot() {
    const t3 = super.createRenderRoot();
    return this.renderOptions.renderBefore ??= t3.firstChild, t3;
  }
  update(t3) {
    const r4 = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t3), this._$Do = D(r4, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(true);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(false);
  }
  render() {
    return E;
  }
}
i4._$litElement$ = true, i4["finalized"] = true, s3.litElementHydrateSupport?.({ LitElement: i4 });
var o4 = s3.litElementPolyfillSupport;
o4?.({ LitElement: i4 });
(s3.litElementVersions ??= []).push("4.2.2");
// custom_components/llm_gateway/frontend/voice-harness-audio-settings.ts
async function voiceSettingsRequest(hass, action, data = {}) {
  if (!hass.callApi)
    throw new Error("Home Assistant is unavailable");
  const service = action === "preview" ? "kukui_voice_audio_preview" : action === "pause" || action === "resume" ? `kukui_voice_${action}` : `kukui_voice_config_${action}`;
  const response = await hass.callApi("POST", `services/rest_command/${service}?return_response`, data);
  const result = response.service_response;
  if (result?.content?.ok !== true || result.status !== 200) {
    throw new Error(result?.content?.error || "The satellite did not apply this request");
  }
  if (action === "preview" && !["played", "muted"].includes(result.content.status || "")) {
    throw new Error("Test sound playback was not confirmed");
  }
  if (action === "read" || action === "update") {
    const config = result.content.config;
    if (!config || typeof config !== "object" || Array.isArray(config)) {
      throw new Error("The satellite did not return its settings");
    }
    return { ...result.content, config: Object.fromEntries(Object.entries(config).filter(([, value]) => typeof value === "boolean" || typeof value === "number" && Number.isFinite(value))) };
  }
  return result.content;
}

class VoiceSettingsSaver {
  save;
  changed;
  pending = {};
  saved = {};
  error = "";
  saving = false;
  inflight = {};
  applied = false;
  timer;
  flight;
  constructor(save, changed) {
    this.save = save;
    this.changed = changed;
  }
  edit(field, value) {
    this.editPatch({ [field]: value });
  }
  editPatch(patch) {
    this.pending = { ...this.pending, ...patch };
    this.error = "";
    this.applied = false;
    clearTimeout(this.timer);
    this.timer = setTimeout(() => void this.flush().catch(() => {}), 400);
    this.changed();
  }
  flush(reapply = false) {
    clearTimeout(this.timer);
    if (this.flight)
      return this.flight;
    const run = async () => {
      while (Object.keys(this.pending).length || reapply) {
        reapply = false;
        const patch = this.pending;
        this.inflight = patch;
        this.pending = {};
        this.saving = true;
        this.changed();
        try {
          const response = await this.save({ ...patch });
          if (!response.ok || !response.apply?.applied || !response.config) {
            throw new Error(response.error || "Settings were saved but could not be applied");
          }
          this.saved = { ...response.config };
          this.applied = true;
          this.error = "";
        } catch (error) {
          this.pending = { ...patch, ...this.pending };
          this.error = error instanceof Error ? error.message : String(error);
          this.applied = false;
          throw error;
        } finally {
          this.saving = false;
          this.inflight = {};
          this.changed();
        }
      }
    };
    this.flight = run().finally(() => {
      this.flight = undefined;
    });
    return this.flight;
  }
}
var groups = [
  { title: ["Wake and follow-up", "唤醒与追问"], fields: [
    ["wake_cue_volume", "Wake cue", "唤醒提示音", 0.05, 0.7, 1],
    ["follow_up_cue_volume", "Follow-up cue", "追问提示音", 0.05, 0.7, 1]
  ] },
  { title: ["Spoken replies", "语音播报"], fields: [
    ["tts_volume_day", "Daytime speech", "日间播报", 0.2, 0.7, 1],
    ["tts_volume_night", "Nighttime speech", "夜间播报", 0.2, 0.5, 0.75]
  ] },
  { title: ["Gentle feedback", "轻声反馈"], fields: [
    ["processing_volume", "Thinking", "思考等待音", 0.05, 0.45, 0.65],
    ["fallback_volume", "Completion and errors", "完成与错误提示", 0.2, 0.6, 1]
  ] }
];
var audioScenes = [
  { id: "daily", name: ["Everyday", "日常"], hint: ["Clear and present", "清晰、自然"], values: {
    wake_cue_volume: 1,
    follow_up_cue_volume: 1,
    processing_volume: 0.58,
    tts_volume_day: 1,
    tts_volume_night: 0.72,
    fallback_volume: 1,
    night_mode: false
  } },
  { id: "focus", name: ["Focus", "专注"], hint: ["Less interruption", "减少打扰"], values: {
    wake_cue_volume: 0.7,
    follow_up_cue_volume: 0.75,
    processing_volume: 0.25,
    tts_volume_day: 0.85,
    tts_volume_night: 0.6,
    fallback_volume: 0.7,
    night_mode: false
  } },
  { id: "night", name: ["Quiet night", "夜间"], hint: ["Softer cues and speech", "提示与播报更柔和"], values: {
    wake_cue_volume: 0.55,
    follow_up_cue_volume: 0.6,
    processing_volume: 0.2,
    tts_volume_day: 1,
    tts_volume_night: 0.72,
    fallback_volume: 0.55,
    night_mode: true
  } }
];

class VoiceHarnessAudioSettings extends i4 {
  static properties = { hass: { attribute: false }, language: { type: String }, active: { type: Boolean } };
  constructor() {
    super();
    this.active = true;
  }
  loaded = false;
  loadError = "";
  previewing = "";
  previewMessage = "";
  controllingCapture = false;
  runtime;
  readFlight;
  poll;
  onVisibility = () => {
    if (document.visibilityState !== "hidden")
      this.refresh();
  };
  saver = new VoiceSettingsSaver(async (patch) => {
    const response = await voiceSettingsRequest(this.hass, "update", { config: patch });
    this.runtime = response.runtime;
    this.loadError = "";
    this.loaded = true;
    return response;
  }, () => this.requestUpdate());
  setConfig() {}
  getCardSize() {
    return 10;
  }
  connectedCallback() {
    super.connectedCallback();
    document.addEventListener("visibilitychange", this.onVisibility);
    this.poll = setInterval(() => void this.refresh(), 2000);
    this.refresh();
  }
  updated(changes) {
    if ((changes.has("hass") || changes.has("active")) && this.hass && this.active)
      this.refresh();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    clearInterval(this.poll);
    document.removeEventListener("visibilitychange", this.onVisibility);
    this.saver.flush().catch(() => {});
  }
  refresh() {
    if (this.readFlight)
      return this.readFlight;
    if (!this.active || !this.hass?.callApi || this.saver.saving || document.visibilityState === "hidden")
      return Promise.resolve();
    const savedBeforeRead = this.saver.saved;
    this.readFlight = (async () => {
      try {
        const response = await voiceSettingsRequest(this.hass, "read");
        if (this.saver.saving || this.saver.saved !== savedBeforeRead)
          return;
        this.saver.saved = { ...response.config };
        this.saver.applied = response.apply?.applied === true;
        this.runtime = response.runtime;
        this.loaded = true;
        this.loadError = "";
      } catch (error) {
        if (this.saver.saved === savedBeforeRead)
          this.loadError = String(error);
      } finally {
        this.readFlight = undefined;
        this.requestUpdate();
      }
    })();
    return this.readFlight;
  }
  text(en, zh) {
    return (this.language || this.hass?.language || "en").startsWith("zh") ? zh : en;
  }
  async preview(field) {
    this.previewing = field;
    this.previewMessage = this.text("Requesting a test sound on the tablet…", "正在请求平板试听…");
    this.requestUpdate();
    try {
      await this.saver.flush(!this.saver.applied);
      const response = await voiceSettingsRequest(this.hass, "preview", { field });
      this.previewMessage = response.status === "muted" ? this.text("Speaker muted. Your volume settings are kept.", "扬声器已静音，音量设置已保留。") : this.text("Tablet test playback completed", "平板试听播放完成");
    } catch (error) {
      this.previewMessage = `${this.text("Test sound not completed", "试听未完成")} · ${error instanceof Error ? error.message : String(error)}`;
    } finally {
      this.previewing = "";
      this.requestUpdate();
    }
  }
  async toggleCapture() {
    this.controllingCapture = true;
    this.requestUpdate();
    try {
      await voiceSettingsRequest(this.hass, this.runtime?.capture === "paused" ? "resume" : "pause", { seconds: 1800, reason: "audio_settings" });
      await this.refresh();
    } catch (error) {
      this.previewMessage = `${this.text("Wake control not confirmed", "唤醒控制未确认")} · ${String(error)}`;
    } finally {
      this.controllingCapture = false;
      this.requestUpdate();
    }
  }
  captureLabel() {
    switch (this.runtime?.capture) {
      case "listening":
        return this.text("Listening to you", "正在聆听你");
      case "closed":
        return this.text("Recording ended", "本轮收音已结束");
      case "wake_word":
        return this.text("Ready for the wake word", "等待唤醒词");
      case "paused":
        return this.text("Wake word paused", "唤醒已暂停");
      default:
        return this.text("Capture state unavailable", "收音状态未知");
    }
  }
  render() {
    const values = { ...this.saver.saved, ...this.saver.inflight, ...this.saver.pending };
    const pending = Object.keys(this.saver.pending).length > 0;
    const scene = audioScenes.find((item) => Object.entries(item.values).every(([key, value]) => values[key] === value));
    const busy = ["listening", "stt", "thinking", "speaking"].includes(this.runtime?.phase || "");
    const status = this.loadError ? this.text("Tablet connection interrupted", "平板连接中断") : !this.loaded ? this.text("Connecting to the tablet…", "正在连接平板…") : this.saver.error ? this.text("Application not confirmed", "应用未确认") : this.saver.saving ? this.text("Applying…", "正在应用…") : pending ? this.text("Saving…", "正在保存…") : this.saver.applied ? this.text("Synced with the tablet", "已同步到平板") : this.text("Saved · application pending", "已保存 · 等待应用");
    return b2`
      <section aria-label=${this.text("Tablet audio", "平板声音")}>
        <header><div><span class="eyebrow">${this.text("VOICE & SOUND", "语音与声音")}</span>
          <h2>${this.text("Tablet audio", "平板声音")}</h2><p role="status">${status}</p></div>
          <span class="profile">${this.runtime?.tts_profile === "night" ? this.text("Night speech", "夜间播报") : this.runtime?.tts_profile === "day" ? this.text("Day speech", "日间播报") : "—"}
            <strong>${!this.loadError && this.runtime?.tts_volume != null ? `${Math.round(this.runtime.tts_volume * 100)}%` : "—"}</strong></span></header>
        <div class="toggles">${[["audio_muted", "Speaker mute", "扬声器静音"], ["night_mode", "Use night volume", "使用夜间音量"]].map(([field, en, zh]) => b2`
          <button aria-pressed=${values[field] === true} ?disabled=${!this.loaded || typeof values[field] !== "boolean"}
            @click=${() => this.saver.edit(field, !values[field])}>${this.text(en, zh)}</button>`)}</div>
        <div class="capture"><span class=${this.runtime?.capture === "listening" && !this.loadError ? "listening" : ""}>${this.loadError ? this.text("Capture state unavailable", "收音状态未知") : this.captureLabel()}</span>
          <button ?disabled=${!this.loaded || !!this.loadError || this.controllingCapture || !this.runtime}
            @click=${() => this.toggleCapture()}>${this.controllingCapture ? this.text("Updating…", "正在处理…") : this.runtime?.capture === "paused" ? this.text("Resume wake word", "恢复唤醒") : this.text("Pause for 30 min", "免打扰 30 分钟")}</button></div>
        <p class="explanation">${this.text("Mute keeps the microphone available. Do not disturb pauses wake and capture.", "静音保留麦克风；免打扰暂停唤醒与收音。")}</p>
        <div class="section-label"><h3>${this.text("Sound for your moment", "适合此刻的声音")}</h3><span>${scene ? this.text(scene.name[0], scene.name[1]) : this.text("Custom", "自定义")}</span></div>
        <div class="scenes">${audioScenes.map((item) => b2`<button aria-pressed=${scene?.id === item.id}
          ?disabled=${!this.loaded} @click=${() => this.saver.editPatch(item.values)}>
          <strong>${this.text(item.name[0], item.name[1])}</strong><span>${this.text(item.hint[0], item.hint[1])}</span></button>`)}</div>
        <p class="explanation">${this.text("Night speech volume follows the tablet's clock, from 22:00 to 07:00.", "平板会在每天 22:00–07:00 自动使用夜间播报音量。")}</p>
        <details class="fine-tuning"><summary>${this.text("Fine-tune volumes", "音量微调")}</summary>
        <div class="groups">${groups.map((group) => b2`<fieldset><legend>${this.text(group.title[0], group.title[1])}</legend>
          ${group.fields.map(([field, en, zh, min, low, high]) => {
      const value = typeof values[field] === "number" ? values[field] : undefined;
      const active = this.previewing === field;
      return b2`<div class="volume-row" aria-busy=${active}>
              <label for=${field}>${this.text(en, zh)}<output for=${field}>${value == null ? "—" : `${Math.round(value * 100)}%`}</output></label>
              <div class="slider-row"><div class="range">
                <span class="recommended" aria-hidden="true" style=${`left:${(low - min) / (1 - min) * 100}%;width:${(high - low) / (1 - min) * 100}%`}></span>
                <input id=${field} type="range" min=${min} max="1" step="0.01" .value=${String(value ?? min)}
                  aria-valuetext=${value == null ? "—" : `${Math.round(value * 100)}%`}
                  ?disabled=${!this.loaded || value == null}
                  @input=${(event) => this.saver.edit(field, Number(event.target.value))}>
              </div><button class="preview" ?disabled=${!this.loaded || value == null || Boolean(this.previewing) || busy || !!this.loadError}
                aria-label=${`${this.text("Play test sound on tablet", "在平板试听")} · ${this.text(en, zh)}`}
                @click=${() => this.preview(field)}>
                ${active ? b2`<span class="wave" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>` : b2`<span aria-hidden="true">▶</span>`}
                <span>${active ? this.text("Testing…", "试听中…") : this.text("Test", "试听")}</span>
              </button></div>
              <p class="range-note">${this.text("Everyday range", "日常建议")} ${Math.round(low * 100)}–${Math.round(high * 100)}%</p>
            </div>`;
    })}</fieldset>`)}</div>
        <div class="headroom"><span class="peak-line" aria-hidden="true"></span><p>${this.text("Earcon master peak", "提示音母带峰值")} <strong>−1.0 dBFS</strong><br>
          ${this.text("100% is unity gain. Night speech is automatic from 22:00 to 07:00 on the tablet.", "100% 为原始增益。平板时间 22:00–07:00 自动使用夜间播报音量。")}</p></div>
        <p class="preview-status" role="status">${this.previewMessage || (busy ? this.text("A conversation is active. Test sounds are available after the reply.", "正在对话，回复结束后可以试听。") : this.text("Test sounds play through the tablet speaker.", "试听声音从平板扬声器播放。"))}</p>
        </details>
        ${this.loadError ? b2`<div class="error" role="alert">${this.text("Cannot refresh tablet settings. Your edits are kept.", "暂时无法读取平板设置，修改仍会保留。")}
          <button @click=${() => this.refresh()}>${this.text("Reconnect", "重新连接")}</button></div>` : ""}
        ${this.saver.error || this.loaded && !this.saver.applied && !pending && !this.saver.saving ? b2`<div class="error" role="alert">${this.saver.error ? this.text("Changes are unconfirmed and kept for retry.", "修改尚未确认，已保留供重试。") : this.text("Saved settings need another application attempt.", "已保存的设置需要重新应用。")}
          <button @click=${() => void this.saver.flush(true).catch(() => {})}>${this.text("Retry", "重试")}</button></div>` : ""}
      </section>`;
  }
  static styles = i`
    :host { display: block; container-type: inline-size; color: var(--primary-text-color, #213b3b); --accent: var(--primary-color, #257a70); --surface: var(--card-background-color, #fff); --muted: var(--secondary-text-color, #637773); }
    * { box-sizing: border-box; }
    section { background: linear-gradient(145deg, color-mix(in srgb, var(--accent) 7%, var(--surface)), var(--surface) 45%); border: 1px solid var(--divider-color, #dfe7e3); border-radius: 26px; padding: 26px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
    .eyebrow { color: var(--muted); font-size: 11px; letter-spacing: .14em; }
    h2 { font-size: 27px; font-weight: 550; margin: 7px 0 8px; letter-spacing: -.03em; }
    h3 { font-size: 14px; font-weight: 550; margin: 0; }
    .fine-tuning { border-top: 1px solid var(--divider-color, #d6e2de); margin-top: 22px; }
    summary { min-height: 52px; padding: 16px 0; cursor: pointer; font-size: 14px; font-weight: 550; }
    summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; border-radius: 4px; }
    p { color: var(--muted); font-size: 12px; line-height: 1.6; margin: 0; }
    .profile { color: var(--muted); font-size: 11px; text-align: right; white-space: nowrap; }
    .profile strong { display: block; color: var(--primary-text-color, #213b3b); font-size: 30px; font-weight: 450; font-variant-numeric: tabular-nums; }
    button { font: inherit; font-size: 13px; border: 1px solid var(--divider-color, #d6e2de); background: transparent; color: inherit; border-radius: 14px; min-height: 44px; min-width: 44px; padding: 10px 14px; cursor: pointer; transition: background .18s, transform .18s; touch-action: manipulation; }
    button:hover:enabled { background: color-mix(in srgb, var(--accent) 9%, transparent); }
    button:active:enabled { transform: scale(.98); }
    button:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
    button:disabled { opacity: .45; cursor: default; }
    button[aria-pressed=true] { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 12%, transparent); }
    .toggles { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 24px; }
    .capture { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 12px; font-size: 12px; color: var(--muted); }
    .capture > span::before { content: ''; display: inline-block; width: 6px; height: 6px; margin-right: 8px; background: currentColor; border-radius: 50%; }
    .capture .listening { color: var(--accent); }
    .capture .listening::before { animation: listen 1.2s ease-in-out infinite alternate; }
    .capture button { font-size: 12px; padding: 8px 10px; border-color: transparent; flex-shrink: 0; }
    .explanation { margin-top: 3px; font-size: 11px; }
    .section-label { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 26px 0 12px; }
    .section-label > span { font-size: 12px; color: var(--muted); }
    .scenes { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .scenes button { text-align: left; padding: 14px; }
    .scenes strong { display: block; font-size: 14px; font-weight: 550; }
    .scenes span { display: block; margin-top: 6px; font-size: 11px; color: var(--muted); line-height: 1.4; }
    .groups { display: grid; gap: 20px; margin-top: 28px; }
    fieldset { min-width: 0; margin: 0; padding: 14px 16px 2px; border: 1px solid var(--divider-color, #dfe7e3); border-radius: 18px; }
    legend { padding: 0 7px; font-size: 13px; font-weight: 550; color: var(--muted); }
    .volume-row { margin: 2px 0 16px; }
    label { display: flex; justify-content: space-between; gap: 12px; align-items: center; font-size: 14px; }
    output { font-size: 15px; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .slider-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 14px; align-items: center; margin-top: 3px; }
    .range { position: relative; height: 44px; }
    .recommended { position: absolute; height: 3px; bottom: 1px; border-radius: 2px; background: color-mix(in srgb, var(--accent) 35%, transparent); pointer-events: none; }
    input { display: block; width: 100%; min-width: 0; height: 44px; margin: 0; accent-color: var(--accent); cursor: pointer; }
    .preview { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-width: 82px; padding: 8px 11px; font-size: 12px; }
    .range-note { font-size: 10px; margin-top: 3px; }
    .headroom { display: flex; gap: 12px; align-items: center; margin-top: 22px; }
    .headroom p { font-size: 11px; }
    .headroom strong { font-weight: 500; white-space: nowrap; }
    .peak-line { width: 5px; height: 32px; flex-shrink: 0; border-radius: 3px; border-top: 2px solid var(--accent); background: color-mix(in srgb, var(--accent) 15%, transparent); }
    .error { display: flex; gap: 12px; align-items: center; justify-content: space-between; color: var(--error-color, #b84030); margin-top: 16px; font-size: 13px; }
    .preview-status { margin-top: 18px; min-height: 20px; }
    .wave { display: inline-flex; align-items: center; gap: 2px; height: 18px; }
    .wave i { display: block; background: currentColor; width: 2px; height: 12px; border-radius: 2px; animation: wave .6s ease-in-out infinite alternate; }
    .wave i:nth-child(2n) { animation-delay: -.25s; height: 18px; }
    .wave i:nth-child(3) { animation-delay: -.4s; }
    @keyframes wave { from { transform: scaleY(.3); } to { transform: scaleY(1); } }
    @keyframes listen { from { opacity: .4; } to { opacity: 1; } }
    @container (min-width: 700px) { .groups { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; } .preview > span:last-child { display: none; } .preview { min-width: 44px; } }
    @container (max-width: 430px) { section { padding: 20px 16px; border-radius: 20px; } h2 { font-size: 25px; } .scenes { gap: 7px; } .scenes button { padding: 12px 10px; } }
    @media (prefers-reduced-motion: reduce) { *, *::before { animation: none !important; transition: none !important; } }
  `;
}
if (!customElements.get("voice-harness-audio-settings")) {
  customElements.define("voice-harness-audio-settings", VoiceHarnessAudioSettings);
}

// custom_components/llm_gateway/frontend/voice-harness-styles.ts
var harnessFoundationStyles = i`
  :host {
    box-sizing: border-box;
    color: var(--primary-text-color, #202a32);
    font-family: var(
      --paper-font-body1_-_font-family,
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      sans-serif
    );
    --vh-ink: var(--primary-text-color, #202a32);
    --vh-muted: var(--secondary-text-color, #626f78);
    --vh-surface: var(--card-background-color, #fff);
    --vh-background: var(--primary-background-color, #f4f6f8);
    --vh-line: color-mix(
      in srgb,
      var(--divider-color, #cdd5dc) 65%,
      transparent
    );
    --vh-accent: var(--primary-color, #347c8c);
    --vh-soft: color-mix(in srgb, var(--vh-accent) 8%, var(--vh-surface));
    --vh-radius-s: 12px;
    --vh-radius-m: 20px;
    --vh-radius-l: 28px;
    --vh-space-xs: 6px;
    --vh-space-s: 12px;
    --vh-space-m: 20px;
    --vh-ease: cubic-bezier(0.2, 0.8, 0.2, 1);
    font-size: 14px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
  :host([hidden]),
  [hidden] {
    display: none !important;
  }
  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }
  h1,
  h2,
  h3,
  p {
    margin: 0;
  }
  h2 {
    font-size: clamp(22px, 2vw, 30px);
    font-weight: 650;
    letter-spacing: -0.035em;
    line-height: 1.2;
  }
  h3 {
    font-size: 16px;
    font-weight: 650;
    letter-spacing: -0.015em;
  }
  ha-icon {
    width: 22px;
    height: 22px;
    --mdc-icon-size: 22px;
    flex: 0 0 auto;
  }
  :focus-visible {
    outline: 3px solid var(--vh-accent);
    outline-offset: 3px;
  }
  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      animation: none !important;
      transition: none !important;
      scroll-behavior: auto !important;
    }
  }
`;
var harnessButtonStyles = i`
  button,
  select,
  input,
  textarea {
    font: inherit;
    color: inherit;
  }
  button,
  select,
  input:not([type="checkbox"]):not([type="radio"]):not([type="range"]) {
    min-height: 44px;
  }
  button {
    min-width: 44px;
    border: 1px solid var(--vh-line);
    border-radius: var(--vh-radius-s);
    padding: 10px 16px;
    background: var(--vh-surface);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-weight: 550;
    transition:
      background 180ms,
      transform 180ms var(--vh-ease),
      box-shadow 180ms;
  }
  button:hover:not(:disabled) {
    background: var(--vh-soft);
    box-shadow: 0 2px 8px #00000008;
  }
  button:active:not(:disabled) {
    transform: scale(0.975);
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  button.primary {
    background: var(--vh-accent);
    color: var(--text-primary-color, white);
    border-color: transparent;
  }
  button.primary:hover:not(:disabled) {
    background: color-mix(in srgb, var(--vh-accent) 88%, var(--vh-ink));
  }
  button.quiet {
    background: transparent;
    border-color: transparent;
  }
  input,
  select,
  textarea {
    width: 100%;
    border: 1px solid var(--vh-line);
    border-radius: var(--vh-radius-s);
    background: var(--vh-background);
    padding: 10px 12px;
  }
  textarea {
    resize: vertical;
    line-height: 1.65;
  }
  label {
    display: grid;
    gap: 8px;
    font-weight: 550;
  }
  summary {
    cursor: pointer;
    min-height: 44px;
    padding: 12px 0;
  }
`;
var harnessSurfaceStyles = i`
  .surface {
    background: var(--vh-surface);
    border: 1px solid var(--vh-line);
    border-radius: var(--vh-radius-m);
    padding: 24px;
    min-width: 0;
  }
  .muted,
  .meta {
    color: var(--vh-muted);
    font-size: 13px;
  }
  .eyebrow {
    color: var(--vh-muted);
    font-size: 11px;
    font-weight: 650;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .section-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
  }
  .section-head > div {
    min-width: 0;
    display: grid;
    gap: 8px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 550;
    background: var(--vh-background);
    color: var(--vh-muted);
    white-space: nowrap;
  }
  .ok {
    color: var(--success-color, #238675);
  }
  .warning {
    color: var(--warning-color, #ae782b);
  }
  .bad {
    color: var(--error-color, #c45050);
  }
  .chip.ok {
    background: color-mix(
      in srgb,
      var(--success-color, #238675) 10%,
      var(--vh-surface)
    );
  }
  .chip.warning {
    background: color-mix(
      in srgb,
      var(--warning-color, #ae782b) 10%,
      var(--vh-surface)
    );
  }
  .chip.bad {
    background: color-mix(
      in srgb,
      var(--error-color, #c45050) 10%,
      var(--vh-surface)
    );
  }
  .empty {
    padding: 48px 24px;
    text-align: center;
    color: var(--vh-muted);
  }
  .error {
    padding: 14px 18px;
    border-radius: var(--vh-radius-s);
    background: color-mix(
      in srgb,
      var(--error-color, #c45050) 10%,
      var(--vh-surface)
    );
    overflow-wrap: anywhere;
  }
  pre {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font: 12px/1.65 var(--code-font-family, ui-monospace, monospace);
  }
  @media (max-width: 600px) {
    .surface {
      padding: 18px;
    }
    .section-head {
      align-items: flex-start;
      flex-wrap: wrap;
    }
  }
`;

// custom_components/llm_gateway/frontend/voice-harness-navigation.ts
class VoiceHarnessNavigation extends i4 {
  static properties = {
    active: { type: String },
    items: { attribute: false }
  };
  constructor() {
    super();
    this.active = "";
    this.items = [];
  }
  render() {
    return b2`
      <nav aria-label="Voice Harness views" role="tablist">
        ${this.items.map((item) => b2`
            <button
              aria-selected=${String(item.id === this.active)}
              data-id=${item.id}
              role="tab"
              tabindex=${item.id === this.active ? "0" : "-1"}
              @click=${() => this.select(item.id)}
              @keydown=${this.onKeydown}
            >
              <ha-icon icon=${item.icon}></ha-icon>
              <span>${item.label}</span>
            </button>
          `)}
      </nav>
    `;
  }
  select(id) {
    this.dispatchEvent(new CustomEvent("harness-view-select", {
      bubbles: true,
      composed: true,
      detail: { id }
    }));
  }
  onKeydown(event) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      return;
    }
    event.preventDefault();
    const current = this.items.findIndex((item2) => item2.id === this.active);
    let next = current < 0 ? 0 : current;
    if (event.key === "Home")
      next = 0;
    if (event.key === "End")
      next = this.items.length - 1;
    if (event.key === "ArrowLeft")
      next = (next - 1 + this.items.length) % this.items.length;
    if (event.key === "ArrowRight")
      next = (next + 1) % this.items.length;
    const item = this.items[next];
    if (!item)
      return;
    this.select(item.id);
    const button = this.renderRoot.querySelector(`button[data-id="${CSS.escape(item.id)}"]`);
    button?.focus();
  }
  static styles = [
    harnessFoundationStyles,
    harnessButtonStyles,
    i`
      :host {
        display: block;
        margin: 0;
      }
      nav {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 4px;
        padding: 5px;
        border: 1px solid var(--vh-line);
        border-radius: 16px;
        background: var(--vh-surface);
      }
      button {
        min-width: 0;
        min-height: 46px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 0 10px;
        background: transparent;
        white-space: nowrap;
      }
      button:hover {
        background: color-mix(in srgb, var(--primary-color) 8%, transparent);
      }
      button[aria-selected="true"] {
        background: var(--vh-soft);
        color: var(--vh-accent);
      }
      ha-icon {
        width: 20px;
        height: 20px;
        flex: 0 0 auto;
      }
      span {
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      @media (max-width: 560px) {
        button {
          padding: 8px 4px;
          flex-direction: column;
          gap: 4px;
          font-size: 11px;
          min-height: 60px;
        }
        ha-icon {
          width: 18px;
          height: 18px;
          --mdc-icon-size: 18px;
        }
      }
    `
  ];
}
if (!customElements.get("voice-harness-navigation")) {
  customElements.define("voice-harness-navigation", VoiceHarnessNavigation);
}

// custom_components/llm_gateway/frontend/voice-harness-live-model.ts
var object = (value) => value && typeof value === "object" && !Array.isArray(value) ? value : {};
var records = (value) => Array.isArray(value) ? value.map(object) : [];
var measurement = (value) => typeof value === "number" && Number.isFinite(value) ? value : null;
var idOf = (value) => String(value.run_id || value.id || "");
var speechOf = (value) => String(object(value.speech).final || value.final_speech_text || value.assistant_text || "");
function isLiveRun(record) {
  return object(record.lineage).mode !== "dry_run" && record.terminal_outcome !== "dry_run" && record.outcome !== "dry_run" && object(record.route).kind !== "replay";
}
function latestConversation(input) {
  return [...input].filter(isLiveRun).sort((a3, b3) => {
    const time = (run) => Date.parse(String(run.created_at || run.started_at || "")) || 0;
    return time(b3) - time(a3);
  })[0] || null;
}
function conversationFacts(run) {
  const facts = object(run.interaction);
  const observations = records(facts.observations);
  const dispatches = records(facts.dispatches);
  const sent = dispatches.filter((dispatch) => dispatch.dispatch_status === "sent");
  const failed = dispatches.some((dispatch) => dispatch.dispatch_status === "failed");
  const allSent = sent.length > 0 && sent.length === dispatches.length;
  const family = String(run.task_family || object(run.route_decision).task_family || "");
  const action = ["home_control", "volume_control"].includes(family) || dispatches.length > 0;
  const outcome = runOutcome(run);
  const terminal = run.terminal_outcome || object(object(run.route).harness_loop).terminal_outcome || object(run.route).terminal_outcome || run.status;
  const evidence = terminal === "partial" || failed && sent.length > 0 ? "partial" : outcome === "running" ? "running" : outcome === "clarification" ? "clarification" : outcome === "failed" || failed ? "failed" : outcome === "cancelled" ? "cancelled" : action ? sent.some((dispatch) => dispatch.confirmation_status === "not_confirmed") ? "not_confirmed" : allSent && sent.every((dispatch) => dispatch.confirmation_status === "confirmed") ? "confirmed" : allSent && sent.every((dispatch) => dispatch.acceptance_status === "accepted") ? "accepted" : sent.length ? "sent" : "unconfirmed" : observations.some((observation) => observation.answerable === true) ? "observed" : outcome === "answered" ? "reply" : "unknown";
  return {
    intent: String(facts.intent_text || run.user_text || object(run.input).text || ""),
    reply: speechOf(run),
    evidence,
    sources: [...new Set(observations.filter((observation) => observation.answerable === true).flatMap((observation) => records(observation.entities)).map((entity) => String(entity.name || entity.entity_id || "")).filter(Boolean))]
  };
}
function supportsActionReplay(record) {
  const decision = object(record.route_decision);
  return decision.route === "local_action" && decision.next_action === "execute_local" && object(record.lineage).mode !== "dry_run";
}
function observedMetrics(input) {
  const live = input.filter(isLiveRun);
  const settled = live.filter((run) => ["answered", "failed", "clarification", "cancelled"].includes(runOutcome(run)));
  const timed = settled.map((run) => measurement(run.latency_ms)).filter((value) => value !== null && value >= 0);
  const sorted = [...timed].sort((a3, b3) => a3 - b3);
  const middle = Math.floor(sorted.length / 2);
  const ratio = (count) => settled.length ? 100 * count / settled.length : null;
  return {
    count: settled.length,
    medianMs: sorted.length ? (sorted[middle] + sorted[Math.floor((sorted.length - 1) / 2)]) / 2 : null,
    successRate: ratio(settled.filter((run) => runOutcome(run) === "answered").length),
    errorRate: ratio(settled.filter((run) => runOutcome(run) === "failed").length),
    latencies: timed.reverse(),
    outcomes: [...settled].reverse().map((run) => runOutcome(run) === "answered" ? 1 : 0),
    errors: [...settled].reverse().map((run) => runOutcome(run) === "failed" ? 1 : 0)
  };
}
var stageIds = [
  "wake",
  "asr",
  "llm",
  "tts",
  "playback",
  "follow_up"
];
function eventStage(event) {
  const name = String(event.type || event.event_type || event.stage || "").toLowerCase();
  if (/follow[_./-]?up/.test(name))
    return "follow_up";
  if (/wake/.test(name))
    return "wake";
  if (/playback|player[._/]|audio[._/]play/.test(name))
    return "playback";
  if (/^asr[./]|^stt[./]|recognition|transcript/.test(name))
    return "asr";
  if (/^tts[./]|synth/.test(name))
    return "tts";
  if (/^gateway[./]|^llm[./]|model|provider|route_decision|tool|completion/.test(name))
    return "llm";
  return null;
}
function eventStart(event) {
  return measurement(event.offset_ms ?? event.start_ms ?? event.t_ms ?? (event.source === "llm-gateway" ? event.monotonic_ms : null));
}
function pipelineStages(run) {
  const events = records(run.event_stream);
  const source = events.length ? events : records(run.timeline_spans).length ? records(run.timeline_spans) : records(run.timeline);
  return stageIds.map((id) => {
    const matching = source.filter((event) => eventStage(event) === id);
    const starts = matching.map(eventStart).filter((n4) => n4 !== null);
    const spans = matching.flatMap((event) => {
      const start = eventStart(event);
      const duration = measurement(event.duration_ms ?? object(event.payload).duration_ms);
      return duration === null || duration < 0 ? [] : [{ start, duration }];
    });
    const aligned = spans.filter((span) => span.start !== null);
    let durationMs = aligned.length && aligned.length === spans.length ? Math.max(...aligned.map((span) => span.start + span.duration)) - Math.min(...aligned.map((span) => span.start)) : spans.length === 1 ? spans[0].duration : null;
    if (durationMs === null && id === "llm" && matching.some((event) => event.source === "llm-gateway"))
      durationMs = measurement(run.latency_ms);
    const statuses = matching.map((event) => String(event.status || object(event.payload).status || "observed"));
    const failure = statuses.find((status) => ["failed", "error", "unsupported", "not_confirmed"].includes(status));
    return {
      id,
      startMs: starts.length ? Math.min(...starts) : null,
      durationMs,
      status: failure || statuses.at(-1) || "missing",
      events: matching
    };
  });
}
function livePipeline(states, display, now = Date.now()) {
  const pipeline = object(states.voice_pipeline);
  const available = pipeline.available === true && ["on", "ready", "ok"].includes(String(pipeline.state));
  const paused = ["on", "paused"].includes(String(object(states.voice_paused).state));
  const timestamp = display.updated_at || display.created_at || display.timestamp;
  const age = typeof timestamp === "string" ? now - Date.parse(timestamp) : NaN;
  const expiry = typeof display.expires_at === "string" ? Date.parse(display.expires_at) : NaN;
  const fresh = Number.isFinite(age) && age >= 0 && age <= 30000 && (!Number.isFinite(expiry) || expiry > now);
  const state = String(display.state || display.phase || "");
  const active = available && !paused && fresh && [
    "listening",
    "recording",
    "stt",
    "thinking",
    "processing",
    "searching",
    "speaking",
    "tts",
    "playing"
  ].includes(state);
  return {
    active,
    connected: available,
    phase: paused ? "paused" : active ? state : available ? "standby" : pipeline.state === "off" ? "offline" : "unknown",
    ageMs: Number.isFinite(age) ? age : null
  };
}
function sparkline(values, width = 180, height = 42) {
  if (values.length < 2)
    return "";
  const min = Math.min(...values);
  const spread = Math.max(...values) - min;
  return values.map((value, index) => (index / (values.length - 1) * width).toFixed(1) + "," + (height - (spread ? (value - min) / spread : 0.5) * (height - 8) - 4).toFixed(1)).join(" ");
}
var pcmSampleRates = [8000, 16000, 22050, 24000, 44100, 48000];
function pcmWave(pcm, sampleRate, channels) {
  if (!pcmSampleRates.includes(sampleRate) || ![1, 2].includes(channels) || pcm.byteLength === 0 || pcm.byteLength % (channels * 2)) {
    throw new Error("Use complete 16-bit little-endian PCM samples with the selected rate and channels.");
  }
  const result = new ArrayBuffer(44 + pcm.byteLength);
  const bytes = new Uint8Array(result);
  const view = new DataView(result);
  for (const [offset, text] of [
    [0, "RIFF"],
    [8, "WAVE"],
    [12, "fmt "],
    [36, "data"]
  ])
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

// custom_components/llm_gateway/frontend/voice-harness-stat.ts
class VoiceHarnessStat extends i4 {
  static properties = {
    icon: {},
    label: {},
    tone: { reflect: true },
    value: {},
    hint: {},
    values: { attribute: false }
  };
  constructor() {
    super();
    this.icon = "";
    this.label = "";
    this.tone = "muted";
    this.value = "";
    this.hint = "";
    this.values = [];
  }
  render() {
    const points = sparkline(this.values);
    return b2`
      <div class="label">
        ${this.icon ? b2`<ha-icon icon=${this.icon}></ha-icon>` : A}<span
          >${this.label}</span
        >
      </div>
      <strong>${this.value || "—"}</strong>
      <small>${this.hint}</small>
      ${points ? w`<svg viewBox="0 0 180 42" preserveAspectRatio="none" aria-hidden="true"><polyline points=${points} fill="none" stroke="currentColor" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" stroke-linecap="round" /></svg>` : A}
    `;
  }
  static styles = [
    harnessFoundationStyles,
    i`
      :host {
        display: grid;
        align-content: start;
        position: relative;
        min-height: 170px;
        gap: 10px;
        padding: 22px;
        border: 1px solid var(--vh-line);
        border-radius: var(--vh-radius-m);
        background: var(--vh-surface);
        overflow: hidden;
      }
      .label {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--vh-muted);
        font-size: 13px;
      }
      ha-icon {
        width: 18px;
        height: 18px;
        --mdc-icon-size: 18px;
      }
      strong {
        font-size: clamp(26px, 3vw, 40px);
        font-weight: 570;
        letter-spacing: -0.045em;
        line-height: 1.15;
        font-variant-numeric: tabular-nums;
        z-index: 1;
        overflow-wrap: anywhere;
      }
      small {
        color: var(--vh-muted);
        font-size: 11px;
        z-index: 1;
        max-width: 70%;
      }
      svg {
        position: absolute;
        right: 16px;
        bottom: 12px;
        width: 42%;
        height: 32px;
        color: var(--vh-accent);
        opacity: 0.7;
      }
      :host([tone="bad"]) svg {
        color: var(--error-color, #c45050);
      }
      :host([tone="ok"]) svg {
        color: var(--success-color, #238675);
      }
      @media (max-width: 600px) {
        :host {
          min-height: 150px;
          padding: 18px;
        }
        strong {
          font-size: 28px;
        }
        .label {
          font-size: 12px;
        }
      }
    `
  ];
}
if (!customElements.get("voice-harness-stat"))
  customElements.define("voice-harness-stat", VoiceHarnessStat);

// custom_components/llm_gateway/frontend/voice-harness-overview.ts
class VoiceHarnessOverview extends i4 {
  static properties = {
    entries: { attribute: false },
    satellite: { attribute: false },
    language: {}
  };
  constructor() {
    super();
    this.entries = [];
    this.satellite = {};
    this.language = "en";
  }
  text(en, zh) {
    return this.language.startsWith("zh") ? zh : en;
  }
  render() {
    const t3 = this.text.bind(this);
    const runs = this.entries.flatMap((entry) => records(object(entry.traces).records));
    const active = this.entries.flatMap((entry) => records(entry.voice_runs).filter((run) => run.status === "running"));
    const latest = latestConversation([...active, ...runs]);
    const facts = latest ? conversationFacts(latest) : null;
    const live = livePipeline(object(this.satellite.states), object(object(this.entries[0]?.feedback).latest_display));
    const stateLabel = live.phase === "paused" ? t3("Do not disturb", "免打扰中") : live.active ? t3("Conversation in progress", "正在对话") : live.phase === "standby" ? t3("Standing by", "语音待机") : live.phase === "offline" ? t3("Voice connection interrupted", "语音连接中断") : t3("Capture state unknown", "收音状态未知");
    const evidence = facts?.evidence || "unknown";
    const evidenceLabel = {
      observed: t3("State read from observations", "已有观测依据"),
      sent: t3("Request sent · confirmation missing", "请求已发送 · 设备确认暂缺"),
      accepted: t3("Request accepted · device unconfirmed", "请求已受理 · 设备确认暂缺"),
      confirmed: t3("Device reported the requested state", "设备已回报请求的状态"),
      not_confirmed: t3("Device did not confirm the request", "设备尚未确认这次请求"),
      unconfirmed: t3("Device response unconfirmed", "尚无设备响应的确认"),
      reply: t3("Reply generated", "已生成回复"),
      failed: t3("This request did not complete", "这次请求未完成"),
      partial: t3("Only part of the request was sent", "请求仅部分发出"),
      clarification: t3("One detail to clarify", "还需要补充一点信息"),
      cancelled: t3("Conversation stopped", "本次对话已停止"),
      running: t3("Processing your request", "正在处理这句话"),
      unknown: t3("Awaiting evidence", "等待结果依据")
    }[evidence];
    const guidance = !latest ? t3("Your next conversation will appear here.", "下一次对话会记录在这里。") : evidence === "clarification" ? t3("Answer the question above to continue.", "回答上面的澄清问题即可继续。") : ["failed", "partial"].includes(evidence) ? t3("The reply explains what is missing. Details are available in the record.", "可从回复了解未完成的原因，在记录中查看详情。") : ["sent", "accepted", "unconfirmed", "not_confirmed"].includes(evidence) ? t3("The device response remains unconfirmed. The record has the available evidence.", "设备响应仍待确认，可在记录中查看已有反馈。") : evidence === "running" ? t3("Waiting for the reply.", "正在等待回复。") : evidence === "unknown" ? t3("There is not enough evidence to judge this request yet.", "目前还没有足够依据判断这次请求的结果。") : t3("Nothing else is needed for this conversation.", "这次对话无需补充。");
    const timestamp = String(latest?.created_at || latest?.started_at || "");
    const userText = String(latest?.user_text || object(latest?.input).text || "");
    return b2`
      <div class="section-head intro">
        <div><span class="eyebrow">${t3("VOICE & SPACE", "语音与空间")}</span>
          <h2>${t3("Your last conversation", "最近的对话")}</h2>
          <p class="muted">${t3("What was understood, what happened, and what needs you.", "听懂了什么，实际发生了什么，是否需要你。")}</p>
        </div>
        <span class="chip" role="status"><span class="dot" data-active=${String(live.active)}></span>${stateLabel}</span>
      </div>
      <div class="conversation-grid">
        <section class="surface conversation" aria-label=${t3("Understood intent", "理解的意图")}>
          <div class="section-head"><span class="eyebrow">${t3("YOU SAID", "刚才那句话")}</span>
            ${Number.isFinite(Date.parse(timestamp)) ? b2`<time datetime=${timestamp}>${new Date(timestamp).toLocaleString(this.language, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</time>` : A}
          </div>
          <h3 class="utterance">${userText || t3("No conversation recorded yet.", "还没有对话记录。")}</h3>
          ${facts?.intent && facts.intent !== userText ? b2`<p class="resolved"><span>${t3("Understood as", "理解为")}</span>${facts.intent}</p>` : A}
          <div class="reply"><span class="eyebrow">${t3("THE REPLY", "系统的回应")}</span>
            <p>${facts?.reply || (latest ? t3("The reply has not been recorded yet.", "暂未记录到回复。") : t3("Speak as you normally would.", "像平常一样开口就好。"))}</p>
          </div>
          <button class="quiet" @click=${() => this.navigate("runs")}>${t3("Conversation records", "查看对话记录")} <ha-icon icon="mdi:arrow-top-right"></ha-icon></button>
        </section>
        <section class="surface reality" aria-label=${t3("Result and next step", "结果与下一步")}>
          <span class="eyebrow">${t3("WHAT HAPPENED", "实际结果")}</span>
          <div class="evidence" data-tone=${evidence === "failed" ? "bad" : ["observed", "confirmed"].includes(evidence) ? "ok" : "muted"}>
            <ha-icon icon=${evidence === "confirmed" ? "mdi:check-circle-outline" : evidence === "observed" ? "mdi:thermometer" : evidence === "failed" ? "mdi:alert-circle-outline" : "mdi:message-processing-outline"}></ha-icon>
            <h3>${latest ? evidenceLabel : t3("No result yet", "暂无结果")}</h3>
          </div>
          ${facts?.sources.length ? b2`<p class="source">${t3("Source at the time of the reply: ", "回复时的来源：")}${facts.sources.join(" · ")}</p>` : A}
          ${evidence === "reply" ? b2`<p class="source">${t3("This record contains a text reply. Speaker playback is recorded separately.", "这里记录了文字回复，扬声器播放需要独立的播放记录。")}</p>` : A}
          <div class="next-step"><span class="eyebrow">${t3("DOES THIS NEED YOU?", "需要你做什么")}</span><p>${guidance}</p></div>
          ${live.phase === "paused" || live.phase === "offline" ? b2`<button class="quiet" @click=${() => this.navigate("settings")}>${t3("Voice settings", "语音设置")} <ha-icon icon="mdi:arrow-top-right"></ha-icon></button>` : A}
        </section>
      </div>
      <details class="surface diagnostics">
        <summary>${t3("System details", "系统详情")}<span>${t3("Measurements, connections and diagnostics", "测量、连接与诊断")}</span></summary>
        ${this.diagnostics(runs)}
        <slot name="diagnostics"></slot>
        <details class="memory"><summary>${t3("Conversation memory", "对话记忆")}</summary><slot name="memory"></slot></details>
      </details>
    `;
  }
  diagnostics(runs) {
    const t3 = this.text.bind(this);
    const metrics = observedMetrics(runs);
    const snapshot = object(this.satellite.diagnostic_snapshot);
    const wake = records(snapshot.event_stream).filter((event) => /wake/.test(String(event.type))).at(-1);
    const wakeTime = wake?.timestamp || object(snapshot.wake).last_detected_at;
    const format = (value, suffix) => value === null ? "—" : new Intl.NumberFormat(this.language, { maximumFractionDigits: suffix === "ms" ? 0 : 1 }).format(value) + suffix;
    const loaded = this.entries.some((entry) => entry.state === "loaded");
    return b2`
      <div class="metrics">
        <voice-harness-stat .label=${t3("Median response", "响应中位数")} .value=${format(metrics.medianMs, "ms")} .values=${metrics.latencies} .hint=${t3("Retained live conversations", "已保留的实际对话")} icon="mdi:timer-outline"></voice-harness-stat>
        <voice-harness-stat .label=${t3("Replies completed", "回答完成率")} .value=${format(metrics.successRate, "%")} .values=${metrics.outcomes} .hint=${t3("Reply outcome only", "仅描述回答结果")} icon="mdi:check-circle-outline"></voice-harness-stat>
        <voice-harness-stat .label=${t3("Error rate", "错误率")} .value=${format(metrics.errorRate, "%")} .values=${metrics.errors} .hint=${String(metrics.count) + t3(" completed conversations", " 次已结束对话")} icon="mdi:pulse"></voice-harness-stat>
        <voice-harness-stat .label=${t3("Last wake", "最近唤醒")} .value=${typeof wakeTime === "string" && Number.isFinite(Date.parse(wakeTime)) ? new Date(wakeTime).toLocaleTimeString(this.language, { hour: "2-digit", minute: "2-digit" }) : "—"} .hint=${t3("Satellite timestamp", "卫星时间戳")} icon="mdi:microphone-outline"></voice-harness-stat>
      </div>
      <p class="system-state">${loaded ? t3("Gateway loaded", "网关已加载") : t3("Gateway state unknown", "网关状态未知")} · ${t3("Connection checks and missing measurements follow below.", "连接检查与缺失测量见下方。")}</p>
    `;
  }
  navigate(destination) {
    this.dispatchEvent(new CustomEvent("harness-overview-navigate", { bubbles: true, composed: true, detail: { destination } }));
  }
  static styles = [harnessFoundationStyles, harnessButtonStyles, harnessSurfaceStyles, i`
    :host { display: grid; gap: 24px; }
    .intro { margin: 0 0 4px; }
    .intro h2 { margin-top: 9px; }
    .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
    .dot[data-active="true"] { background: var(--vh-accent); animation: breathe 1.8s ease-in-out infinite; }
    .conversation-grid { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(280px, 1fr); gap: 22px; }
    .conversation { padding: 32px; background: radial-gradient(ellipse at top left, color-mix(in srgb, var(--vh-accent) 6%, transparent), transparent 70%), var(--vh-surface); }
    .conversation .section-head { align-items: center; }
    time { font-size: 12px; color: var(--vh-muted); font-variant-numeric: tabular-nums; }
    .utterance { margin: 34px 0 28px; font-size: clamp(24px, 2.5vw, 34px); font-weight: 500; line-height: 1.55; letter-spacing: -.025em; overflow-wrap: anywhere; }
    .resolved { display: grid; gap: 5px; font-size: 15px; line-height: 1.65; margin: -10px 0 28px; }
    .resolved span { color: var(--vh-muted); font-size: 12px; }
    .reply { border-top: 1px solid var(--vh-line); padding-top: 24px; }
    .reply p { font-size: 17px; line-height: 1.8; margin: 14px 0 24px; white-space: pre-wrap; overflow-wrap: anywhere; }
    .conversation button { padding-left: 0; color: var(--vh-accent); }
    .reality { padding: 32px; }
    .evidence { display: flex; gap: 12px; align-items: flex-start; margin: 24px 0 16px; }
    .evidence ha-icon { color: var(--vh-muted); width: 24px; height: 24px; flex-shrink: 0; }
    .evidence[data-tone="ok"] ha-icon { color: var(--success-color, #43806c); }
    .evidence[data-tone="bad"] ha-icon { color: var(--error-color, #b54747); }
    .evidence h3 { margin: 0; font-size: 20px; font-weight: 550; line-height: 1.5; }
    .source { color: var(--vh-muted); font-size: 13px; line-height: 1.75; overflow-wrap: anywhere; }
    .next-step { border-top: 1px solid var(--vh-line); padding-top: 24px; margin-top: 30px; }
    .next-step p { font-size: 15px; line-height: 1.8; margin: 12px 0 0; }
    .reality button { margin-top: 16px; }
    .diagnostics { padding: 0 26px; background: transparent; }
    summary { min-height: 60px; padding: 18px 0; font-size: 14px; font-weight: 550; cursor: pointer; }
    summary span { color: var(--vh-muted); font-size: 12px; font-weight: 400; margin-left: 18px; }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 6px 0 20px; }
    .system-state { color: var(--vh-muted); font-size: 12px; margin-bottom: 24px; }
    .memory { border-top: 1px solid var(--vh-line); }
    ::slotted(*) { display: block; padding-bottom: 20px; }
    @keyframes breathe { 50% { opacity: .35; transform: scale(.8); } }
    @media (max-width: 850px) { .conversation-grid { grid-template-columns: 1fr; } .metrics { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 600px) { :host { gap: 18px; } .conversation-grid { gap: 16px; } .conversation, .reality { padding: 24px 20px; } .utterance { margin-top: 24px; font-size: 26px; } .diagnostics { padding: 0 18px; } summary span { display: none; } .metrics { gap: 10px; } .next-step { margin-top: 22px; } }
    @media (prefers-reduced-motion: reduce) { .dot { animation: none !important; } }
  `];
}
if (!customElements.get("voice-harness-overview"))
  customElements.define("voice-harness-overview", VoiceHarnessOverview);
// node_modules/diff/libesm/diff/base.js
class Diff {
  diff(oldStr, newStr, options = {}) {
    let callback;
    if (typeof options === "function") {
      callback = options;
      options = {};
    } else if ("callback" in options) {
      callback = options.callback;
    }
    const oldString = this.castInput(oldStr, options);
    const newString = this.castInput(newStr, options);
    const oldTokens = this.removeEmpty(this.tokenize(oldString, options));
    const newTokens = this.removeEmpty(this.tokenize(newString, options));
    return this.diffWithOptionsObj(oldTokens, newTokens, options, callback);
  }
  diffWithOptionsObj(oldTokens, newTokens, options, callback) {
    var _a;
    const done = (value) => {
      value = this.postProcess(value, options);
      if (callback) {
        setTimeout(function() {
          callback(value);
        }, 0);
        return;
      } else {
        return value;
      }
    };
    const newLen = newTokens.length, oldLen = oldTokens.length;
    let editLength = 1;
    let maxEditLength = newLen + oldLen;
    if (options.maxEditLength != null) {
      maxEditLength = Math.min(maxEditLength, options.maxEditLength);
    }
    const maxExecutionTime = (_a = options.timeout) !== null && _a !== undefined ? _a : Infinity;
    const abortAfterTimestamp = Date.now() + maxExecutionTime;
    const bestPath = [{ oldPos: -1, lastComponent: undefined }];
    let newPos = this.extractCommon(bestPath[0], newTokens, oldTokens, 0, options);
    if (bestPath[0].oldPos + 1 >= oldLen && newPos + 1 >= newLen) {
      return done(this.buildValues(bestPath[0].lastComponent, newTokens, oldTokens));
    }
    let minDiagonalToConsider = -Infinity, maxDiagonalToConsider = Infinity;
    const execEditLength = () => {
      for (let diagonalPath = Math.max(minDiagonalToConsider, -editLength);diagonalPath <= Math.min(maxDiagonalToConsider, editLength); diagonalPath += 2) {
        let basePath;
        const removePath = bestPath[diagonalPath - 1], addPath = bestPath[diagonalPath + 1];
        if (removePath) {
          bestPath[diagonalPath - 1] = undefined;
        }
        let canAdd = false;
        if (addPath) {
          const addPathNewPos = addPath.oldPos - diagonalPath;
          canAdd = addPath && 0 <= addPathNewPos && addPathNewPos < newLen;
        }
        const canRemove = removePath && removePath.oldPos + 1 < oldLen;
        if (!canAdd && !canRemove) {
          bestPath[diagonalPath] = undefined;
          continue;
        }
        if (!canRemove || canAdd && removePath.oldPos < addPath.oldPos) {
          basePath = this.addToPath(addPath, true, false, 0, options);
        } else {
          basePath = this.addToPath(removePath, false, true, 1, options);
        }
        newPos = this.extractCommon(basePath, newTokens, oldTokens, diagonalPath, options);
        if (basePath.oldPos + 1 >= oldLen && newPos + 1 >= newLen) {
          return done(this.buildValues(basePath.lastComponent, newTokens, oldTokens)) || true;
        } else {
          bestPath[diagonalPath] = basePath;
          if (basePath.oldPos + 1 >= oldLen) {
            maxDiagonalToConsider = Math.min(maxDiagonalToConsider, diagonalPath - 1);
          }
          if (newPos + 1 >= newLen) {
            minDiagonalToConsider = Math.max(minDiagonalToConsider, diagonalPath + 1);
          }
        }
      }
      editLength++;
    };
    if (callback) {
      (function exec() {
        setTimeout(function() {
          if (editLength > maxEditLength || Date.now() > abortAfterTimestamp) {
            return callback(undefined);
          }
          if (!execEditLength()) {
            exec();
          }
        }, 0);
      })();
    } else {
      while (editLength <= maxEditLength && Date.now() <= abortAfterTimestamp) {
        const ret = execEditLength();
        if (ret) {
          return ret;
        }
      }
    }
  }
  addToPath(path, added, removed, oldPosInc, options) {
    const last = path.lastComponent;
    if (last && !options.oneChangePerToken && last.added === added && last.removed === removed) {
      return {
        oldPos: path.oldPos + oldPosInc,
        lastComponent: { count: last.count + 1, added, removed, previousComponent: last.previousComponent }
      };
    } else {
      return {
        oldPos: path.oldPos + oldPosInc,
        lastComponent: { count: 1, added, removed, previousComponent: last }
      };
    }
  }
  extractCommon(basePath, newTokens, oldTokens, diagonalPath, options) {
    const newLen = newTokens.length, oldLen = oldTokens.length;
    let oldPos = basePath.oldPos, newPos = oldPos - diagonalPath, commonCount = 0;
    while (newPos + 1 < newLen && oldPos + 1 < oldLen && this.equals(oldTokens[oldPos + 1], newTokens[newPos + 1], options)) {
      newPos++;
      oldPos++;
      commonCount++;
      if (options.oneChangePerToken) {
        basePath.lastComponent = { count: 1, previousComponent: basePath.lastComponent, added: false, removed: false };
      }
    }
    if (commonCount && !options.oneChangePerToken) {
      basePath.lastComponent = { count: commonCount, previousComponent: basePath.lastComponent, added: false, removed: false };
    }
    basePath.oldPos = oldPos;
    return newPos;
  }
  equals(left, right, options) {
    if (options.comparator) {
      return options.comparator(left, right);
    } else {
      return left === right || !!options.ignoreCase && left.toLowerCase() === right.toLowerCase();
    }
  }
  removeEmpty(array2) {
    const ret = [];
    for (let i5 = 0;i5 < array2.length; i5++) {
      if (array2[i5]) {
        ret.push(array2[i5]);
      }
    }
    return ret;
  }
  castInput(value, options) {
    return value;
  }
  tokenize(value, options) {
    return Array.from(value);
  }
  join(chars) {
    return chars.join("");
  }
  postProcess(changeObjects, options) {
    return changeObjects;
  }
  get useLongestToken() {
    return false;
  }
  buildValues(lastComponent, newTokens, oldTokens) {
    const components = [];
    let nextComponent;
    while (lastComponent) {
      components.push(lastComponent);
      nextComponent = lastComponent.previousComponent;
      delete lastComponent.previousComponent;
      lastComponent = nextComponent;
    }
    components.reverse();
    const componentLen = components.length;
    let componentPos = 0, newPos = 0, oldPos = 0;
    for (;componentPos < componentLen; componentPos++) {
      const component = components[componentPos];
      if (!component.removed) {
        if (!component.added && this.useLongestToken) {
          let value = newTokens.slice(newPos, newPos + component.count);
          value = value.map(function(value2, i5) {
            const oldValue = oldTokens[oldPos + i5];
            return oldValue.length > value2.length ? oldValue : value2;
          });
          component.value = this.join(value);
        } else {
          component.value = this.join(newTokens.slice(newPos, newPos + component.count));
        }
        newPos += component.count;
        if (!component.added) {
          oldPos += component.count;
        }
      } else {
        component.value = this.join(oldTokens.slice(oldPos, oldPos + component.count));
        oldPos += component.count;
      }
    }
    return components;
  }
}

// node_modules/diff/libesm/util/string.js
function longestCommonPrefix(str1, str2) {
  let i5;
  for (i5 = 0;i5 < str1.length && i5 < str2.length; i5++) {
    if (str1[i5] != str2[i5]) {
      return str1.slice(0, i5);
    }
  }
  return str1.slice(0, i5);
}
function longestCommonSuffix(str1, str2) {
  let i5;
  if (!str1 || !str2 || str1[str1.length - 1] != str2[str2.length - 1]) {
    return "";
  }
  for (i5 = 0;i5 < str1.length && i5 < str2.length; i5++) {
    if (str1[str1.length - (i5 + 1)] != str2[str2.length - (i5 + 1)]) {
      return str1.slice(-i5);
    }
  }
  return str1.slice(-i5);
}
function replacePrefix(string2, oldPrefix, newPrefix) {
  if (string2.slice(0, oldPrefix.length) != oldPrefix) {
    throw Error(`string ${JSON.stringify(string2)} doesn't start with prefix ${JSON.stringify(oldPrefix)}; this is a bug`);
  }
  return newPrefix + string2.slice(oldPrefix.length);
}
function replaceSuffix(string2, oldSuffix, newSuffix) {
  if (!oldSuffix) {
    return string2 + newSuffix;
  }
  if (string2.slice(-oldSuffix.length) != oldSuffix) {
    throw Error(`string ${JSON.stringify(string2)} doesn't end with suffix ${JSON.stringify(oldSuffix)}; this is a bug`);
  }
  return string2.slice(0, -oldSuffix.length) + newSuffix;
}
function removePrefix(string2, oldPrefix) {
  return replacePrefix(string2, oldPrefix, "");
}
function removeSuffix(string2, oldSuffix) {
  return replaceSuffix(string2, oldSuffix, "");
}
function maximumOverlap(string1, string2) {
  return string2.slice(0, overlapCount(string1, string2));
}
function overlapCount(a3, b3) {
  let startA = 0;
  if (a3.length > b3.length) {
    startA = a3.length - b3.length;
  }
  let endB = b3.length;
  if (a3.length < b3.length) {
    endB = a3.length;
  }
  const map = Array(endB);
  let k2 = 0;
  map[0] = 0;
  for (let j2 = 1;j2 < endB; j2++) {
    if (b3[j2] == b3[k2]) {
      map[j2] = map[k2];
    } else {
      map[j2] = k2;
    }
    while (k2 > 0 && b3[j2] != b3[k2]) {
      k2 = map[k2];
    }
    if (b3[j2] == b3[k2]) {
      k2++;
    }
  }
  k2 = 0;
  for (let i5 = startA;i5 < a3.length; i5++) {
    while (k2 > 0 && a3[i5] != b3[k2]) {
      k2 = map[k2];
    }
    if (a3[i5] == b3[k2]) {
      k2++;
    }
  }
  return k2;
}
function segment(string2, segmenter) {
  const parts = [];
  for (const segmentObj of Array.from(segmenter.segment(string2))) {
    const segment2 = segmentObj.segment;
    if (parts.length && /\s/.test(parts[parts.length - 1]) && /\s/.test(segment2)) {
      parts[parts.length - 1] += segment2;
    } else {
      parts.push(segment2);
    }
  }
  return parts;
}
function trailingWs(string2, segmenter) {
  if (segmenter) {
    return leadingAndTrailingWs(string2, segmenter)[1];
  }
  let i5;
  for (i5 = string2.length - 1;i5 >= 0; i5--) {
    if (!string2[i5].match(/\s/)) {
      break;
    }
  }
  return string2.substring(i5 + 1);
}
function leadingWs(string2, segmenter) {
  if (segmenter) {
    return leadingAndTrailingWs(string2, segmenter)[0];
  }
  const match = string2.match(/^\s*/);
  return match ? match[0] : "";
}
function leadingAndTrailingWs(string2, segmenter) {
  if (!segmenter) {
    return [leadingWs(string2), trailingWs(string2)];
  }
  if (segmenter.resolvedOptions().granularity != "word") {
    throw new Error('The segmenter passed must have a granularity of "word"');
  }
  const segments = segment(string2, segmenter);
  const firstSeg = segments[0];
  const lastSeg = segments[segments.length - 1];
  const head = /\s/.test(firstSeg) ? firstSeg : "";
  const tail = /\s/.test(lastSeg) ? lastSeg : "";
  return [head, tail];
}

// node_modules/diff/libesm/diff/word.js
var extendedWordChars = "a-zA-Z0-9_\\u{AD}\\u{C0}-\\u{D6}\\u{D8}-\\u{F6}\\u{F8}-\\u{2C6}\\u{2C8}-\\u{2D7}\\u{2DE}-\\u{2FF}\\u{1E00}-\\u{1EFF}";
var tokenizeIncludingWhitespace = new RegExp(`[${extendedWordChars}]+|\\s+|[^${extendedWordChars}]`, "ug");

class WordDiff extends Diff {
  equals(left, right, options) {
    if (options.ignoreCase) {
      left = left.toLowerCase();
      right = right.toLowerCase();
    }
    return left.trim() === right.trim();
  }
  tokenize(value, options = {}) {
    let parts;
    if (options.intlSegmenter) {
      const segmenter = options.intlSegmenter;
      if (segmenter.resolvedOptions().granularity != "word") {
        throw new Error('The segmenter passed must have a granularity of "word"');
      }
      parts = segment(value, segmenter);
    } else {
      parts = value.match(tokenizeIncludingWhitespace) || [];
    }
    const tokens = [];
    let prevPart = null;
    parts.forEach((part) => {
      if (/\s/.test(part)) {
        if (prevPart == null) {
          tokens.push(part);
        } else {
          tokens.push(tokens.pop() + part);
        }
      } else if (prevPart != null && /\s/.test(prevPart)) {
        if (tokens[tokens.length - 1] == prevPart) {
          tokens.push(tokens.pop() + part);
        } else {
          tokens.push(prevPart + part);
        }
      } else {
        tokens.push(part);
      }
      prevPart = part;
    });
    return tokens;
  }
  join(tokens) {
    return tokens.map((token, i5) => {
      if (i5 == 0) {
        return token;
      } else {
        return token.replace(/^\s+/, "");
      }
    }).join("");
  }
  postProcess(changes, options) {
    if (!changes || options.oneChangePerToken) {
      return changes;
    }
    let lastKeep = null;
    let insertion = null;
    let deletion = null;
    changes.forEach((change) => {
      if (change.added) {
        insertion = change;
      } else if (change.removed) {
        deletion = change;
      } else {
        if (insertion || deletion) {
          dedupeWhitespaceInChangeObjects(lastKeep, deletion, insertion, change, options.intlSegmenter);
        }
        lastKeep = change;
        insertion = null;
        deletion = null;
      }
    });
    if (insertion || deletion) {
      dedupeWhitespaceInChangeObjects(lastKeep, deletion, insertion, null, options.intlSegmenter);
    }
    return changes;
  }
}
var wordDiff = new WordDiff;
function dedupeWhitespaceInChangeObjects(startKeep, deletion, insertion, endKeep, segmenter) {
  if (deletion && insertion) {
    const [oldWsPrefix, oldWsSuffix] = leadingAndTrailingWs(deletion.value, segmenter);
    const [newWsPrefix, newWsSuffix] = leadingAndTrailingWs(insertion.value, segmenter);
    if (startKeep) {
      const commonWsPrefix = longestCommonPrefix(oldWsPrefix, newWsPrefix);
      startKeep.value = replaceSuffix(startKeep.value, newWsPrefix, commonWsPrefix);
      deletion.value = removePrefix(deletion.value, commonWsPrefix);
      insertion.value = removePrefix(insertion.value, commonWsPrefix);
    }
    if (endKeep) {
      const commonWsSuffix = longestCommonSuffix(oldWsSuffix, newWsSuffix);
      endKeep.value = replacePrefix(endKeep.value, newWsSuffix, commonWsSuffix);
      deletion.value = removeSuffix(deletion.value, commonWsSuffix);
      insertion.value = removeSuffix(insertion.value, commonWsSuffix);
    }
  } else if (insertion) {
    if (startKeep) {
      const ws = leadingWs(insertion.value, segmenter);
      insertion.value = insertion.value.substring(ws.length);
    }
    if (endKeep) {
      const ws = leadingWs(endKeep.value, segmenter);
      endKeep.value = endKeep.value.substring(ws.length);
    }
  } else if (startKeep && endKeep) {
    const newWsFull = leadingWs(endKeep.value, segmenter), [delWsStart, delWsEnd] = leadingAndTrailingWs(deletion.value, segmenter);
    const newWsStart = longestCommonPrefix(newWsFull, delWsStart);
    deletion.value = removePrefix(deletion.value, newWsStart);
    const newWsEnd = longestCommonSuffix(removePrefix(newWsFull, newWsStart), delWsEnd);
    deletion.value = removeSuffix(deletion.value, newWsEnd);
    endKeep.value = replacePrefix(endKeep.value, newWsFull, newWsEnd);
    startKeep.value = replaceSuffix(startKeep.value, newWsFull, newWsFull.slice(0, newWsFull.length - newWsEnd.length));
  } else if (endKeep) {
    const endKeepWsPrefix = leadingWs(endKeep.value, segmenter);
    const deletionWsSuffix = trailingWs(deletion.value, segmenter);
    const overlap = maximumOverlap(deletionWsSuffix, endKeepWsPrefix);
    deletion.value = removeSuffix(deletion.value, overlap);
  } else if (startKeep) {
    const startKeepWsSuffix = trailingWs(startKeep.value, segmenter);
    const deletionWsPrefix = leadingWs(deletion.value, segmenter);
    const overlap = maximumOverlap(startKeepWsSuffix, deletionWsPrefix);
    deletion.value = removePrefix(deletion.value, overlap);
  }
}

class WordsWithSpaceDiff extends Diff {
  tokenize(value) {
    const regex = new RegExp(`(\\r?\\n)|[${extendedWordChars}]+|[^\\S\\n\\r]+|[^${extendedWordChars}]`, "ug");
    return value.match(regex) || [];
  }
}
var wordsWithSpaceDiff = new WordsWithSpaceDiff;
function diffWordsWithSpace(oldStr, newStr, options) {
  return wordsWithSpaceDiff.diff(oldStr, newStr, options);
}

// node_modules/diff/libesm/diff/line.js
class LineDiff extends Diff {
  constructor() {
    super(...arguments);
    this.tokenize = tokenize;
  }
  equals(left, right, options) {
    if (options.ignoreWhitespace) {
      if (!options.newlineIsToken || !left.includes(`
`)) {
        left = left.trim();
      }
      if (!options.newlineIsToken || !right.includes(`
`)) {
        right = right.trim();
      }
    } else if (options.ignoreNewlineAtEof && !options.newlineIsToken) {
      if (left.endsWith(`
`)) {
        left = left.slice(0, -1);
      }
      if (right.endsWith(`
`)) {
        right = right.slice(0, -1);
      }
    }
    return super.equals(left, right, options);
  }
}
var lineDiff = new LineDiff;
function diffLines(oldStr, newStr, options) {
  return lineDiff.diff(oldStr, newStr, options);
}
function tokenize(value, options) {
  if (options.stripTrailingCr) {
    value = value.replace(/\r\n/g, `
`);
  }
  const retLines = [], linesAndNewlines = value.split(/(\n|\r\n)/);
  if (!linesAndNewlines[linesAndNewlines.length - 1]) {
    linesAndNewlines.pop();
  }
  for (let i5 = 0;i5 < linesAndNewlines.length; i5++) {
    const line = linesAndNewlines[i5];
    if (i5 % 2 && !options.newlineIsToken) {
      retLines[retLines.length - 1] += line;
    } else {
      retLines.push(line);
    }
  }
  return retLines;
}
// custom_components/llm_gateway/frontend/voice-harness-replay-diff.ts
function object2(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
function runId(record) {
  return String(record.run_id || record.id || "");
}
function resolveReplayPair(records2, selected) {
  const forks = records2.filter((record) => object2(record.lineage).mode === "dry_run");
  const fork = selected?.forkId ? forks.find((record) => runId(record) === selected.forkId) : forks[0];
  if (!fork)
    return null;
  const lineage = object2(fork.lineage);
  const sourceId = String(selected?.sourceId || lineage.replay_of || "");
  const source = records2.find((record) => runId(record) === sourceId);
  if (!source)
    return null;
  return { source, fork, sourceId, forkId: runId(fork) };
}
function stable(value) {
  if (Array.isArray(value)) {
    return `[
${value.map((item) => `  ${stable(item)}`).join(`,
`)}
]`;
  }
  if (value && typeof value === "object") {
    const record = value;
    return `{
${Object.keys(record).sort().map((key) => `  ${JSON.stringify(key)}: ${stable(record[key])}`).join(`,
`)}
}`;
  }
  return JSON.stringify(value ?? null);
}
function timeline(record) {
  const spans = record.timeline_spans;
  const events = Array.isArray(spans) && spans.length ? spans : record.timeline;
  return Array.isArray(events) ? events.map((item) => {
    const event = object2(item);
    return {
      stage: event.stage,
      status: event.status,
      start_ms: event.start_ms ?? event.t_ms,
      duration_ms: event.duration_ms ?? 0
    };
  }) : [];
}
function actions(record) {
  if (Array.isArray(record.proposed_actions))
    return record.proposed_actions;
  const raw = object2(record.raw_payload);
  return Array.isArray(raw.proposed_actions) ? raw.proposed_actions : [];
}
function speech(record) {
  const speechValue = object2(record.speech);
  return String(speechValue.final || record.final_speech_text || record.assistant_text || "");
}
function replayDiffSections(source, fork) {
  const values = [
    ["route", object2(source.route), object2(fork.route)],
    ["actions", actions(source), actions(fork)],
    ["speech", speech(source), speech(fork)],
    ["events", timeline(source), timeline(fork)]
  ];
  return values.map(([id, before, after]) => {
    const left = typeof before === "string" ? before : stable(before);
    const right = typeof after === "string" ? after : stable(after);
    return {
      id,
      changed: left !== right,
      parts: id === "speech" ? diffWordsWithSpace(left, right) : diffLines(`${left}
`, `${right}
`)
    };
  });
}

// custom_components/llm_gateway/frontend/voice-harness-replay-inspector.ts
class VoiceHarnessReplayInspector extends i4 {
  static properties = {
    pair: { attribute: false },
    language: { type: String },
    labels: { attribute: false }
  };
  constructor() {
    super();
    this.pair = null;
    this.language = "en";
    this.labels = {};
  }
  render() {
    if (!this.pair)
      return A;
    const sections = replayDiffSections(this.pair.source, this.pair.fork);
    const changed = sections.filter((section) => section.changed).length;
    const t3 = (en, zh) => this.language.startsWith("zh") ? zh : en;
    return b2`
      <section>
        <header>
          <div><span class="eyebrow">REPLAY DIFF</span><strong>${t3("Response comparison", "回答差异对比")}</strong></div>
          <span class=${changed ? "chip warning" : "chip ok"}>${changed} ${t3("changed sections", "处变化")}</span>
        </header>
        <div class="lineage">
          <span>${this.pair.sourceId}</span><b aria-hidden="true">→</b><span>${this.pair.forkId}</span>
        </div>
        <div class="sections">
          ${sections.map((item) => b2`
            <details class="diff" ?open=${item.changed}>
              <summary>
                <strong>${this.labels[item.id] || item.id}</strong>
                <span class=${item.changed ? "chip warning" : "chip muted"}>
                  ${item.changed ? t3("Changed", "有变化") : t3("Unchanged", "无变化")}
                </span>
              </summary>
              <pre>${item.parts.map((part) => b2`<span class=${part.added ? "added" : part.removed ? "removed" : "same"}>${part.value}</span>`)}</pre>
            </details>
          `)}
        </div>
      </section>
    `;
  }
  static styles = [harnessFoundationStyles, i`
    :host { display: block; margin: 14px 0; color: var(--primary-text-color); }
    section { overflow: hidden; border: 1px solid var(--divider-color); border-radius: 18px; background: var(--card-background-color); }
    header { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 48px; padding: 0 12px; border-bottom: 1px solid var(--divider-color); }
    header > div { display: grid; gap: 2px; }
    .eyebrow { color: var(--secondary-text-color); font-size: 10px; font-weight: 650; letter-spacing: .04em; text-transform: uppercase; }
    .chip { display: inline-flex; align-items: center; min-height: 20px; padding: 0 7px; border-radius: 999px; font-size: 10px; font-weight: 650; }
    .warning { background: color-mix(in srgb, var(--warning-color, #f9a825) 16%, transparent); color: var(--warning-color, #a66a00); }
    .ok { background: color-mix(in srgb, var(--success-color, #43a047) 15%, transparent); color: var(--success-color, #2e7d32); }
    .muted { background: color-mix(in srgb, var(--secondary-text-color) 11%, transparent); color: var(--secondary-text-color); }
    .lineage { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid var(--divider-color); color: var(--secondary-text-color); font-family: var(--code-font-family, Menlo, Consolas, monospace); font-size: 10px; }
    .lineage span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .lineage b { color: var(--primary-color); }
    .sections { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .diff { min-width: 0; border-right: 1px solid var(--divider-color); border-bottom: 1px solid var(--divider-color); }
    .diff:nth-child(2n) { border-right: 0; }
    summary { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 48px; padding: 0 10px; cursor: pointer; font-size: 11px; }
    pre { max-height: 220px; margin: 0; padding: 8px 10px; overflow: auto; border-top: 1px solid var(--divider-color); background: var(--primary-background-color); font: 12px/1.75 var(--code-font-family, Menlo, Consolas, monospace); white-space: pre-wrap; }
    pre span { display: inline; }
    .added { background: color-mix(in srgb, var(--success-color, #43a047) 16%, transparent); color: var(--success-color, #2e7d32); }
    .removed { background: color-mix(in srgb, var(--error-color) 13%, transparent); color: var(--error-color); text-decoration: line-through; }
    @media (max-width: 560px) { .sections { grid-template-columns: 1fr; } .diff { border-right: 0; } }
  `];
}
if (!customElements.get("voice-harness-replay-inspector")) {
  customElements.define("voice-harness-replay-inspector", VoiceHarnessReplayInspector);
}

// custom_components/llm_gateway/frontend/voice-harness-run-list.ts
class VoiceHarnessRunList extends i4 {
  static properties = {
    items: { attribute: false },
    selected: { type: String }
  };
  constructor() {
    super();
    this.items = [];
    this.selected = "";
  }
  render() {
    return b2`
      <div role="listbox" aria-label="Voice Harness runs">
        ${this.items.map((item) => b2`
            <button
              aria-selected=${String(item.id === this.selected)}
              data-id=${item.id}
              role="option"
              tabindex=${item.id === this.selected ? "0" : "-1"}
              @click=${() => this.select(item.id)}
              @keydown=${this.onKeydown}
            >
              <span class="status ${item.status}" aria-hidden="true"></span>
              <span class="identity">
                <strong>${item.title}</strong>
                <small>${item.subtitle}</small>
              </span>
              <span class="facts"><small>${item.route}</small><small>${item.latency}</small></span>
            </button>
          `)}
      </div>
    `;
  }
  select(id) {
    this.dispatchEvent(new CustomEvent("harness-run-select", {
      bubbles: true,
      composed: true,
      detail: { id }
    }));
  }
  onKeydown(event) {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key))
      return;
    event.preventDefault();
    const current = this.items.findIndex((item2) => item2.id === this.selected);
    let next = current < 0 ? 0 : current;
    if (event.key === "Home")
      next = 0;
    if (event.key === "End")
      next = this.items.length - 1;
    if (event.key === "ArrowUp")
      next = (next - 1 + this.items.length) % this.items.length;
    if (event.key === "ArrowDown")
      next = (next + 1) % this.items.length;
    const item = this.items[next];
    if (!item)
      return;
    this.select(item.id);
    this.renderRoot.querySelector(`button[data-id="${CSS.escape(item.id)}"]`)?.focus();
  }
  static styles = [harnessFoundationStyles, harnessButtonStyles, i`
    :host { display: block; min-width: 0; }
    div { display: grid; gap: var(--vh-space-xs); }
    button { width: 100%; min-height: 64px; display: grid; grid-template-columns: 8px minmax(0, 1fr) auto; gap: var(--vh-space-s); align-items: center; padding: var(--vh-space-s); background: transparent; text-align: left; }
    button:hover { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
    button[aria-selected="true"] { background: color-mix(in srgb, var(--primary-color) 13%, var(--card-background-color)); }
    .status { width: 7px; height: 7px; border-radius: 50%; background: var(--secondary-text-color); }
    .status.ok { background: var(--success-color); }
    .status.warning { background: var(--warning-color); }
    .status.bad { background: var(--error-color); }
    .identity, .facts { min-width: 0; display: grid; gap: 3px; }
    strong, small { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    strong { font-size: 12px; }
    small { color: var(--secondary-text-color); font-size: 10px; }
    .facts { justify-items: end; }
  `];
}
if (!customElements.get("voice-harness-run-list")) {
  customElements.define("voice-harness-run-list", VoiceHarnessRunList);
}
// node_modules/lit-html/directive.js
var t3 = { ATTRIBUTE: 1, CHILD: 2, PROPERTY: 3, BOOLEAN_ATTRIBUTE: 4, EVENT: 5, ELEMENT: 6 };
var e4 = (t4) => (...e5) => ({ _$litDirective$: t4, values: e5 });

class i5 {
  constructor(t4) {}
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AT(t4, e5, i6) {
    this._$Ct = t4, this._$AM = e5, this._$Ci = i6;
  }
  _$AS(t4, e5) {
    return this.update(t4, e5);
  }
  update(t4, e5) {
    return this.render(...e5);
  }
}

// node_modules/lit-html/directives/unsafe-html.js
class e5 extends i5 {
  constructor(i6) {
    if (super(i6), this.it = A, i6.type !== t3.CHILD)
      throw Error(this.constructor.directiveName + "() can only be used in child bindings");
  }
  render(r4) {
    if (r4 === A || r4 == null)
      return this._t = undefined, this.it = r4;
    if (r4 === E)
      return r4;
    if (typeof r4 != "string")
      throw Error(this.constructor.directiveName + "() called with a non-string value");
    if (r4 === this.it)
      return this._t;
    this.it = r4;
    const s4 = [r4];
    return s4.raw = s4, this._t = { _$litType$: this.constructor.resultType, strings: s4, values: [] };
  }
}
e5.directiveName = "unsafeHTML", e5.resultType = 1;
var o5 = e4(e5);
// node_modules/lit-html/directive-helpers.js
var { I: t4 } = j;
var i6 = (o6) => o6;
var s4 = () => document.createComment("");
var v2 = (o6, n4, e6) => {
  const l3 = o6._$AA.parentNode, d3 = n4 === undefined ? o6._$AB : n4._$AA;
  if (e6 === undefined) {
    const i7 = l3.insertBefore(s4(), d3), n5 = l3.insertBefore(s4(), d3);
    e6 = new t4(i7, n5, o6, o6.options);
  } else {
    const t5 = e6._$AB.nextSibling, n5 = e6._$AM, c4 = n5 !== o6;
    if (c4) {
      let t6;
      e6._$AQ?.(o6), e6._$AM = o6, e6._$AP !== undefined && (t6 = o6._$AU) !== n5._$AU && e6._$AP(t6);
    }
    if (t5 !== d3 || c4) {
      let o7 = e6._$AA;
      for (;o7 !== t5; ) {
        const t6 = i6(o7).nextSibling;
        i6(l3).insertBefore(o7, d3), o7 = t6;
      }
    }
  }
  return e6;
};
var u3 = (o6, t5, i7 = o6) => (o6._$AI(t5, i7), o6);
var m2 = {};
var p3 = (o6, t5 = m2) => o6._$AH = t5;
var M2 = (o6) => o6._$AH;
var h3 = (o6) => {
  o6._$AR(), o6._$AA.remove();
};

// node_modules/lit-html/directives/repeat.js
var u4 = (e6, s5, t5) => {
  const r4 = new Map;
  for (let l3 = s5;l3 <= t5; l3++)
    r4.set(e6[l3], l3);
  return r4;
};
var c4 = e4(class extends i5 {
  constructor(e6) {
    if (super(e6), e6.type !== t3.CHILD)
      throw Error("repeat() can only be used in text expressions");
  }
  dt(e6, s5, t5) {
    let r4;
    t5 === undefined ? t5 = s5 : s5 !== undefined && (r4 = s5);
    const l3 = [], o6 = [];
    let i7 = 0;
    for (const s6 of e6)
      l3[i7] = r4 ? r4(s6, i7) : i7, o6[i7] = t5(s6, i7), i7++;
    return { values: o6, keys: l3 };
  }
  render(e6, s5, t5) {
    return this.dt(e6, s5, t5).values;
  }
  update(s5, [t5, r4, c5]) {
    const d3 = M2(s5), { values: p4, keys: a3 } = this.dt(t5, r4, c5);
    if (!Array.isArray(d3))
      return this.ut = a3, p4;
    const h4 = this.ut ??= [], v3 = [];
    let m3, y3, x2 = 0, j2 = d3.length - 1, k2 = 0, w2 = p4.length - 1;
    for (;x2 <= j2 && k2 <= w2; )
      if (d3[x2] === null)
        x2++;
      else if (d3[j2] === null)
        j2--;
      else if (h4[x2] === a3[k2])
        v3[k2] = u3(d3[x2], p4[k2]), x2++, k2++;
      else if (h4[j2] === a3[w2])
        v3[w2] = u3(d3[j2], p4[w2]), j2--, w2--;
      else if (h4[x2] === a3[w2])
        v3[w2] = u3(d3[x2], p4[w2]), v2(s5, v3[w2 + 1], d3[x2]), x2++, w2--;
      else if (h4[j2] === a3[k2])
        v3[k2] = u3(d3[j2], p4[k2]), v2(s5, d3[x2], d3[j2]), j2--, k2++;
      else if (m3 === undefined && (m3 = u4(a3, k2, w2), y3 = u4(h4, x2, j2)), m3.has(h4[x2]))
        if (m3.has(h4[j2])) {
          const e6 = y3.get(a3[k2]), t6 = e6 !== undefined ? d3[e6] : null;
          if (t6 === null) {
            const e7 = v2(s5, d3[x2]);
            u3(e7, p4[k2]), v3[k2] = e7;
          } else
            v3[k2] = u3(t6, p4[k2]), v2(s5, d3[x2], t6), d3[e6] = null;
          k2++;
        } else
          h3(d3[j2]), j2--;
      else
        h3(d3[x2]), x2++;
    for (;k2 <= w2; ) {
      const e6 = v2(s5, v3[w2 + 1]);
      u3(e6, p4[k2]), v3[k2++] = e6;
    }
    for (;x2 <= j2; ) {
      const e6 = d3[x2++];
      e6 !== null && h3(e6);
    }
    return this.ut = a3, p3(s5, v3), E;
  }
});
// custom_components/llm_gateway/frontend/voice-harness-runs.ts
var stageNames = {
  wake: ["Wake", "唤醒"],
  asr: ["Recognition", "识别"],
  llm: ["Gateway", "网关"],
  tts: ["Synthesis", "合成"],
  playback: ["Playback", "播放"],
  follow_up: ["Follow-up", "追问"]
};

class VoiceHarnessRuns extends i4 {
  static properties = {
    entries: { attribute: false },
    language: {},
    loadDetail: { attribute: false },
    replay: { attribute: false },
    filter: { state: true },
    query: { state: true },
    selected: { state: true },
    selection: { state: true },
    detailTab: { state: true },
    error: { state: true },
    loading: { state: true },
    audioUrl: { state: true },
    compareOpen: { state: true }
  };
  details = new Map;
  audioName = "";
  audioRate = 16000;
  audioChannels = 1;
  opener;
  constructor() {
    super();
    this.entries = [];
    this.language = "en";
    this.filter = "all";
    this.query = "";
    this.selected = null;
    this.selection = [];
    this.detailTab = "conversation";
    this.error = "";
    this.loading = false;
    this.audioUrl = "";
    this.compareOpen = false;
  }
  text(en, zh) {
    return this.language.startsWith("zh") ? zh : en;
  }
  get items() {
    return this.entries.flatMap((entry) => records(object(entry.traces).records).map((record) => ({
      entryId: String(entry.entry_id),
      record
    })));
  }
  key(item) {
    return item.entryId + ":" + idOf(item.record);
  }
  current(item) {
    return this.details.get(this.key(item)) || item.record;
  }
  label(record) {
    const status = runOutcome(record);
    return {
      answered: this.text("Answered", "已回答"),
      failed: this.text("Failed", "失败"),
      clarification: this.text("Clarification", "待澄清"),
      cancelled: this.text("Cancelled", "已取消"),
      running: this.text("In progress", "进行中"),
      unknown: this.text("Unknown", "未知")
    }[status];
  }
  filtered(item) {
    const record = item.record;
    const outcome = runOutcome(record);
    const query = this.query.trim().toLocaleLowerCase();
    return (!query || [
      record.user_text,
      speechOf(record),
      object(record.route).model,
      idOf(record)
    ].join(" ").toLocaleLowerCase().includes(query)) && (this.filter === "all" || this.filter === outcome || this.filter === "warning" && ["clarification", "cancelled", "unknown", "running"].includes(outcome) || this.filter === "slow" && (measurement(record.latency_ms) ?? -1) > 3000);
  }
  time(value) {
    const date = new Date(String(value));
    return Number.isFinite(date.getTime()) ? date.toLocaleString(this.language, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    }) : "—";
  }
  render() {
    const t5 = this.text.bind(this);
    const items = this.items.filter((item) => this.filtered(item));
    const selected = this.selected ? this.current(this.selected) : null;
    return b2`
      <div class="section-head">
        <div>
          <span class="eyebrow">VOICE HARNESS / ${t5("RUNS", "运行记录")}</span>
          <h2>
            ${t5("Every conversation has a story.", "每一段对话，都有迹可循。")}
          </h2>
          <p class="muted">
            ${t5("Follow the timing, the answer and the evidence behind it.", "沿着时间线，看见回应，也看见回应背后的证据。")}
          </p>
        </div>
        <span class="chip"
          >${this.items.length} ${t5("retained runs", "条保留记录")}</span
        >
      </div>
      <section class="surface run-surface">
        <div class="toolbar">
          <div class="filters" aria-label=${t5("Filter runs", "筛选运行记录")}>
            ${[
      ["all", t5("All", "全部")],
      ["answered", t5("Answered", "已回答")],
      ["warning", t5("Attention", "留意")],
      ["failed", t5("Failed", "失败")],
      ["slow", ">3s"]
    ].map(([id, label]) => b2`<button
                  class="filter"
                  aria-pressed=${String(this.filter === id)}
                  @click=${() => {
      this.filter = id;
    }}
                >
                  ${label}
                </button>`)}
          </div>
          <label class="search"
            ><span class="sr-only"
              >${t5("Search runs", "搜索对话、模型或 ID")}</span
            ><input
              type="search"
              .value=${this.query}
              @input=${(event) => {
      this.query = event.target.value;
    }}
              placeholder=${t5("Search conversations, models…", "搜索对话、模型…")}
          /></label>
        </div>
        ${this.selection.length ? b2`<div class="compare-bar">
                <span
                  >${this.selection.length}/2 ${t5("selected", "条已选")}</span
                ><button
                  class="primary"
                  ?disabled=${this.selection.length !== 2}
                  @click=${() => this.openComparison()}
                >
                  ${t5("Compare replies", "对比模型回答")}</button
                ><button
                  class="quiet"
                  @click=${() => {
      this.selection = [];
    }}
                >
                  ${t5("Clear", "清除")}
                </button>
              </div>` : A}
        <div class="list-head" aria-hidden="true">
          <span>${t5("Conversation", "对话")}</span
          ><span>${t5("Route / duration", "路由 / 耗时")}</span
          ><span>${t5("Outcome", "结果")}</span
          ><span>${t5("Compare", "对比")}</span>
        </div>
        <div class="run-list">
          ${c4(items, (item) => this.key(item), (item) => b2`
              <article class="run-row">
                <button
                  class="run-open"
                  @click=${(event) => this.open(item, event.currentTarget)}
                >
                  <span class=${"status-dot " + runTone(item.record)}></span
                  ><span class="identity"
                    ><strong
                      >${String(item.record.user_text || idOf(item.record))}</strong
                    ><small
                      >${this.time(item.record.created_at)}${object(item.record.lineage).mode === "dry_run" ? " · " + t5("Dry-run replay", "模拟重放") : ""}</small
                    ><span class="excerpt"
                      >${speechOf(item.record) || t5("No answer retained", "未保留回答")}</span
                    ></span
                  >
                  <span class="run-facts"
                    ><strong
                      >${String(object(item.record.route).kind || item.record.route || "—")}</strong
                    ><small
                      >${measurement(item.record.latency_ms) === null ? "—" : Number(item.record.latency_ms).toLocaleString(this.language) + " ms"}</small
                    ></span
                  >
                  <span class=${"chip " + runTone(item.record)}
                    >${this.label(item.record)}</span
                  >
                </button>
                <button
                  class="compare-pick quiet"
                  aria-label=${t5("Select for comparison: ", "选择对比：") + String(item.record.user_text || idOf(item.record))}
                  aria-pressed=${String(this.selection.some((value) => this.key(value) === this.key(item)))}
                  @click=${() => this.toggleCompare(item)}
                >
                  <ha-icon icon="mdi:compare-horizontal"></ha-icon
                  ><span class="mobile-compare">${t5("Compare", "对比")}</span>
                </button>
              </article>
            `)}
        </div>
        ${!items.length ? b2`<div class="empty">
                <ha-icon icon="mdi:message-outline"></ha-icon>
                <h3>${t5("A quiet moment", "这里暂时很安静")}</h3>
                <p>
                  ${this.query || this.filter !== "all" ? t5("No runs match these filters.", "没有符合当前筛选的记录。") : t5("Retained voice runs appear here. Enable diagnostic traces in Settings to capture the next conversation.", "保留的语音运行会出现在这里。可在设置中开启诊断记录，观察下一段对话。")}
                </p>
              </div>` : A}
      </section>
      <dialog
        aria-labelledby="inspector-title"
        @cancel=${() => this.close()}
        @click=${(event) => {
      if (event.target === event.currentTarget) {
        const bounds = event.currentTarget.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right)
          this.close();
      }
    }}
      >
        <header class="drawer-header">
          <div>
            <span class="eyebrow"
              >${this.compareOpen ? "REPLAY DIFF" : "TRACE INSPECTOR"}</span
            >
            <h3 id="inspector-title">
              ${this.compareOpen ? t5("Two perspectives, side by side", "两次回应，一目了然") : t5("Inside the conversation", "走进这段对话")}
            </h3>
          </div>
          <button
            class="quiet"
            aria-label=${t5("Close inspector", "关闭检查抽屉")}
            @click=${() => this.close()}
          >
            ✕
          </button>
        </header>
        <div class="drawer-body">
          ${this.error ? b2`<p class="error" role="alert">${this.error}</p>` : A}
          ${this.loading ? b2`<p role="status" class="muted">${t5("Loading observed evidence…", "正在读取观测证据…")}</p>` : A}
          ${this.compareOpen ? this.comparison() : selected ? this.detail(selected) : A}
        </div>
      </dialog>
    `;
  }
  detail(record) {
    const t5 = this.text.bind(this);
    const usage = object(record.usage);
    return b2`
      <div class="detail-summary">
        <span class=${"chip " + runTone(record)}>${this.label(record)}</span
        ><span class="muted">${this.time(record.created_at)}</span
        ><span class="chip">${String(object(record.route).model || "—")}</span>
      </div>
      <h2 class="question">
        ${String(record.user_text || object(record.input).text || "—")}
      </h2>
      <nav
        class="detail-tabs"
        aria-label=${t5("Run detail sections", "运行详情分组")}
      >
        ${[
      ["conversation", t5("Conversation", "对话")],
      ["evidence", t5("Evidence", "证据")],
      ["audio", t5("Audio", "音频")],
      ["json", "JSON"]
    ].map(([id, label]) => b2`<button
              aria-pressed=${String(this.detailTab === id)}
              @click=${() => {
      this.detailTab = id;
    }}
            >
              ${label}
            </button>`)}
      </nav>
      <section
        ?hidden=${this.detailTab !== "conversation"}
        class="conversation"
      >
        <div class="bubble user">
          <small>${t5("You", "你")}</small>
          <p>${String(record.user_text || "—")}</p>
        </div>
        <div class="bubble assistant">
          <small>${t5("Assistant", "助手")}</small>
          <p>${speechOf(record) || t5("No answer retained", "未保留回答")}</p>
        </div>
      </section>
      <section ?hidden=${this.detailTab !== "evidence"} class="evidence">
        <p class="muted">
          ${t5("Dispatch, acceptance and physical confirmation remain separate facts.", "派发、接收和物理确认，是彼此独立的事实。")}
        </p>
        <details class="timing-details">
          <summary>${t5("Timing and model usage", "时序与模型用量")}</summary>
          ${this.waterfall(record)}
          <div class="usage">
          ${[
      [
        t5("Input tokens", "输入 Token"),
        usage.input_tokens ?? usage.prompt_tokens
      ],
      [
        t5("Output tokens", "输出 Token"),
        usage.output_tokens ?? usage.completion_tokens
      ],
      [t5("Cached tokens", "缓存 Token"), usage.cached_input_tokens]
    ].map(([label, value]) => b2`<div>
                <small>${label}</small
                ><strong
                  >${measurement(value) === null ? "—" : Number(value).toLocaleString(this.language)}</strong
                >
              </div>`)}
        </div>
        </details>
        <button
          class="primary"
          ?disabled=${this.loading || !this.replay || !supportsActionReplay(record)}
          @click=${() => this.replaySelected()}
        >
          ↻ ${t5("Replay action proposal", "重放动作提案")}
        </button>
        <p class="muted replay-note">
          ${supportsActionReplay(record) ? t5("Replay evaluates the recorded local action. Device actions remain proposals.", "重放评估已记录的本地动作，设备动作保留为提案。") : t5("This record has no replayable local action. Use the Test panel to preview a new model response.", "此记录没有可重放的本地动作，可在测试面板演练模型回答。")}
        </p>
        ${this.detailTab === "evidence" ? b2`
                ${[...records(record.actions), ...records(record.proposed_actions)].map((action) => b2`<article class="surface"><strong>${String(action.entity_id || action.domain || action.service || "Action")}</strong>${this.jsonTree(action, "Actuation evidence")}</article>`)}
                ${this.jsonTree(record.outcome_verdict || record.harness_loop || object(record.route).outcome_verdict || {}, t5("Outcome", "对话结果"))}
                ${this.jsonTree(record.tools || [], t5("Tool calls", "工具调用"))}
                ${this.jsonTree(record.errors || [], t5("Errors", "错误"))}
                ${this.jsonTree(record.event_stream || record.timeline || [], t5("Observed events", "观测事件"))}
              ` : A}
      </section>
      <section ?hidden=${this.detailTab !== "audio"} class="audio-preview">
        <h3>${t5("Listen in context", "在语境中试听")}</h3>
        <p class="muted">
          ${t5("This trace does not retain microphone recordings. Load a local WAV or 16-bit PCM sample to audition; it stays in this browser.", "此记录不保存麦克风录音。可载入本地 WAV 或 16 位 PCM 样本试听，文件仅留在浏览器。")}
        </p>
        <div class="audio-format">
          <label
            >${t5("PCM sample rate", "PCM 采样率")}<select
              @change=${(event) => {
      this.audioRate = Number(event.target.value);
      this.clearAudio();
    }}
            >
              ${pcmSampleRates.map((rate) => b2`<option .selected=${rate === this.audioRate} value=${rate}>${rate} Hz</option>`)}
            </select></label
          ><label
            >${t5("Channels", "声道")}<select
              @change=${(event) => {
      this.audioChannels = Number(event.target.value);
      this.clearAudio();
    }}
            >
              <option value="1">${t5("Mono", "单声道")}</option>
              <option value="2">${t5("Stereo", "双声道")}</option>
            </select></label
          >
        </div>
        <label
          >${t5("Local audio sample", "本地音频样本")}<input
            type="file"
            accept=".wav,.pcm,audio/wav"
            @change=${(event) => this.loadAudio(event.target.files?.[0])}
        /></label>
        ${this.audioUrl ? b2`<span class="muted">${this.audioName}</span><audio controls preload="metadata" src=${this.audioUrl}></audio>` : A}
      </section>
      <section ?hidden=${this.detailTab !== "json"}>
        ${this.detailTab === "json" ? this.jsonTree(record, t5("Complete run", "完整运行记录")) : A}
      </section>
    `;
  }
  waterfall(record) {
    const t5 = this.text.bind(this);
    const stages = pipelineStages(record);
    const starts = stages.flatMap((stage) => stage.startMs === null ? [] : [stage.startMs]);
    const origin = Math.min(0, ...starts);
    const end = Math.max(1, ...stages.map((stage) => (stage.startMs ?? origin) + (stage.durationMs ?? 0)));
    const span = end - origin;
    return b2`<section
      class="waterfall"
      aria-label=${t5("Observed pipeline timing", "观测链路时序")}
    >
      <div class="timing-head">
        <span>${t5("Pipeline timing", "链路时序")}</span
        ><small
          >${t5("Missing spans stay unmeasured", "缺失阶段保留为未测量")}</small
        >
      </div>
      ${stages.map((stage) => b2`<details
            class="stage"
            style=${"--stage-color:var(--stage-" + stage.id + ")"}
          >
            <summary>
              <span
                >${stageNames[stage.id][this.language.startsWith("zh") ? 1 : 0]}</span
              ><span class="track"
                >${stage.events.length ? b2`<i class=${stage.startMs === null ? "unaligned" : stage.durationMs === null ? "point" : ""} style=${"left:" + (stage.startMs === null ? 0 : Math.max(0, (stage.startMs - origin) / span * 100)) + "%;width:" + (stage.durationMs === null || stage.startMs === null ? 2 : Math.max(1, Math.min(100, stage.durationMs / span * 100))) + "%"}></i>` : b2`<em>—</em>`}</span
              ><small
                >${stage.durationMs === null ? t5("Unmeasured", "未测量") : Math.round(stage.durationMs) + " ms"}</small
              >
            </summary>
            <div class="stage-detail">
              <span class="chip">${stage.status}</span
              >${stage.startMs === null && stage.events.length ? b2`<p class="muted">${t5("No shared time offset was recorded.", "未记录统一时间偏移。")}</p>` : A}${stage.events.length ? stage.events.map((event) => this.jsonTree(event, String(event.type || event.stage || event.event_type || "Event"))) : b2`<p class="muted">${t5("No stage evidence retained", "未保留该阶段证据")}</p>`}
            </div>
          </details>`)}
    </section>`;
  }
  jsonTree(value, label, depth = 0) {
    if (value && typeof value === "object") {
      const entries = Object.entries(value);
      return b2`<details class="json-tree" ?open=${depth === 0}>
        <summary>
          <strong>${label}</strong
          ><span class="muted"
            >${Array.isArray(value) ? "[" + entries.length + "]" : "{" + entries.length + "}"}</span
          >
        </summary>
        ${depth >= 6 ? b2`<pre>${JSON.stringify(value, null, 2)}</pre>` : b2`<div class="json-children">${entries.map(([key, child]) => this.jsonTree(child, key, depth + 1))}</div>`}
      </details>`;
    }
    return b2`<div class="json-value">
      <span>${label}</span
      ><code>${typeof value === "string" ? value : JSON.stringify(value)}</code>
    </div>`;
  }
  toggleCompare(item) {
    const found = this.selection.some((value) => this.key(value) === this.key(item));
    this.selection = found ? this.selection.filter((value) => this.key(value) !== this.key(item)) : [...this.selection.slice(-1), item];
  }
  async fetchDetail(item) {
    const detail = this.details.get(this.key(item));
    if (detail || !this.loadDetail)
      return detail || item.record;
    const loaded = await this.loadDetail(item.entryId, idOf(item.record));
    this.details.set(this.key(item), loaded);
    this.requestUpdate();
    return loaded;
  }
  async open(item, opener) {
    this.opener = opener;
    this.selected = item;
    this.compareOpen = false;
    this.detailTab = "conversation";
    this.error = "";
    this.clearAudio();
    await this.updateComplete;
    this.showDialog();
    this.loading = true;
    try {
      await this.fetchDetail(item);
    } catch (error) {
      this.error = String(error instanceof Error ? error.message : error);
    } finally {
      this.loading = false;
    }
  }
  showDialog() {
    const dialog = this.renderRoot.querySelector("dialog");
    if (dialog && !dialog.open)
      dialog.showModal();
  }
  close() {
    this.renderRoot.querySelector("dialog")?.close();
    this.clearAudio();
    this.selected = null;
    this.compareOpen = false;
    this.opener?.focus();
  }
  async openComparison() {
    if (this.selection.length !== 2)
      return;
    this.opener = this.renderRoot.querySelector(".compare-bar .primary") || undefined;
    this.error = "";
    this.compareOpen = true;
    this.loading = true;
    await this.updateComplete;
    this.showDialog();
    try {
      await Promise.all(this.selection.map((item) => this.fetchDetail(item)));
    } catch (error) {
      this.error = String(error instanceof Error ? error.message : error);
    } finally {
      this.loading = false;
    }
  }
  comparison() {
    if (this.selection.length !== 2)
      return A;
    const [left, right] = this.selection;
    return b2`<voice-harness-replay-inspector
      .language=${this.language}
      .pair=${{ source: this.current(left), fork: this.current(right), sourceId: idOf(left.record), forkId: idOf(right.record) }}
      .labels=${{ route: this.text("Model & route", "模型与路由"), actions: this.text("Proposed actions", "动作提案"), speech: this.text("Reply", "回答"), events: this.text("Events", "事件") }}
    ></voice-harness-replay-inspector>`;
  }
  async replaySelected() {
    if (!this.selected || !this.replay)
      return;
    this.loading = true;
    this.error = "";
    try {
      const source = this.selected;
      const record = await this.replay(source.entryId, idOf(source.record));
      if (record) {
        const fork = { entryId: source.entryId, record };
        this.details.set(this.key(fork), record);
        this.selection = [source, fork];
        this.compareOpen = true;
      }
    } catch (error) {
      this.error = String(error instanceof Error ? error.message : error);
    } finally {
      this.loading = false;
    }
  }
  clearAudio() {
    this.renderRoot.querySelector("audio")?.pause();
    if (this.audioUrl)
      URL.revokeObjectURL(this.audioUrl);
    this.audioUrl = "";
  }
  async loadAudio(file) {
    if (!file)
      return;
    this.error = "";
    this.clearAudio();
    try {
      const bytes = await file.arrayBuffer();
      const blob = file.name.toLowerCase().endsWith(".pcm") ? new Blob([
        pcmWave(new Uint8Array(bytes), this.audioRate, this.audioChannels)
      ], { type: "audio/wav" }) : new Blob([bytes], { type: "audio/wav" });
      this.audioName = file.name;
      this.audioUrl = URL.createObjectURL(blob);
    } catch (error) {
      this.error = String(error instanceof Error ? error.message : error);
    }
  }
  updated(changes) {
    if (changes.has("detailTab") && this.detailTab !== "audio")
      this.renderRoot.querySelector("audio")?.pause();
  }
  disconnectedCallback() {
    this.clearAudio();
    super.disconnectedCallback();
  }
  static styles = [
    harnessFoundationStyles,
    harnessButtonStyles,
    harnessSurfaceStyles,
    i`
      :host {
        display: block;
        --stage-wake: #c19b55;
        --stage-asr: #4c9c98;
        --stage-llm: #788fca;
        --stage-tts: #a487bb;
        --stage-playback: #659975;
        --stage-follow_up: #c58d73;
      }
      .run-surface {
        padding: 8px 22px;
      }
      .toolbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 14px 0;
      }
      .filters {
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
      }
      .filter {
        border: 0;
        background: transparent;
        padding: 10px 14px;
        border-radius: 999px;
        color: var(--vh-muted);
      }
      [aria-pressed="true"] {
        background: var(--vh-soft);
        color: var(--vh-accent);
      }
      .search {
        max-width: 320px;
        width: 30%;
      }
      .search input {
        background: transparent;
      }
      .list-head {
        padding: 14px 8px;
        border-bottom: 1px solid var(--vh-line);
        display: grid;
        grid-template-columns: minmax(0, 1fr) 140px 100px 65px;
        color: var(--vh-muted);
        font-size: 12px;
      }
      .run-row {
        display: flex;
        align-items: center;
        gap: 10px;
        border-bottom: 1px solid var(--vh-line);
      }
      .run-row:last-child {
        border-bottom: 0;
      }
      .run-open {
        flex: 1;
        display: grid;
        grid-template-columns: 8px minmax(0, 1fr) 140px 100px;
        gap: 14px;
        text-align: left;
        background: transparent;
        border: 0;
        border-radius: 14px;
        padding: 22px 8px;
      }
      .identity {
        min-width: 0;
        display: grid;
        gap: 5px;
      }
      .identity strong {
        font-size: 15px;
        font-weight: 570;
        white-space: nowrap;
        text-overflow: ellipsis;
        overflow: hidden;
      }
      .identity small,
      .run-facts small {
        font-size: 11px;
        color: var(--vh-muted);
        font-weight: 400;
      }
      .excerpt {
        font-size: 13px;
        color: var(--vh-muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-weight: 400;
      }
      .run-facts {
        display: grid;
        gap: 6px;
        font-variant-numeric: tabular-nums;
      }
      .run-facts strong {
        font-size: 13px;
        text-transform: capitalize;
        font-weight: 550;
      }
      .run-open .chip {
        justify-self: start;
      }
      .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: currentColor;
      }
      .compare-pick {
        width: 56px;
        flex-shrink: 0;
      }
      .mobile-compare {
        display: none;
      }
      .compare-bar {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 0;
      }
      .compare-bar > span {
        margin-right: auto;
        color: var(--vh-muted);
      }
      dialog {
        position: fixed;
        inset: 0 0 0 auto;
        width: min(860px, 94vw);
        max-width: 100vw;
        height: 100%;
        max-height: 100%;
        margin: 0;
        border: 0;
        border-left: 1px solid var(--vh-line);
        background: var(--vh-background);
        color: var(--vh-ink);
        padding: 0;
        box-shadow: -24px 0 80px #00000015;
      }
      dialog[open] {
        animation: drawer-in 280ms var(--vh-ease);
      }
      dialog::backdrop {
        background: #14253266;
        backdrop-filter: blur(3px);
      }
      .drawer-header {
        position: sticky;
        top: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 22px 30px;
        background: var(--vh-surface);
        border-bottom: 1px solid var(--vh-line);
        z-index: 2;
      }
      .drawer-header > div {
        display: grid;
        gap: 6px;
      }
      .drawer-body {
        padding: 24px 30px 48px;
      }
      .detail-summary {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
      }
      .question {
        margin: 22px 0;
        font-size: 25px;
        line-height: 1.5;
        overflow-wrap: anywhere;
      }
      .waterfall {
        padding: 18px 20px;
        border-radius: var(--vh-radius-m);
        background: var(--vh-surface);
        border: 1px solid var(--vh-line);
      }
      .timing-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        margin-bottom: 10px;
      }
      .timing-head small {
        font-size: 10px;
        color: var(--vh-muted);
      }
      .stage summary {
        display: grid;
        grid-template-columns: 68px minmax(0, 1fr) 76px;
        align-items: center;
        gap: 12px;
        font-size: 12px;
      }
      .stage summary::marker {
        content: "";
      }
      .stage summary > small {
        text-align: right;
        color: var(--vh-muted);
        font-size: 11px;
      }
      .track {
        height: 18px;
        position: relative;
        border-radius: 5px;
        background: var(--vh-background);
        overflow: hidden;
      }
      .track i {
        position: absolute;
        top: 3px;
        height: 12px;
        min-width: 3px;
        border-radius: 3px;
        background: var(--stage-color);
      }
      .track i.point {
        width: 3px !important;
      }
      .track i.unaligned {
        background: repeating-linear-gradient(
          45deg,
          var(--stage-color) 0px 2px,
          transparent 2px 4px
        );
        width: 100% !important;
        opacity: 0.55;
      }
      .track em {
        padding-left: 8px;
        color: var(--vh-muted);
        font-style: normal;
      }
      .stage-detail {
        padding: 8px 0 16px;
      }
      .detail-tabs {
        display: flex;
        gap: 6px;
        margin: 22px 0;
        padding: 4px;
        border-radius: 14px;
        background: var(--vh-surface);
      }
      .detail-tabs button {
        flex: 1;
        border: 0;
        background: transparent;
      }
      .detail-tabs [aria-pressed="true"] {
        background: var(--vh-soft);
      }
      .conversation {
        display: grid;
        gap: 16px;
      }
      .bubble {
        padding: 18px 20px;
        border-radius: 20px;
        max-width: 90%;
      }
      .bubble p {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        font-size: 15px;
        line-height: 1.75;
      }
      .bubble small {
        display: block;
        margin-bottom: 8px;
        color: var(--vh-muted);
      }
      .bubble.user {
        justify-self: end;
        background: var(--vh-soft);
        border-bottom-right-radius: 5px;
      }
      .bubble.assistant {
        justify-self: start;
        background: var(--vh-surface);
        border-bottom-left-radius: 5px;
      }
      .usage {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin: 12px 0;
      }
      .timing-details > summary {
        min-height: 48px;
        padding: 14px 0;
        cursor: pointer;
        font-size: 14px;
      }
      .usage > div {
        padding: 16px;
        border-radius: 14px;
        border: 1px solid var(--vh-line);
        display: grid;
        gap: 6px;
      }
      .usage small {
        color: var(--vh-muted);
        font-size: 11px;
      }
      .usage strong {
        font-size: 24px;
        font-weight: 550;
        font-variant-numeric: tabular-nums;
      }
      .replay-note {
        margin-top: -4px;
      }
      .evidence,
      .audio-preview {
        display: grid;
        gap: 16px;
      }
      .json-tree {
        border-bottom: 1px solid var(--vh-line);
        min-width: 0;
      }
      .json-tree summary {
        display: flex;
        gap: 12px;
        align-items: center;
        font-size: 12px;
      }
      .json-tree summary::before {
        content: "›";
        font-size: 18px;
      }
      .json-tree[open] > summary::before {
        transform: rotate(90deg);
      }
      .json-children {
        padding-left: 14px;
        border-left: 1px solid var(--vh-line);
      }
      .json-value {
        display: grid;
        grid-template-columns: minmax(80px, 0.35fr) minmax(0, 1fr);
        gap: 10px;
        font-size: 11px;
        padding: 8px 0;
        overflow-wrap: anywhere;
      }
      .json-value > span {
        color: var(--vh-muted);
      }
      .audio-format {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      audio {
        width: 100%;
        margin-top: 12px;
      }
      .empty h3 {
        margin: 12px 0;
      }
      .empty p {
        max-width: 480px;
        margin: auto;
        line-height: 1.7;
      }
      .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip-path: inset(50%);
      }
      @keyframes drawer-in {
        from {
          transform: translateX(60px);
          opacity: 0;
        }
      }
      @media (max-width: 900px) {
        .toolbar {
          flex-wrap: wrap;
        }
        .search {
          width: 100%;
          max-width: none;
        }
        .run-open {
          grid-template-columns: 6px minmax(0, 1fr) 76px;
        }
        .run-facts {
          display: none;
        }
        .list-head {
          grid-template-columns: 1fr 80px 56px;
        }
        .list-head > span:nth-child(2) {
          display: none;
        }
      }
      @media (max-width: 600px) {
        .run-surface {
          padding: 6px 12px;
        }
        .run-row {
          flex-wrap: wrap;
          gap: 0;
          padding: 10px 0;
        }
        .run-open {
          padding: 10px 0;
          width: 100%;
          flex-basis: 100%;
          gap: 8px;
        }
        .identity strong {
          white-space: normal;
          font-size: 14px;
        }
        .compare-pick {
          width: auto;
          min-height: 44px;
          margin-left: auto;
          font-size: 12px;
        }
        .mobile-compare {
          display: inline;
        }
        .list-head {
          display: none;
        }
        .run-open .chip {
          font-size: 10px;
          padding: 5px 8px;
        }
        .filters {
          gap: 0;
          flex-wrap: nowrap;
          width: 100%;
          justify-content: space-between;
        }
        .filter {
          padding: 10px;
          font-size: 12px;
        }
        dialog {
          width: 100%;
        }
        .drawer-header,
        .drawer-body {
          padding: 18px;
        }
        .waterfall {
          padding: 14px;
        }
        .stage summary {
          grid-template-columns: 46px minmax(0, 1fr) 60px;
          gap: 8px;
        }
        .timing-head {
          align-items: flex-start;
          flex-direction: column;
        }
        .bubble {
          max-width: 95%;
        }
        .usage {
          gap: 8px;
        }
        .usage > div {
          padding: 12px;
        }
        .json-value {
          grid-template-columns: 1fr;
          gap: 3px;
        }
      }
    `
  ];
}
if (!customElements.get("voice-harness-runs"))
  customElements.define("voice-harness-runs", VoiceHarnessRuns);

// custom_components/llm_gateway/frontend/voice-harness-playground.ts
class VoiceHarnessPlayground extends i4 {
  static properties = {
    hass: { attribute: false },
    language: {},
    scenarios: { attribute: false },
    entries: { attribute: false },
    draft: { state: true },
    chosen: { state: true },
    result: { state: true },
    text: { state: true },
    events: { state: true },
    status: { state: true },
    error: { state: true },
    usage: { state: true },
    expanded: { state: true },
    route: { state: true },
    entryId: { state: true }
  };
  active;
  last;
  constructor() {
    super();
    this.language = "en";
    this.scenarios = [];
    this.entries = [];
    this.draft = {
      user: "",
      response: "",
      expected: JSON.stringify({ spoken_response: { max_sentences: 2 } }, null, 2)
    };
    this.chosen = "";
    this.result = null;
    this.text = "";
    this.events = [];
    this.usage = {};
    this.status = "idle";
    this.error = "";
    this.expanded = false;
    this.route = "auto";
    this.entryId = "";
  }
  t(en, zh) {
    return this.language.startsWith("zh") ? zh : en;
  }
  choose(scenario) {
    if (this.active)
      return;
    this.chosen = scenario.id;
    this.draft = {
      user: scenario.user,
      response: scenario.response,
      expected: JSON.stringify(scenario.expected, null, 2)
    };
    this.result = null;
    this.error = "";
    this.status = "idle";
    this.text = "";
    this.events = [];
    this.usage = {};
  }
  edit(field, event) {
    this.draft = {
      ...this.draft,
      [field]: event.target.value
    };
  }
  render() {
    const t5 = this.t.bind(this);
    const working = ["connecting", "streaming", "evaluating"].includes(this.status);
    const visible = this.expanded ? this.scenarios : this.scenarios.slice(0, 6);
    return b2`
      <div class="section-head">
        <div>
          <span class="eyebrow"
            >VOICE HARNESS / ${t5("PLAYGROUND", "测试")}</span
          >
          <h2>
            ${t5("Investigate a response.", "排查一次回应。")}
          </h2>
          <p class="muted">
            ${t5("Use a recorded problem to check an answer or a tool proposal.", "从实际遇到的问题出发，检查回答或工具提案。")}
          </p>
        </div>
        <span class="chip">${t5("Preview workspace", "演练工作台")}</span>
      </div>
      <section class="scenarios" aria-label=${t5("Scenarios", "场景卡片")}>
        ${visible.map((scenario, index) => b2`<button
              class="scenario"
              aria-pressed=${String(this.chosen === scenario.id)}
              ?disabled=${working}
              @click=${() => this.choose(scenario)}
            >
              <span class="scenario-top"
                ><ha-icon
                  icon=${["mdi:home-thermometer-outline", "mdi:reply-all-outline", "mdi:weather-cloudy", "mdi:shield-check-outline", "mdi:waveform", "mdi:message-outline"][index % 6]}
                ></ha-icon
                ><span>${String(index + 1).padStart(2, "0")}</span></span
              ><strong>${scenario.title}</strong><small>${scenario.user}</small
              ><span class="scenario-arrow">↗</span>
            </button>`)}
      </section>
      ${this.scenarios.length > 6 ? b2`<button
              class="quiet more"
              @click=${() => {
      this.expanded = !this.expanded;
    }}
            >
              ${this.expanded ? t5("Show less", "收起场景") : t5("All scenarios", "全部场景") + " · " + this.scenarios.length}
            </button>` : A}
      <div class="workbench">
        <section class="surface composer">
          <div class="section-head">
            <div>
              <span class="eyebrow">COMPOSE</span>
              <h3>${t5("Your test conversation", "你的测试对话")}</h3>
            </div>
            <span class="chip">${t5("Text input", "文本输入")}</span>
          </div>
          <label
            >${t5("Say something", "说点什么")}<textarea
              rows="4"
              .value=${this.draft.user}
              ?disabled=${working}
              @input=${(event) => this.edit("user", event)}
              placeholder=${t5("What is the temperature in the bedroom?", "卧室现在温度怎么样？")}
            ></textarea>
          </label>
          <div class="route-fields">
            <label
              >${t5("Gateway", "网关")}<select
                .value=${this.entryId || String(this.entries[0]?.entry_id || "")}
                ?disabled=${working}
                @change=${(event) => {
      this.entryId = event.target.value;
    }}
              >
                ${this.entries.map((entry) => b2`<option value=${String(entry.entry_id)}>${String(entry.title)}</option>`)}
              </select></label
            ><label
              >${t5("Model route", "模型路由")}<select
                .value=${this.route}
                ?disabled=${working}
                @change=${(event) => {
      this.route = event.target.value;
    }}
              >
                ${["auto", "fast", "mid", "deep"].map((route) => b2`<option value=${route}>${route === "auto" ? t5("Automatic", "自动") : route[0].toUpperCase() + route.slice(1)}</option>`)}
              </select></label
            >
          </div>
          <details class="draft-details" open>
            <summary>
              ${t5("Assertions & reference reply", "断言与参考回答")}
            </summary>
            <label
              >${t5("Reference reply (assertion check only)", "参考回答（用于断言检查）")}<textarea
                rows="3"
                .value=${this.draft.response}
                ?disabled=${working}
                @input=${(event) => this.edit("response", event)}
              ></textarea></label
            ><label
              >${t5("Expected behavior · JSON", "预期行为 · JSON")}<textarea
                class="code"
                rows="5"
                .value=${this.draft.expected}
                ?disabled=${working}
                @input=${(event) => this.edit("expected", event)}
              ></textarea>
            </label>
          </details>
          <div class="actions">
            <button
              class="primary"
              ?disabled=${working || !this.draft.user.trim() || !this.entries.length}
              @click=${() => this.run("stream")}
            >
              ${t5("Run & watch", "运行并观察")} ↗</button
            ><button
              ?disabled=${working || !this.draft.user.trim()}
              @click=${() => this.run("evaluate")}
            >
              ${t5("Check assertions", "检查断言")}
            </button>
          </div>
          <p class="muted boundary">
            ${t5("Model preview makes a real provider request. Tool calls are shown as proposals; device state is never changed. Text scenarios do not measure microphone or network reliability.", "模型演练会真实请求服务商；工具调用显示为提案，设备状态不变。文本场景不代表麦克风或弱网实测。")}
          </p>
        </section>
        <section
          class="surface monitor"
          aria-label=${t5("Live test output", "实时测试输出")}
        >
          <div class="section-head">
            <div>
              <span class="eyebrow">LIVE OUTPUT</span>
              <h3>${t5("As it happens", "看见回应发生")}</h3>
            </div>
            <span
              class=${"chip " + (this.status === "error" ? "bad" : this.status === "complete" ? "ok" : "muted")}
              >${{ idle: t5("Ready", "就绪"), connecting: t5("Connecting", "连接中"), streaming: t5("Streaming", "生成中"), evaluating: t5("Checking", "检查中"), complete: t5("Complete", "已完成"), cancelled: t5("Stopped", "已停止"), error: t5("Failed", "失败") }[this.status] || this.status}</span
            >
          </div>
          ${this.error ? b2`<p class="error" role="alert">${this.error}</p>` : A}
          ${this.status === "idle" && !this.text ? b2`<div class="waiting">
                  <div class="waiting-glyph">
                    <ha-icon icon="mdi:creation-outline"></ha-icon>
                  </div>
                  <h3>
                    ${t5("Space for a new idea", "给一句新想法，留个位置")}
                  </h3>
                  <p>
                    ${t5("Choose a scenario or write your own. The response and tool proposals appear here.", "选择场景，或写下你的问题。回答与工具提案会在这里展开。")}
                  </p>
                </div>` : b2`<div
                  class="stream-text"
                  aria-label=${t5("Model response", "模型回答")}
                >
                  ${this.text}${working ? b2`<span class="caret" aria-hidden="true"></span>` : A}
                </div>`}
          <div class="event-track">
            ${this.events.map((event) => b2`<article class="stream-event">
                  <span class="event-marker"></span>
                  <div>
                    <strong
                      >${event.type === "route" ? String(event.route).toUpperCase() + " · " + String(event.model) : t5("Tool proposal", "工具提案") + " · " + String(event.name || "…")}</strong
                    >${event.type === "tool" ? b2`<code>${String(event.arguments || "")}</code><small>${t5("Not dispatched", "尚未派发")}</small>` : A}
                  </div>
                </article>`)}
          </div>
          ${Object.keys(this.usage).length ? b2`<div class="tokens">${Object.entries(this.usage).map(([key, value]) => b2`<span>${key}: <strong>${String(value)}</strong></span>`)}</div>` : A}
          ${this.result ? b2`<div class=${"assertions " + (this.result.passed ? "ok" : "bad")} role="status"><strong>${this.result.passed ? "✓ " + t5("Assertions passed", "断言通过") : "× " + t5("Assertions failed", "断言未通过")}</strong>${Array.isArray(this.result.violations) ? this.result.violations.map((violation) => b2`<p>${String(violation)}</p>`) : A}</div>` : A}
          <div class="monitor-actions">
            ${working ? b2`<button @click=${() => this.stop()}>${t5("Stop", "停止")}</button>` : this.last ? b2`<button @click=${() => this.replayLast()}>↻ ${t5("Replay test", "重放本轮测试")}</button>` : A}<span
              role="status"
              class="muted"
              >${this.status === "complete" ? this.last?.mode === "evaluate" ? t5("Reference reply checked", "已检查参考回答") : t5("Provider completion and assertions recorded", "已记录生成结束与断言结果") : ""}</span
            >
          </div>
        </section>
      </div>
      <details class="surface policies">
        <summary>${t5("Prompt & policy reference", "提示词与策略参考")}</summary>
        <slot name="policies"></slot>
      </details>
    `;
  }
  async run(mode, replay = false) {
    let expected;
    try {
      expected = JSON.parse(this.draft.expected);
      if (!expected || typeof expected !== "object" || Array.isArray(expected))
        throw new Error;
    } catch {
      this.error = this.t("Expected behavior must be a JSON object.", "预期行为必须是 JSON 对象。");
      return;
    }
    const snapshot = { ...this.draft };
    const entryId = this.entryId || String(this.entries[0]?.entry_id || "");
    if (!replay)
      this.last = { mode, draft: snapshot, entryId, route: this.route };
    this.result = null;
    this.text = "";
    this.events = [];
    this.usage = {};
    this.error = "";
    const stream = {};
    this.active = stream;
    this.status = mode === "stream" ? "connecting" : "evaluating";
    try {
      if (mode === "evaluate") {
        const result = await requestHarnessJson(this.hass, "POST", "llm_gateway/harness/evaluate", {
          entry_id: entryId,
          user: snapshot.user,
          response: snapshot.response,
          expected
        });
        if (this.active !== stream)
          return;
        this.result = result;
        this.text = String(result.spoken || "");
        this.status = "complete";
        this.active = undefined;
        return;
      }
      if (!this.hass?.connection)
        throw new Error(this.t("Connect through Home Assistant to stream a model response.", "请通过 Home Assistant 连接模型流式演练。"));
      const connection = this.hass.connection;
      const disconnected = () => {
        if (this.active !== stream)
          return;
        this.error = this.t("Connection lost. Replay when Home Assistant reconnects.", "连接已断开，Home Assistant 恢复后可重放测试。");
        this.status = "error";
        this.active = undefined;
        this.release(stream);
      };
      connection.addEventListener?.("disconnected", disconnected);
      stream.removeDisconnect = () => connection.removeEventListener?.("disconnected", disconnected);
      const unsubscribe = await connection.subscribeMessage((event) => {
        if (this.active !== stream)
          return;
        if (event.type === "token") {
          this.status = "streaming";
          this.text += String(event.text || "");
        }
        if (event.type === "route")
          this.events = [...this.events, event];
        if (event.type === "tool") {
          const prior = this.events.findIndex((item) => item.type === "tool" && item.index === event.index);
          this.events = prior < 0 ? [...this.events, { ...event }] : this.events.map((item, index) => index === prior ? { ...event } : item);
        }
        if (event.type === "usage")
          this.usage = object(event.usage);
        if (event.type === "complete") {
          this.result = { ...event };
          this.status = "complete";
          this.active = undefined;
          this.release(stream);
        }
        if (event.type === "error") {
          this.error = String(event.message || "Stream failed");
          this.status = "error";
          this.active = undefined;
          this.release(stream);
        }
      }, {
        type: "llm_gateway/harness/stream",
        entry_id: entryId,
        user: snapshot.user,
        route: this.route,
        expected
      }, { resubscribe: false });
      stream.unsubscribe = unsubscribe;
      if (this.active !== stream)
        this.release(stream);
    } catch (error) {
      if (this.active !== stream)
        return;
      this.error = error instanceof Error ? error.message : String(error);
      this.status = "error";
      this.active = undefined;
      this.release(stream);
    }
  }
  stop() {
    const current = this.active;
    this.active = undefined;
    if (current)
      this.release(current);
    this.status = "cancelled";
  }
  release(stream) {
    stream.removeDisconnect?.();
    stream.removeDisconnect = undefined;
    const unsubscribe = stream.unsubscribe;
    stream.unsubscribe = undefined;
    if (unsubscribe)
      Promise.resolve().then(unsubscribe).catch(() => {});
  }
  replayLast() {
    if (!this.last)
      return;
    this.draft = { ...this.last.draft };
    this.entryId = this.last.entryId;
    this.route = this.last.route;
    this.run(this.last.mode, true);
  }
  disconnectedCallback() {
    if (this.active)
      this.stop();
    super.disconnectedCallback();
  }
  static styles = [
    harnessFoundationStyles,
    harnessButtonStyles,
    harnessSurfaceStyles,
    i`
      :host {
        display: block;
      }
      .scenarios {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
      }
      .scenario {
        min-height: 158px;
        position: relative;
        padding: 22px;
        display: grid;
        align-content: start;
        justify-content: stretch;
        gap: 10px;
        text-align: left;
        border-radius: 20px;
      }
      .scenario[aria-pressed="true"] {
        border-color: var(--vh-accent);
        background: var(--vh-soft);
      }
      .scenario-top {
        display: flex;
        justify-content: space-between;
        color: var(--vh-accent);
      }
      .scenario-top > span {
        color: var(--vh-muted);
        font-size: 11px;
        font-variant-numeric: tabular-nums;
      }
      .scenario strong {
        font-size: 15px;
        font-weight: 580;
        margin-top: 2px;
      }
      .scenario small {
        color: var(--vh-muted);
        font-size: 12px;
        font-weight: 400;
        max-width: 90%;
      }
      .scenario-arrow {
        position: absolute;
        bottom: 16px;
        right: 20px;
        color: var(--vh-muted);
      }
      .more {
        display: flex;
        margin: 8px auto;
        color: var(--vh-muted);
        font-size: 12px;
      }
      .workbench {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        align-items: start;
        gap: 18px;
        margin: 22px 0;
      }
      .composer,
      .monitor {
        display: grid;
        gap: 20px;
      }
      .section-head {
        margin-bottom: 0;
      }
      .route-fields {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      .draft-details {
        border-top: 1px solid var(--vh-line);
      }
      .draft-details summary {
        color: var(--vh-muted);
        font-size: 13px;
      }
      .draft-details label {
        margin-top: 14px;
      }
      .code {
        font:
          12px/1.65 ui-monospace,
          monospace;
      }
      .actions {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
      }
      .actions button {
        flex: 1;
      }
      .boundary {
        font-size: 12px;
        line-height: 1.7;
      }
      .monitor {
        min-height: 500px;
        position: sticky;
        top: 20px;
        background: linear-gradient(
          150deg,
          var(--vh-soft),
          var(--vh-surface) 38%
        );
      }
      .waiting {
        min-height: 270px;
        display: grid;
        align-content: center;
        justify-items: center;
        gap: 16px;
        text-align: center;
      }
      .waiting p {
        max-width: 300px;
        color: var(--vh-muted);
        font-size: 13px;
        line-height: 1.8;
      }
      .waiting-glyph {
        width: 62px;
        height: 62px;
        border-radius: 20px;
        background: var(--vh-soft);
        color: var(--vh-accent);
        display: grid;
        place-items: center;
        margin-bottom: 8px;
      }
      .stream-text {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        font-size: 16px;
        line-height: 1.9;
        min-height: 130px;
      }
      .caret {
        display: inline-block;
        height: 1em;
        width: 2px;
        background: var(--vh-accent);
        animation: blink 1s ease infinite;
        vertical-align: middle;
        margin-left: 3px;
      }
      .event-track {
        display: grid;
        gap: 16px;
      }
      .stream-event {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        font-size: 12px;
      }
      .event-marker {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--vh-accent);
        margin-top: 6px;
        flex-shrink: 0;
      }
      .stream-event > div {
        display: grid;
        gap: 6px;
        min-width: 0;
      }
      .stream-event strong {
        font-weight: 500;
        overflow-wrap: anywhere;
      }
      .stream-event code {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        color: var(--vh-muted);
      }
      .stream-event small {
        color: var(--warning-color);
      }
      .tokens {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        color: var(--vh-muted);
        font-size: 11px;
      }
      .assertions {
        padding: 16px;
        border: 1px solid currentColor;
        border-radius: 14px;
        font-size: 13px;
      }
      .assertions p {
        margin-top: 8px;
        overflow-wrap: anywhere;
      }
      .monitor-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
      }
      .policies {
        padding-top: 0;
        padding-bottom: 0;
      }
      .policies summary {
        padding: 18px 0;
      }
      @keyframes blink {
        50% {
          opacity: 0;
        }
      }
      @media (max-width: 950px) {
        .scenarios {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .workbench {
          grid-template-columns: 1fr;
        }
        .monitor {
          position: static;
          min-height: 360px;
        }
      }
      @media (max-width: 600px) {
        .scenarios {
          gap: 10px;
        }
        .scenario {
          padding: 16px;
          min-height: 165px;
        }
        .scenario strong {
          font-size: 13px;
        }
        .scenario small {
          font-size: 11px;
        }
        .route-fields {
          gap: 10px;
        }
        .actions {
          flex-direction: column;
        }
      }
    `
  ];
}
if (!customElements.get("voice-harness-playground"))
  customElements.define("voice-harness-playground", VoiceHarnessPlayground);

// node_modules/yaml/browser/dist/nodes/identity.js
var ALIAS = Symbol.for("yaml.alias");
var DOC = Symbol.for("yaml.document");
var MAP = Symbol.for("yaml.map");
var PAIR = Symbol.for("yaml.pair");
var SCALAR = Symbol.for("yaml.scalar");
var SEQ = Symbol.for("yaml.seq");
var NODE_TYPE = Symbol.for("yaml.node.type");
var isAlias = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === ALIAS;
var isDocument = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === DOC;
var isMap = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === MAP;
var isPair = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === PAIR;
var isScalar = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === SCALAR;
var isSeq = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === SEQ;
function isCollection(node) {
  if (node && typeof node === "object")
    switch (node[NODE_TYPE]) {
      case MAP:
      case SEQ:
        return true;
    }
  return false;
}
function isNode(node) {
  if (node && typeof node === "object")
    switch (node[NODE_TYPE]) {
      case ALIAS:
      case MAP:
      case SCALAR:
      case SEQ:
        return true;
    }
  return false;
}
var hasAnchor = (node) => (isScalar(node) || isCollection(node)) && !!node.anchor;

// node_modules/yaml/browser/dist/visit.js
var BREAK = Symbol("break visit");
var SKIP = Symbol("skip children");
var REMOVE = Symbol("remove node");
function visit(node, visitor) {
  const visitor_ = initVisitor(visitor);
  if (isDocument(node)) {
    const cd = visit_(null, node.contents, visitor_, Object.freeze([node]));
    if (cd === REMOVE)
      node.contents = null;
  } else
    visit_(null, node, visitor_, Object.freeze([]));
}
visit.BREAK = BREAK;
visit.SKIP = SKIP;
visit.REMOVE = REMOVE;
function visit_(key, node, visitor, path) {
  const ctrl = callVisitor(key, node, visitor, path);
  if (isNode(ctrl) || isPair(ctrl)) {
    replaceNode(key, path, ctrl);
    return visit_(key, ctrl, visitor, path);
  }
  if (typeof ctrl !== "symbol") {
    if (isCollection(node)) {
      path = Object.freeze(path.concat(node));
      for (let i7 = 0;i7 < node.items.length; ++i7) {
        const ci = visit_(i7, node.items[i7], visitor, path);
        if (typeof ci === "number")
          i7 = ci - 1;
        else if (ci === BREAK)
          return BREAK;
        else if (ci === REMOVE) {
          node.items.splice(i7, 1);
          i7 -= 1;
        }
      }
    } else if (isPair(node)) {
      path = Object.freeze(path.concat(node));
      const ck = visit_("key", node.key, visitor, path);
      if (ck === BREAK)
        return BREAK;
      else if (ck === REMOVE)
        node.key = null;
      const cv = visit_("value", node.value, visitor, path);
      if (cv === BREAK)
        return BREAK;
      else if (cv === REMOVE)
        node.value = null;
    }
  }
  return ctrl;
}
async function visitAsync(node, visitor) {
  const visitor_ = initVisitor(visitor);
  if (isDocument(node)) {
    const cd = await visitAsync_(null, node.contents, visitor_, Object.freeze([node]));
    if (cd === REMOVE)
      node.contents = null;
  } else
    await visitAsync_(null, node, visitor_, Object.freeze([]));
}
visitAsync.BREAK = BREAK;
visitAsync.SKIP = SKIP;
visitAsync.REMOVE = REMOVE;
async function visitAsync_(key, node, visitor, path) {
  const ctrl = await callVisitor(key, node, visitor, path);
  if (isNode(ctrl) || isPair(ctrl)) {
    replaceNode(key, path, ctrl);
    return visitAsync_(key, ctrl, visitor, path);
  }
  if (typeof ctrl !== "symbol") {
    if (isCollection(node)) {
      path = Object.freeze(path.concat(node));
      for (let i7 = 0;i7 < node.items.length; ++i7) {
        const ci = await visitAsync_(i7, node.items[i7], visitor, path);
        if (typeof ci === "number")
          i7 = ci - 1;
        else if (ci === BREAK)
          return BREAK;
        else if (ci === REMOVE) {
          node.items.splice(i7, 1);
          i7 -= 1;
        }
      }
    } else if (isPair(node)) {
      path = Object.freeze(path.concat(node));
      const ck = await visitAsync_("key", node.key, visitor, path);
      if (ck === BREAK)
        return BREAK;
      else if (ck === REMOVE)
        node.key = null;
      const cv = await visitAsync_("value", node.value, visitor, path);
      if (cv === BREAK)
        return BREAK;
      else if (cv === REMOVE)
        node.value = null;
    }
  }
  return ctrl;
}
function initVisitor(visitor) {
  if (typeof visitor === "object" && (visitor.Collection || visitor.Node || visitor.Value)) {
    return Object.assign({
      Alias: visitor.Node,
      Map: visitor.Node,
      Scalar: visitor.Node,
      Seq: visitor.Node
    }, visitor.Value && {
      Map: visitor.Value,
      Scalar: visitor.Value,
      Seq: visitor.Value
    }, visitor.Collection && {
      Map: visitor.Collection,
      Seq: visitor.Collection
    }, visitor);
  }
  return visitor;
}
function callVisitor(key, node, visitor, path) {
  if (typeof visitor === "function")
    return visitor(key, node, path);
  if (isMap(node))
    return visitor.Map?.(key, node, path);
  if (isSeq(node))
    return visitor.Seq?.(key, node, path);
  if (isPair(node))
    return visitor.Pair?.(key, node, path);
  if (isScalar(node))
    return visitor.Scalar?.(key, node, path);
  if (isAlias(node))
    return visitor.Alias?.(key, node, path);
  return;
}
function replaceNode(key, path, node) {
  const parent = path[path.length - 1];
  if (isCollection(parent)) {
    parent.items[key] = node;
  } else if (isPair(parent)) {
    if (key === "key")
      parent.key = node;
    else
      parent.value = node;
  } else if (isDocument(parent)) {
    parent.contents = node;
  } else {
    const pt = isAlias(parent) ? "alias" : "scalar";
    throw new Error(`Cannot replace node with ${pt} parent`);
  }
}

// node_modules/yaml/browser/dist/doc/directives.js
var escapeChars = {
  "!": "%21",
  ",": "%2C",
  "[": "%5B",
  "]": "%5D",
  "{": "%7B",
  "}": "%7D"
};
var escapeTagName = (tn) => tn.replace(/[!,[\]{}]/g, (ch) => escapeChars[ch]);

class Directives {
  constructor(yaml, tags) {
    this.docStart = null;
    this.docEnd = false;
    this.yaml = Object.assign({}, Directives.defaultYaml, yaml);
    this.tags = Object.assign({}, Directives.defaultTags, tags);
  }
  clone() {
    const copy = new Directives(this.yaml, this.tags);
    copy.docStart = this.docStart;
    return copy;
  }
  atDocument() {
    const res = new Directives(this.yaml, this.tags);
    switch (this.yaml.version) {
      case "1.1":
        this.atNextDocument = true;
        break;
      case "1.2":
        this.atNextDocument = false;
        this.yaml = {
          explicit: Directives.defaultYaml.explicit,
          version: "1.2"
        };
        this.tags = Object.assign({}, Directives.defaultTags);
        break;
    }
    return res;
  }
  add(line, onError) {
    if (this.atNextDocument) {
      this.yaml = { explicit: Directives.defaultYaml.explicit, version: "1.1" };
      this.tags = Object.assign({}, Directives.defaultTags);
      this.atNextDocument = false;
    }
    const parts = line.trim().split(/[ \t]+/);
    const name = parts.shift();
    switch (name) {
      case "%TAG": {
        if (parts.length !== 2) {
          onError(0, "%TAG directive should contain exactly two parts");
          if (parts.length < 2)
            return false;
        }
        const [handle, prefix] = parts;
        this.tags[handle] = prefix;
        return true;
      }
      case "%YAML": {
        this.yaml.explicit = true;
        if (parts.length !== 1) {
          onError(0, "%YAML directive should contain exactly one part");
          return false;
        }
        const [version] = parts;
        if (version === "1.1" || version === "1.2") {
          this.yaml.version = version;
          return true;
        } else {
          const isValid = /^\d+\.\d+$/.test(version);
          onError(6, `Unsupported YAML version ${version}`, isValid);
          return false;
        }
      }
      default:
        onError(0, `Unknown directive ${name}`, true);
        return false;
    }
  }
  tagName(source, onError) {
    if (source === "!")
      return "!";
    if (source[0] !== "!") {
      onError(`Not a valid tag: ${source}`);
      return null;
    }
    if (source[1] === "<") {
      const verbatim = source.slice(2, -1);
      if (verbatim === "!" || verbatim === "!!") {
        onError(`Verbatim tags aren't resolved, so ${source} is invalid.`);
        return null;
      }
      if (source[source.length - 1] !== ">")
        onError("Verbatim tags must end with a >");
      return verbatim;
    }
    const [, handle, suffix] = source.match(/^(.*!)([^!]*)$/s);
    if (!suffix)
      onError(`The ${source} tag has no suffix`);
    const prefix = this.tags[handle];
    if (prefix) {
      try {
        return prefix + decodeURIComponent(suffix);
      } catch (error) {
        onError(String(error));
        return null;
      }
    }
    if (handle === "!")
      return source;
    onError(`Could not resolve tag: ${source}`);
    return null;
  }
  tagString(tag) {
    for (const [handle, prefix] of Object.entries(this.tags)) {
      if (tag.startsWith(prefix))
        return handle + escapeTagName(tag.substring(prefix.length));
    }
    return tag[0] === "!" ? tag : `!<${tag}>`;
  }
  toString(doc) {
    const lines = this.yaml.explicit ? [`%YAML ${this.yaml.version || "1.2"}`] : [];
    const tagEntries = Object.entries(this.tags);
    let tagNames;
    if (doc && tagEntries.length > 0 && isNode(doc.contents)) {
      const tags = {};
      visit(doc.contents, (_key, node) => {
        if (isNode(node) && node.tag)
          tags[node.tag] = true;
      });
      tagNames = Object.keys(tags);
    } else
      tagNames = [];
    for (const [handle, prefix] of tagEntries) {
      if (handle === "!!" && prefix === "tag:yaml.org,2002:")
        continue;
      if (!doc || tagNames.some((tn) => tn.startsWith(prefix)))
        lines.push(`%TAG ${handle} ${prefix}`);
    }
    return lines.join(`
`);
  }
}
Directives.defaultYaml = { explicit: false, version: "1.2" };
Directives.defaultTags = { "!!": "tag:yaml.org,2002:" };

// node_modules/yaml/browser/dist/doc/anchors.js
function anchorIsValid(anchor) {
  if (/[\x00-\x19\s,[\]{}]/.test(anchor)) {
    const sa = JSON.stringify(anchor);
    const msg = `Anchor must not contain whitespace or control characters: ${sa}`;
    throw new Error(msg);
  }
  return true;
}
function anchorNames(root) {
  const anchors = new Set;
  visit(root, {
    Value(_key, node) {
      if (node.anchor)
        anchors.add(node.anchor);
    }
  });
  return anchors;
}
function findNewAnchor(prefix, exclude) {
  for (let i7 = 1;; ++i7) {
    const name = `${prefix}${i7}`;
    if (!exclude.has(name))
      return name;
  }
}
function createNodeAnchors(doc, prefix) {
  const aliasObjects = [];
  const sourceObjects = new Map;
  let prevAnchors = null;
  return {
    onAnchor: (source) => {
      aliasObjects.push(source);
      prevAnchors ?? (prevAnchors = anchorNames(doc));
      const anchor = findNewAnchor(prefix, prevAnchors);
      prevAnchors.add(anchor);
      return anchor;
    },
    setAnchors: () => {
      for (const source of aliasObjects) {
        const ref = sourceObjects.get(source);
        if (typeof ref === "object" && ref.anchor && (isScalar(ref.node) || isCollection(ref.node))) {
          ref.node.anchor = ref.anchor;
        } else {
          const error = new Error("Failed to resolve repeated object (this should not happen)");
          error.source = source;
          throw error;
        }
      }
    },
    sourceObjects
  };
}

// node_modules/yaml/browser/dist/doc/applyReviver.js
function applyReviver(reviver, obj, key, val) {
  if (val && typeof val === "object") {
    if (Array.isArray(val)) {
      for (let i7 = 0, len = val.length;i7 < len; ++i7) {
        const v0 = val[i7];
        const v1 = applyReviver(reviver, val, String(i7), v0);
        if (v1 === undefined)
          delete val[i7];
        else if (v1 !== v0)
          val[i7] = v1;
      }
    } else if (val instanceof Map) {
      for (const k2 of Array.from(val.keys())) {
        const v0 = val.get(k2);
        const v1 = applyReviver(reviver, val, k2, v0);
        if (v1 === undefined)
          val.delete(k2);
        else if (v1 !== v0)
          val.set(k2, v1);
      }
    } else if (val instanceof Set) {
      for (const v0 of Array.from(val)) {
        const v1 = applyReviver(reviver, val, v0, v0);
        if (v1 === undefined)
          val.delete(v0);
        else if (v1 !== v0) {
          val.delete(v0);
          val.add(v1);
        }
      }
    } else {
      for (const [k2, v0] of Object.entries(val)) {
        const v1 = applyReviver(reviver, val, k2, v0);
        if (v1 === undefined)
          delete val[k2];
        else if (v1 !== v0)
          val[k2] = v1;
      }
    }
  }
  return reviver.call(obj, key, val);
}

// node_modules/yaml/browser/dist/nodes/toJS.js
function toJS(value, arg, ctx) {
  if (Array.isArray(value))
    return value.map((v3, i7) => toJS(v3, String(i7), ctx));
  if (value && typeof value.toJSON === "function") {
    if (!ctx || !hasAnchor(value))
      return value.toJSON(arg, ctx);
    const data = { aliasCount: 0, count: 1, res: undefined };
    ctx.anchors.set(value, data);
    ctx.onCreate = (res2) => {
      data.res = res2;
      delete ctx.onCreate;
    };
    const res = value.toJSON(arg, ctx);
    if (ctx.onCreate)
      ctx.onCreate(res);
    return res;
  }
  if (typeof value === "bigint" && !ctx?.keep)
    return Number(value);
  return value;
}

// node_modules/yaml/browser/dist/nodes/Node.js
class NodeBase {
  constructor(type) {
    Object.defineProperty(this, NODE_TYPE, { value: type });
  }
  clone() {
    const copy = Object.create(Object.getPrototypeOf(this), Object.getOwnPropertyDescriptors(this));
    if (this.range)
      copy.range = this.range.slice();
    return copy;
  }
  toJS(doc, { mapAsMap, maxAliasCount, onAnchor, reviver } = {}) {
    if (!isDocument(doc))
      throw new TypeError("A document argument is required");
    const ctx = {
      anchors: new Map,
      doc,
      keep: true,
      mapAsMap: mapAsMap === true,
      mapKeyWarned: false,
      maxAliasCount: typeof maxAliasCount === "number" ? maxAliasCount : 100
    };
    const res = toJS(this, "", ctx);
    if (typeof onAnchor === "function")
      for (const { count, res: res2 } of ctx.anchors.values())
        onAnchor(res2, count);
    return typeof reviver === "function" ? applyReviver(reviver, { "": res }, "", res) : res;
  }
}

// node_modules/yaml/browser/dist/nodes/Alias.js
class Alias extends NodeBase {
  constructor(source) {
    super(ALIAS);
    this.source = source;
    Object.defineProperty(this, "tag", {
      set() {
        throw new Error("Alias nodes cannot have tags");
      }
    });
  }
  resolve(doc, ctx) {
    if (ctx?.maxAliasCount === 0)
      throw new ReferenceError("Alias resolution is disabled");
    let nodes;
    if (ctx?.aliasResolveCache) {
      nodes = ctx.aliasResolveCache;
    } else {
      nodes = [];
      visit(doc, {
        Node: (_key, node) => {
          if (isAlias(node) || hasAnchor(node))
            nodes.push(node);
        }
      });
      if (ctx)
        ctx.aliasResolveCache = nodes;
    }
    let found = undefined;
    for (const node of nodes) {
      if (node === this)
        break;
      if (node.anchor === this.source)
        found = node;
    }
    if (found && ctx) {
      const { anchors, doc: doc2, maxAliasCount } = ctx;
      let data = anchors.get(found);
      if (!data) {
        toJS(found, null, ctx);
        data = anchors.get(found);
      }
      if (data?.res === undefined) {
        const msg = "This should not happen: Alias anchor was not resolved?";
        throw new ReferenceError(msg);
      }
      if (maxAliasCount >= 0) {
        data.count += 1;
        if (data.aliasCount === 0)
          data.aliasCount = getAliasCount(doc2, found, anchors);
        if (data.count * data.aliasCount > maxAliasCount) {
          const msg = "Excessive alias count indicates a resource exhaustion attack";
          throw new ReferenceError(msg);
        }
      }
    }
    return found;
  }
  toJSON(_arg, ctx) {
    if (!ctx)
      return { source: this.source };
    const source = this.resolve(ctx.doc, ctx);
    if (!source) {
      const msg = `Unresolved alias (the anchor must be set before the alias): ${this.source}`;
      throw new ReferenceError(msg);
    }
    return ctx.anchors.get(source).res;
  }
  toString(ctx, _onComment, _onChompKeep) {
    const src = `*${this.source}`;
    if (ctx) {
      anchorIsValid(this.source);
      if (ctx.options.verifyAliasOrder && !ctx.anchors.has(this.source)) {
        const msg = `Unresolved alias (the anchor must be set before the alias): ${this.source}`;
        throw new Error(msg);
      }
      if (ctx.implicitKey)
        return `${src} `;
    }
    return src;
  }
}
function getAliasCount(doc, node, anchors) {
  if (isAlias(node)) {
    const source = node.resolve(doc);
    const anchor = anchors && source && anchors.get(source);
    return anchor ? anchor.count * anchor.aliasCount : 0;
  } else if (isCollection(node)) {
    let count = 0;
    for (const item of node.items) {
      const c5 = getAliasCount(doc, item, anchors);
      if (c5 > count)
        count = c5;
    }
    return count;
  } else if (isPair(node)) {
    const kc = getAliasCount(doc, node.key, anchors);
    const vc = getAliasCount(doc, node.value, anchors);
    return Math.max(kc, vc);
  }
  return 1;
}

// node_modules/yaml/browser/dist/nodes/Scalar.js
var isScalarValue = (value) => !value || typeof value !== "function" && typeof value !== "object";

class Scalar extends NodeBase {
  constructor(value) {
    super(SCALAR);
    this.value = value;
  }
  toJSON(arg, ctx) {
    return ctx?.keep ? this.value : toJS(this.value, arg, ctx);
  }
  toString() {
    return String(this.value);
  }
}
Scalar.BLOCK_FOLDED = "BLOCK_FOLDED";
Scalar.BLOCK_LITERAL = "BLOCK_LITERAL";
Scalar.PLAIN = "PLAIN";
Scalar.QUOTE_DOUBLE = "QUOTE_DOUBLE";
Scalar.QUOTE_SINGLE = "QUOTE_SINGLE";

// node_modules/yaml/browser/dist/doc/createNode.js
var defaultTagPrefix = "tag:yaml.org,2002:";
function findTagObject(value, tagName, tags) {
  if (tagName) {
    const match = tags.filter((t5) => t5.tag === tagName);
    const tagObj = match.find((t5) => !t5.format) ?? match[0];
    if (!tagObj)
      throw new Error(`Tag ${tagName} not found`);
    return tagObj;
  }
  return tags.find((t5) => t5.identify?.(value) && !t5.format);
}
function createNode(value, tagName, ctx) {
  if (isDocument(value))
    value = value.contents;
  if (isNode(value))
    return value;
  if (isPair(value)) {
    const map = ctx.schema[MAP].createNode?.(ctx.schema, null, ctx);
    map.items.push(value);
    return map;
  }
  if (value instanceof String || value instanceof Number || value instanceof Boolean || typeof BigInt !== "undefined" && value instanceof BigInt) {
    value = value.valueOf();
  }
  const { aliasDuplicateObjects, onAnchor, onTagObj, schema, sourceObjects } = ctx;
  let ref = undefined;
  if (aliasDuplicateObjects && value && typeof value === "object") {
    ref = sourceObjects.get(value);
    if (ref) {
      ref.anchor ?? (ref.anchor = onAnchor(value));
      return new Alias(ref.anchor);
    } else {
      ref = { anchor: null, node: null };
      sourceObjects.set(value, ref);
    }
  }
  if (tagName?.startsWith("!!"))
    tagName = defaultTagPrefix + tagName.slice(2);
  let tagObj = findTagObject(value, tagName, schema.tags);
  if (!tagObj) {
    if (value && typeof value.toJSON === "function") {
      value = value.toJSON();
    }
    if (!value || typeof value !== "object") {
      const node2 = new Scalar(value);
      if (ref)
        ref.node = node2;
      return node2;
    }
    tagObj = value instanceof Map ? schema[MAP] : (Symbol.iterator in Object(value)) ? schema[SEQ] : schema[MAP];
  }
  if (onTagObj) {
    onTagObj(tagObj);
    delete ctx.onTagObj;
  }
  const node = tagObj?.createNode ? tagObj.createNode(ctx.schema, value, ctx) : typeof tagObj?.nodeClass?.from === "function" ? tagObj.nodeClass.from(ctx.schema, value, ctx) : new Scalar(value);
  if (tagName)
    node.tag = tagName;
  else if (!tagObj.default)
    node.tag = tagObj.tag;
  if (ref)
    ref.node = node;
  return node;
}

// node_modules/yaml/browser/dist/nodes/Collection.js
function collectionFromPath(schema, path, value) {
  let v3 = value;
  for (let i7 = path.length - 1;i7 >= 0; --i7) {
    const k2 = path[i7];
    if (typeof k2 === "number" && Number.isInteger(k2) && k2 >= 0) {
      const a3 = [];
      a3[k2] = v3;
      v3 = a3;
    } else {
      v3 = new Map([[k2, v3]]);
    }
  }
  return createNode(v3, undefined, {
    aliasDuplicateObjects: false,
    keepUndefined: false,
    onAnchor: () => {
      throw new Error("This should not happen, please report a bug.");
    },
    schema,
    sourceObjects: new Map
  });
}
var isEmptyPath = (path) => path == null || typeof path === "object" && !!path[Symbol.iterator]().next().done;

class Collection extends NodeBase {
  constructor(type, schema) {
    super(type);
    Object.defineProperty(this, "schema", {
      value: schema,
      configurable: true,
      enumerable: false,
      writable: true
    });
  }
  clone(schema) {
    const copy = Object.create(Object.getPrototypeOf(this), Object.getOwnPropertyDescriptors(this));
    if (schema)
      copy.schema = schema;
    copy.items = copy.items.map((it) => isNode(it) || isPair(it) ? it.clone(schema) : it);
    if (this.range)
      copy.range = this.range.slice();
    return copy;
  }
  addIn(path, value) {
    if (isEmptyPath(path))
      this.add(value);
    else {
      const [key, ...rest] = path;
      const node = this.get(key, true);
      if (isCollection(node))
        node.addIn(rest, value);
      else if (node === undefined && this.schema)
        this.set(key, collectionFromPath(this.schema, rest, value));
      else
        throw new Error(`Expected YAML collection at ${key}. Remaining path: ${rest}`);
    }
  }
  deleteIn(path) {
    const [key, ...rest] = path;
    if (rest.length === 0)
      return this.delete(key);
    const node = this.get(key, true);
    if (isCollection(node))
      return node.deleteIn(rest);
    else
      throw new Error(`Expected YAML collection at ${key}. Remaining path: ${rest}`);
  }
  getIn(path, keepScalar) {
    const [key, ...rest] = path;
    const node = this.get(key, true);
    if (rest.length === 0)
      return !keepScalar && isScalar(node) ? node.value : node;
    else
      return isCollection(node) ? node.getIn(rest, keepScalar) : undefined;
  }
  hasAllNullValues(allowScalar) {
    return this.items.every((node) => {
      if (!isPair(node))
        return false;
      const n4 = node.value;
      return n4 == null || allowScalar && isScalar(n4) && n4.value == null && !n4.commentBefore && !n4.comment && !n4.tag;
    });
  }
  hasIn(path) {
    const [key, ...rest] = path;
    if (rest.length === 0)
      return this.has(key);
    const node = this.get(key, true);
    return isCollection(node) ? node.hasIn(rest) : false;
  }
  setIn(path, value) {
    const [key, ...rest] = path;
    if (rest.length === 0) {
      this.set(key, value);
    } else {
      const node = this.get(key, true);
      if (isCollection(node))
        node.setIn(rest, value);
      else if (node === undefined && this.schema)
        this.set(key, collectionFromPath(this.schema, rest, value));
      else
        throw new Error(`Expected YAML collection at ${key}. Remaining path: ${rest}`);
    }
  }
}

// node_modules/yaml/browser/dist/stringify/stringifyComment.js
var stringifyComment = (str) => str.replace(/^(?!$)(?: $)?/gm, "#");
function indentComment(comment, indent) {
  if (/^\n+$/.test(comment))
    return comment.substring(1);
  return indent ? comment.replace(/^(?! *$)/gm, indent) : comment;
}
var lineComment = (str, indent, comment) => str.endsWith(`
`) ? indentComment(comment, indent) : comment.includes(`
`) ? `
` + indentComment(comment, indent) : (str.endsWith(" ") ? "" : " ") + comment;

// node_modules/yaml/browser/dist/stringify/foldFlowLines.js
var FOLD_FLOW = "flow";
var FOLD_BLOCK = "block";
var FOLD_QUOTED = "quoted";
function foldFlowLines(text, indent, mode = "flow", { indentAtStart, lineWidth = 80, minContentWidth = 20, onFold, onOverflow } = {}) {
  if (!lineWidth || lineWidth < 0)
    return text;
  if (lineWidth < minContentWidth)
    minContentWidth = 0;
  const endStep = Math.max(1 + minContentWidth, 1 + lineWidth - indent.length);
  if (text.length <= endStep)
    return text;
  const folds = [];
  const escapedFolds = {};
  let end = lineWidth - indent.length;
  if (typeof indentAtStart === "number") {
    if (indentAtStart > lineWidth - Math.max(2, minContentWidth))
      folds.push(0);
    else
      end = lineWidth - indentAtStart;
  }
  let split = undefined;
  let prev = undefined;
  let overflow = false;
  let i7 = -1;
  let escStart = -1;
  let escEnd = -1;
  if (mode === FOLD_BLOCK) {
    i7 = consumeMoreIndentedLines(text, i7, indent.length);
    if (i7 !== -1)
      end = i7 + endStep;
  }
  for (let ch;ch = text[i7 += 1]; ) {
    if (mode === FOLD_QUOTED && ch === "\\") {
      escStart = i7;
      switch (text[i7 + 1]) {
        case "x":
          i7 += 3;
          break;
        case "u":
          i7 += 5;
          break;
        case "U":
          i7 += 9;
          break;
        default:
          i7 += 1;
      }
      escEnd = i7;
    }
    if (ch === `
`) {
      if (mode === FOLD_BLOCK)
        i7 = consumeMoreIndentedLines(text, i7, indent.length);
      end = i7 + indent.length + endStep;
      split = undefined;
    } else {
      if (ch === " " && prev && prev !== " " && prev !== `
` && prev !== "\t") {
        const next = text[i7 + 1];
        if (next && next !== " " && next !== `
` && next !== "\t")
          split = i7;
      }
      if (i7 >= end) {
        if (split) {
          folds.push(split);
          end = split + endStep;
          split = undefined;
        } else if (mode === FOLD_QUOTED) {
          while (prev === " " || prev === "\t") {
            prev = ch;
            ch = text[i7 += 1];
            overflow = true;
          }
          const j2 = i7 > escEnd + 1 ? i7 - 2 : escStart - 1;
          if (escapedFolds[j2])
            return text;
          folds.push(j2);
          escapedFolds[j2] = true;
          end = j2 + endStep;
          split = undefined;
        } else {
          overflow = true;
        }
      }
    }
    prev = ch;
  }
  if (overflow && onOverflow)
    onOverflow();
  if (folds.length === 0)
    return text;
  if (onFold)
    onFold();
  let res = text.slice(0, folds[0]);
  for (let i8 = 0;i8 < folds.length; ++i8) {
    const fold = folds[i8];
    const end2 = folds[i8 + 1] || text.length;
    if (fold === 0)
      res = `
${indent}${text.slice(0, end2)}`;
    else {
      if (mode === FOLD_QUOTED && escapedFolds[fold])
        res += `${text[fold]}\\`;
      res += `
${indent}${text.slice(fold + 1, end2)}`;
    }
  }
  return res;
}
function consumeMoreIndentedLines(text, i7, indent) {
  let end = i7;
  let start = i7 + 1;
  let ch = text[start];
  while (ch === " " || ch === "\t") {
    if (i7 < start + indent) {
      ch = text[++i7];
    } else {
      do {
        ch = text[++i7];
      } while (ch && ch !== `
`);
      end = i7;
      start = i7 + 1;
      ch = text[start];
    }
  }
  return end;
}

// node_modules/yaml/browser/dist/stringify/stringifyString.js
var getFoldOptions = (ctx, isBlock) => ({
  indentAtStart: isBlock ? ctx.indent.length : ctx.indentAtStart,
  lineWidth: ctx.options.lineWidth,
  minContentWidth: ctx.options.minContentWidth
});
var containsDocumentMarker = (str) => /^(%|---|\.\.\.)/m.test(str);
function lineLengthOverLimit(str, lineWidth, indentLength) {
  if (!lineWidth || lineWidth < 0)
    return false;
  const limit = lineWidth - indentLength;
  const strLen = str.length;
  if (strLen <= limit)
    return false;
  for (let i7 = 0, start = 0;i7 < strLen; ++i7) {
    if (str[i7] === `
`) {
      if (i7 - start > limit)
        return true;
      start = i7 + 1;
      if (strLen - start <= limit)
        return false;
    }
  }
  return true;
}
function doubleQuotedString(value, ctx) {
  const json = JSON.stringify(value);
  if (ctx.options.doubleQuotedAsJSON)
    return json;
  const { implicitKey } = ctx;
  const minMultiLineLength = ctx.options.doubleQuotedMinMultiLineLength;
  const indent = ctx.indent || (containsDocumentMarker(value) ? "  " : "");
  let str = "";
  let start = 0;
  for (let i7 = 0, ch = json[i7];ch; ch = json[++i7]) {
    if (ch === " " && json[i7 + 1] === "\\" && json[i7 + 2] === "n") {
      str += json.slice(start, i7) + "\\ ";
      i7 += 1;
      start = i7;
      ch = "\\";
    }
    if (ch === "\\")
      switch (json[i7 + 1]) {
        case "u":
          {
            str += json.slice(start, i7);
            const code = json.substr(i7 + 2, 4);
            switch (code) {
              case "0000":
                str += "\\0";
                break;
              case "0007":
                str += "\\a";
                break;
              case "000b":
                str += "\\v";
                break;
              case "001b":
                str += "\\e";
                break;
              case "0085":
                str += "\\N";
                break;
              case "00a0":
                str += "\\_";
                break;
              case "2028":
                str += "\\L";
                break;
              case "2029":
                str += "\\P";
                break;
              default:
                if (code.substr(0, 2) === "00")
                  str += "\\x" + code.substr(2);
                else
                  str += json.substr(i7, 6);
            }
            i7 += 5;
            start = i7 + 1;
          }
          break;
        case "n":
          if (implicitKey || json[i7 + 2] === '"' || json.length < minMultiLineLength) {
            i7 += 1;
          } else {
            str += json.slice(start, i7) + `

`;
            while (json[i7 + 2] === "\\" && json[i7 + 3] === "n" && json[i7 + 4] !== '"') {
              str += `
`;
              i7 += 2;
            }
            str += indent;
            if (json[i7 + 2] === " ")
              str += "\\";
            i7 += 1;
            start = i7 + 1;
          }
          break;
        default:
          i7 += 1;
      }
  }
  str = start ? str + json.slice(start) : json;
  return implicitKey ? str : foldFlowLines(str, indent, FOLD_QUOTED, getFoldOptions(ctx, false));
}
function singleQuotedString(value, ctx) {
  if (ctx.options.singleQuote === false || ctx.implicitKey && value.includes(`
`) || /[ \t]\n|\n[ \t]/.test(value))
    return doubleQuotedString(value, ctx);
  const indent = ctx.indent || (containsDocumentMarker(value) ? "  " : "");
  const res = "'" + value.replace(/'/g, "''").replace(/\n+/g, `$&
${indent}`) + "'";
  return ctx.implicitKey ? res : foldFlowLines(res, indent, FOLD_FLOW, getFoldOptions(ctx, false));
}
function quotedString(value, ctx) {
  const { singleQuote } = ctx.options;
  let qs;
  if (singleQuote === false)
    qs = doubleQuotedString;
  else {
    const hasDouble = value.includes('"');
    const hasSingle = value.includes("'");
    if (hasDouble && !hasSingle)
      qs = singleQuotedString;
    else if (hasSingle && !hasDouble)
      qs = doubleQuotedString;
    else
      qs = singleQuote ? singleQuotedString : doubleQuotedString;
  }
  return qs(value, ctx);
}
var blockEndNewlines;
try {
  blockEndNewlines = new RegExp(`(^|(?<!
))
+(?!
|$)`, "g");
} catch {
  blockEndNewlines = /\n+(?!\n|$)/g;
}
function blockString({ comment, type, value }, ctx, onComment, onChompKeep) {
  const { blockQuote, commentString, lineWidth } = ctx.options;
  if (!blockQuote || /\n[\t ]+$/.test(value)) {
    return quotedString(value, ctx);
  }
  const indent = ctx.indent || (ctx.forceBlockIndent || containsDocumentMarker(value) ? "  " : "");
  const literal = blockQuote === "literal" ? true : blockQuote === "folded" || type === Scalar.BLOCK_FOLDED ? false : type === Scalar.BLOCK_LITERAL ? true : !lineLengthOverLimit(value, lineWidth, indent.length);
  if (!value)
    return literal ? `|
` : `>
`;
  let chomp;
  let endStart;
  for (endStart = value.length;endStart > 0; --endStart) {
    const ch = value[endStart - 1];
    if (ch !== `
` && ch !== "\t" && ch !== " ")
      break;
  }
  let end = value.substring(endStart);
  const endNlPos = end.indexOf(`
`);
  if (endNlPos === -1) {
    chomp = "-";
  } else if (value === end || endNlPos !== end.length - 1) {
    chomp = "+";
    if (onChompKeep)
      onChompKeep();
  } else {
    chomp = "";
  }
  if (end) {
    value = value.slice(0, -end.length);
    if (end[end.length - 1] === `
`)
      end = end.slice(0, -1);
    end = end.replace(blockEndNewlines, `$&${indent}`);
  }
  let startWithSpace = false;
  let startEnd;
  let startNlPos = -1;
  for (startEnd = 0;startEnd < value.length; ++startEnd) {
    const ch = value[startEnd];
    if (ch === " ")
      startWithSpace = true;
    else if (ch === `
`)
      startNlPos = startEnd;
    else
      break;
  }
  let start = value.substring(0, startNlPos < startEnd ? startNlPos + 1 : startEnd);
  if (start) {
    value = value.substring(start.length);
    start = start.replace(/\n+/g, `$&${indent}`);
  }
  const indentSize = indent ? "2" : "1";
  let header = (startWithSpace ? indentSize : "") + chomp;
  if (comment) {
    header += " " + commentString(comment.replace(/ ?[\r\n]+/g, " "));
    if (onComment)
      onComment();
  }
  if (!literal) {
    const foldedValue = value.replace(/\n+/g, `
$&`).replace(/(?:^|\n)([\t ].*)(?:([\n\t ]*)\n(?![\n\t ]))?/g, "$1$2").replace(/\n+/g, `$&${indent}`);
    let literalFallback = false;
    const foldOptions = getFoldOptions(ctx, true);
    if (blockQuote !== "folded" && type !== Scalar.BLOCK_FOLDED) {
      foldOptions.onOverflow = () => {
        literalFallback = true;
      };
    }
    const body = foldFlowLines(`${start}${foldedValue}${end}`, indent, FOLD_BLOCK, foldOptions);
    if (!literalFallback)
      return `>${header}
${indent}${body}`;
  }
  value = value.replace(/\n+/g, `$&${indent}`);
  return `|${header}
${indent}${start}${value}${end}`;
}
function plainString(item, ctx, onComment, onChompKeep) {
  const { type, value } = item;
  const { actualString, implicitKey, indent, indentStep, inFlow } = ctx;
  if (implicitKey && value.includes(`
`) || inFlow && /[[\]{},]/.test(value)) {
    return quotedString(value, ctx);
  }
  if (/^[\n\t ,[\]{}#&*!|>'"%@`]|^[?-]$|^[?-][ \t]|[\n:][ \t]|[ \t]\n|[\n\t ]#|[\n\t :]$/.test(value)) {
    return implicitKey || inFlow || !value.includes(`
`) ? quotedString(value, ctx) : blockString(item, ctx, onComment, onChompKeep);
  }
  if (!implicitKey && !inFlow && type !== Scalar.PLAIN && value.includes(`
`)) {
    return blockString(item, ctx, onComment, onChompKeep);
  }
  if (containsDocumentMarker(value)) {
    if (indent === "") {
      ctx.forceBlockIndent = true;
      return blockString(item, ctx, onComment, onChompKeep);
    } else if (implicitKey && indent === indentStep) {
      return quotedString(value, ctx);
    }
  }
  const str = value.replace(/\n+/g, `$&
${indent}`);
  if (actualString) {
    const test = (tag) => tag.default && tag.tag !== "tag:yaml.org,2002:str" && tag.test?.test(str);
    const { compat, tags } = ctx.doc.schema;
    if (tags.some(test) || compat?.some(test))
      return quotedString(value, ctx);
  }
  return implicitKey ? str : foldFlowLines(str, indent, FOLD_FLOW, getFoldOptions(ctx, false));
}
function stringifyString(item, ctx, onComment, onChompKeep) {
  const { implicitKey, inFlow } = ctx;
  const ss = typeof item.value === "string" ? item : Object.assign({}, item, { value: String(item.value) });
  let { type } = item;
  if (type !== Scalar.QUOTE_DOUBLE) {
    if (/[\x00-\x08\x0b-\x1f\x7f-\x9f\u{D800}-\u{DFFF}]/u.test(ss.value))
      type = Scalar.QUOTE_DOUBLE;
  }
  const _stringify2 = (_type) => {
    switch (_type) {
      case Scalar.BLOCK_FOLDED:
      case Scalar.BLOCK_LITERAL:
        return implicitKey || inFlow ? quotedString(ss.value, ctx) : blockString(ss, ctx, onComment, onChompKeep);
      case Scalar.QUOTE_DOUBLE:
        return doubleQuotedString(ss.value, ctx);
      case Scalar.QUOTE_SINGLE:
        return singleQuotedString(ss.value, ctx);
      case Scalar.PLAIN:
        return plainString(ss, ctx, onComment, onChompKeep);
      default:
        return null;
    }
  };
  let res = _stringify2(type);
  if (res === null) {
    const { defaultKeyType, defaultStringType } = ctx.options;
    const t5 = implicitKey && defaultKeyType || defaultStringType;
    res = _stringify2(t5);
    if (res === null)
      throw new Error(`Unsupported default string type ${t5}`);
  }
  return res;
}

// node_modules/yaml/browser/dist/stringify/stringify.js
function createStringifyContext(doc, options) {
  const opt = Object.assign({
    blockQuote: true,
    commentString: stringifyComment,
    defaultKeyType: null,
    defaultStringType: "PLAIN",
    directives: null,
    doubleQuotedAsJSON: false,
    doubleQuotedMinMultiLineLength: 40,
    falseStr: "false",
    flowCollectionPadding: true,
    indentSeq: true,
    lineWidth: 80,
    minContentWidth: 20,
    nullStr: "null",
    simpleKeys: false,
    singleQuote: null,
    trailingComma: false,
    trueStr: "true",
    verifyAliasOrder: true
  }, doc.schema.toStringOptions, options);
  let inFlow;
  switch (opt.collectionStyle) {
    case "block":
      inFlow = false;
      break;
    case "flow":
      inFlow = true;
      break;
    default:
      inFlow = null;
  }
  return {
    anchors: new Set,
    doc,
    flowCollectionPadding: opt.flowCollectionPadding ? " " : "",
    indent: "",
    indentStep: typeof opt.indent === "number" ? " ".repeat(opt.indent) : "  ",
    inFlow,
    options: opt
  };
}
function getTagObject(tags, item) {
  if (item.tag) {
    const match = tags.filter((t5) => t5.tag === item.tag);
    if (match.length > 0)
      return match.find((t5) => t5.format === item.format) ?? match[0];
  }
  let tagObj = undefined;
  let obj;
  if (isScalar(item)) {
    obj = item.value;
    let match = tags.filter((t5) => t5.identify?.(obj));
    if (match.length > 1) {
      const testMatch = match.filter((t5) => t5.test);
      if (testMatch.length > 0)
        match = testMatch;
    }
    tagObj = match.find((t5) => t5.format === item.format) ?? match.find((t5) => !t5.format);
  } else {
    obj = item;
    tagObj = tags.find((t5) => t5.nodeClass && obj instanceof t5.nodeClass);
  }
  if (!tagObj) {
    const name = obj?.constructor?.name ?? (obj === null ? "null" : typeof obj);
    throw new Error(`Tag not resolved for ${name} value`);
  }
  return tagObj;
}
function stringifyProps(node, tagObj, { anchors, doc }) {
  if (!doc.directives)
    return "";
  const props = [];
  const anchor = (isScalar(node) || isCollection(node)) && node.anchor;
  if (anchor && anchorIsValid(anchor)) {
    anchors.add(anchor);
    props.push(`&${anchor}`);
  }
  const tag = node.tag ?? (tagObj.default ? null : tagObj.tag);
  if (tag)
    props.push(doc.directives.tagString(tag));
  return props.join(" ");
}
function stringify(item, ctx, onComment, onChompKeep) {
  if (isPair(item))
    return item.toString(ctx, onComment, onChompKeep);
  if (isAlias(item)) {
    if (ctx.doc.directives)
      return item.toString(ctx);
    if (ctx.resolvedAliases?.has(item)) {
      throw new TypeError(`Cannot stringify circular structure without alias nodes`);
    } else {
      if (ctx.resolvedAliases)
        ctx.resolvedAliases.add(item);
      else
        ctx.resolvedAliases = new Set([item]);
      item = item.resolve(ctx.doc);
    }
  }
  let tagObj = undefined;
  const node = isNode(item) ? item : ctx.doc.createNode(item, { onTagObj: (o6) => tagObj = o6 });
  tagObj ?? (tagObj = getTagObject(ctx.doc.schema.tags, node));
  const props = stringifyProps(node, tagObj, ctx);
  if (props.length > 0)
    ctx.indentAtStart = (ctx.indentAtStart ?? 0) + props.length + 1;
  const str = typeof tagObj.stringify === "function" ? tagObj.stringify(node, ctx, onComment, onChompKeep) : isScalar(node) ? stringifyString(node, ctx, onComment, onChompKeep) : node.toString(ctx, onComment, onChompKeep);
  if (!props)
    return str;
  return isScalar(node) || str[0] === "{" || str[0] === "[" ? `${props} ${str}` : `${props}
${ctx.indent}${str}`;
}

// node_modules/yaml/browser/dist/stringify/stringifyPair.js
function stringifyPair({ key, value }, ctx, onComment, onChompKeep) {
  const { allNullValues, doc, indent, indentStep, options: { commentString, indentSeq, simpleKeys } } = ctx;
  let keyComment = isNode(key) && key.comment || null;
  if (simpleKeys) {
    if (keyComment) {
      throw new Error("With simple keys, key nodes cannot have comments");
    }
    if (isCollection(key) || !isNode(key) && typeof key === "object") {
      const msg = "With simple keys, collection cannot be used as a key value";
      throw new Error(msg);
    }
  }
  let explicitKey = !simpleKeys && (!key || keyComment && value == null && !ctx.inFlow || isCollection(key) || (isScalar(key) ? key.type === Scalar.BLOCK_FOLDED || key.type === Scalar.BLOCK_LITERAL : typeof key === "object"));
  ctx = Object.assign({}, ctx, {
    allNullValues: false,
    implicitKey: !explicitKey && (simpleKeys || !allNullValues),
    indent: indent + indentStep
  });
  let keyCommentDone = false;
  let chompKeep = false;
  let str = stringify(key, ctx, () => keyCommentDone = true, () => chompKeep = true);
  if (!explicitKey && !ctx.inFlow && str.length > 1024) {
    if (simpleKeys)
      throw new Error("With simple keys, single line scalar must not span more than 1024 characters");
    explicitKey = true;
  }
  if (ctx.inFlow) {
    if (allNullValues || value == null) {
      if (keyCommentDone && onComment)
        onComment();
      return str === "" ? "?" : explicitKey ? `? ${str}` : str;
    }
  } else if (allNullValues && !simpleKeys || value == null && explicitKey) {
    str = `? ${str}`;
    if (keyComment && !keyCommentDone) {
      str += lineComment(str, ctx.indent, commentString(keyComment));
    } else if (chompKeep && onChompKeep)
      onChompKeep();
    return str;
  }
  if (keyCommentDone)
    keyComment = null;
  if (explicitKey) {
    if (keyComment)
      str += lineComment(str, ctx.indent, commentString(keyComment));
    str = `? ${str}
${indent}:`;
  } else {
    str = `${str}:`;
    if (keyComment)
      str += lineComment(str, ctx.indent, commentString(keyComment));
  }
  let vsb, vcb, valueComment;
  if (isNode(value)) {
    vsb = !!value.spaceBefore;
    vcb = value.commentBefore;
    valueComment = value.comment;
  } else {
    vsb = false;
    vcb = null;
    valueComment = null;
    if (value && typeof value === "object")
      value = doc.createNode(value);
  }
  ctx.implicitKey = false;
  if (!explicitKey && !keyComment && isScalar(value))
    ctx.indentAtStart = str.length + 1;
  chompKeep = false;
  if (!indentSeq && indentStep.length >= 2 && !ctx.inFlow && !explicitKey && isSeq(value) && !value.flow && !value.tag && !value.anchor) {
    ctx.indent = ctx.indent.substring(2);
  }
  let valueCommentDone = false;
  const valueStr = stringify(value, ctx, () => valueCommentDone = true, () => chompKeep = true);
  let ws = " ";
  if (keyComment || vsb || vcb) {
    ws = vsb ? `
` : "";
    if (vcb) {
      const cs = commentString(vcb);
      ws += `
${indentComment(cs, ctx.indent)}`;
    }
    if (valueStr === "" && !ctx.inFlow) {
      if (ws === `
` && valueComment)
        ws = `

`;
    } else {
      ws += `
${ctx.indent}`;
    }
  } else if (!explicitKey && isCollection(value)) {
    const vs0 = valueStr[0];
    const nl0 = valueStr.indexOf(`
`);
    const hasNewline = nl0 !== -1;
    const flow = ctx.inFlow ?? value.flow ?? value.items.length === 0;
    if (hasNewline || !flow) {
      let hasPropsLine = false;
      if (hasNewline && (vs0 === "&" || vs0 === "!")) {
        let sp0 = valueStr.indexOf(" ");
        if (vs0 === "&" && sp0 !== -1 && sp0 < nl0 && valueStr[sp0 + 1] === "!") {
          sp0 = valueStr.indexOf(" ", sp0 + 1);
        }
        if (sp0 === -1 || nl0 < sp0)
          hasPropsLine = true;
      }
      if (!hasPropsLine)
        ws = `
${ctx.indent}`;
    }
  } else if (valueStr === "" || valueStr[0] === `
`) {
    ws = "";
  }
  str += ws + valueStr;
  if (ctx.inFlow) {
    if (valueCommentDone && onComment)
      onComment();
  } else if (valueComment && !valueCommentDone) {
    str += lineComment(str, ctx.indent, commentString(valueComment));
  } else if (chompKeep && onChompKeep) {
    onChompKeep();
  }
  return str;
}

// node_modules/yaml/browser/dist/log.js
function warn(logLevel, warning) {
  if (logLevel === "debug" || logLevel === "warn") {
    console.warn(warning);
  }
}

// node_modules/yaml/browser/dist/schema/yaml-1.1/merge.js
var MERGE_KEY = "<<";
var merge = {
  identify: (value) => value === MERGE_KEY || typeof value === "symbol" && value.description === MERGE_KEY,
  default: "key",
  tag: "tag:yaml.org,2002:merge",
  test: /^<<$/,
  resolve: () => Object.assign(new Scalar(Symbol(MERGE_KEY)), {
    addToJSMap: addMergeToJSMap
  }),
  stringify: () => MERGE_KEY
};
var isMergeKey = (ctx, key) => (merge.identify(key) || isScalar(key) && (!key.type || key.type === Scalar.PLAIN) && merge.identify(key.value)) && ctx?.doc.schema.tags.some((tag) => tag.tag === merge.tag && tag.default);
function addMergeToJSMap(ctx, map, value) {
  const source = resolveAliasValue(ctx, value);
  if (isSeq(source))
    for (const it of source.items)
      mergeValue(ctx, map, it);
  else if (Array.isArray(source))
    for (const it of source)
      mergeValue(ctx, map, it);
  else
    mergeValue(ctx, map, source);
}
function mergeValue(ctx, map, value) {
  const source = resolveAliasValue(ctx, value);
  if (!isMap(source))
    throw new Error("Merge sources must be maps or map aliases");
  const srcMap = source.toJSON(null, ctx, Map);
  for (const [key, value2] of srcMap) {
    if (map instanceof Map) {
      if (!map.has(key))
        map.set(key, value2);
    } else if (map instanceof Set) {
      map.add(key);
    } else if (!Object.prototype.hasOwnProperty.call(map, key)) {
      Object.defineProperty(map, key, {
        value: value2,
        writable: true,
        enumerable: true,
        configurable: true
      });
    }
  }
  return map;
}
function resolveAliasValue(ctx, value) {
  return ctx && isAlias(value) ? value.resolve(ctx.doc, ctx) : value;
}

// node_modules/yaml/browser/dist/nodes/addPairToJSMap.js
function addPairToJSMap(ctx, map, { key, value }) {
  if (isNode(key) && key.addToJSMap)
    key.addToJSMap(ctx, map, value);
  else if (isMergeKey(ctx, key))
    addMergeToJSMap(ctx, map, value);
  else {
    const jsKey = toJS(key, "", ctx);
    if (map instanceof Map) {
      map.set(jsKey, toJS(value, jsKey, ctx));
    } else if (map instanceof Set) {
      map.add(jsKey);
    } else {
      const stringKey = stringifyKey(key, jsKey, ctx);
      const jsValue = toJS(value, stringKey, ctx);
      if (stringKey in map)
        Object.defineProperty(map, stringKey, {
          value: jsValue,
          writable: true,
          enumerable: true,
          configurable: true
        });
      else
        map[stringKey] = jsValue;
    }
  }
  return map;
}
function stringifyKey(key, jsKey, ctx) {
  if (jsKey === null)
    return "";
  if (typeof jsKey !== "object")
    return String(jsKey);
  if (isNode(key) && ctx?.doc) {
    const strCtx = createStringifyContext(ctx.doc, {});
    strCtx.anchors = new Set;
    for (const node of ctx.anchors.keys())
      strCtx.anchors.add(node.anchor);
    strCtx.inFlow = true;
    strCtx.inStringifyKey = true;
    const strKey = key.toString(strCtx);
    if (!ctx.mapKeyWarned) {
      let jsonStr = JSON.stringify(strKey);
      if (jsonStr.length > 40)
        jsonStr = jsonStr.substring(0, 36) + '..."';
      warn(ctx.doc.options.logLevel, `Keys with collection values will be stringified due to JS Object restrictions: ${jsonStr}. Set mapAsMap: true to use object keys.`);
      ctx.mapKeyWarned = true;
    }
    return strKey;
  }
  return JSON.stringify(jsKey);
}

// node_modules/yaml/browser/dist/nodes/Pair.js
function createPair(key, value, ctx) {
  const k2 = createNode(key, undefined, ctx);
  const v3 = createNode(value, undefined, ctx);
  return new Pair(k2, v3);
}

class Pair {
  constructor(key, value = null) {
    Object.defineProperty(this, NODE_TYPE, { value: PAIR });
    this.key = key;
    this.value = value;
  }
  clone(schema) {
    let { key, value } = this;
    if (isNode(key))
      key = key.clone(schema);
    if (isNode(value))
      value = value.clone(schema);
    return new Pair(key, value);
  }
  toJSON(_2, ctx) {
    const pair = ctx?.mapAsMap ? new Map : {};
    return addPairToJSMap(ctx, pair, this);
  }
  toString(ctx, onComment, onChompKeep) {
    return ctx?.doc ? stringifyPair(this, ctx, onComment, onChompKeep) : JSON.stringify(this);
  }
}

// node_modules/yaml/browser/dist/stringify/stringifyCollection.js
function stringifyCollection(collection, ctx, options) {
  const flow = ctx.inFlow ?? collection.flow;
  const stringify2 = flow ? stringifyFlowCollection : stringifyBlockCollection;
  return stringify2(collection, ctx, options);
}
function stringifyBlockCollection({ comment, items }, ctx, { blockItemPrefix, flowChars, itemIndent, onChompKeep, onComment }) {
  const { indent, options: { commentString } } = ctx;
  const itemCtx = Object.assign({}, ctx, { indent: itemIndent, type: null });
  let chompKeep = false;
  const lines = [];
  for (let i7 = 0;i7 < items.length; ++i7) {
    const item = items[i7];
    let comment2 = null;
    if (isNode(item)) {
      if (!chompKeep && item.spaceBefore)
        lines.push("");
      addCommentBefore(ctx, lines, item.commentBefore, chompKeep);
      if (item.comment)
        comment2 = item.comment;
    } else if (isPair(item)) {
      const ik = isNode(item.key) ? item.key : null;
      if (ik) {
        if (!chompKeep && ik.spaceBefore)
          lines.push("");
        addCommentBefore(ctx, lines, ik.commentBefore, chompKeep);
      }
    }
    chompKeep = false;
    let str2 = stringify(item, itemCtx, () => comment2 = null, () => chompKeep = true);
    if (comment2)
      str2 += lineComment(str2, itemIndent, commentString(comment2));
    if (chompKeep && comment2)
      chompKeep = false;
    lines.push(blockItemPrefix + str2);
  }
  let str;
  if (lines.length === 0) {
    str = flowChars.start + flowChars.end;
  } else {
    str = lines[0];
    for (let i7 = 1;i7 < lines.length; ++i7) {
      const line = lines[i7];
      str += line ? `
${indent}${line}` : `
`;
    }
  }
  if (comment) {
    str += `
` + indentComment(commentString(comment), indent);
    if (onComment)
      onComment();
  } else if (chompKeep && onChompKeep)
    onChompKeep();
  return str;
}
function stringifyFlowCollection({ items }, ctx, { flowChars, itemIndent }) {
  const { indent, indentStep, flowCollectionPadding: fcPadding, options: { commentString } } = ctx;
  itemIndent += indentStep;
  const itemCtx = Object.assign({}, ctx, {
    indent: itemIndent,
    inFlow: true,
    type: null
  });
  let reqNewline = false;
  let linesAtValue = 0;
  const lines = [];
  for (let i7 = 0;i7 < items.length; ++i7) {
    const item = items[i7];
    let comment = null;
    if (isNode(item)) {
      if (item.spaceBefore)
        lines.push("");
      addCommentBefore(ctx, lines, item.commentBefore, false);
      if (item.comment)
        comment = item.comment;
    } else if (isPair(item)) {
      const ik = isNode(item.key) ? item.key : null;
      if (ik) {
        if (ik.spaceBefore)
          lines.push("");
        addCommentBefore(ctx, lines, ik.commentBefore, false);
        if (ik.comment)
          reqNewline = true;
      }
      const iv = isNode(item.value) ? item.value : null;
      if (iv) {
        if (iv.comment)
          comment = iv.comment;
        if (iv.commentBefore)
          reqNewline = true;
      } else if (item.value == null && ik?.comment) {
        comment = ik.comment;
      }
    }
    if (comment)
      reqNewline = true;
    let str = stringify(item, itemCtx, () => comment = null);
    reqNewline || (reqNewline = lines.length > linesAtValue || str.includes(`
`));
    if (i7 < items.length - 1) {
      str += ",";
    } else if (ctx.options.trailingComma) {
      if (ctx.options.lineWidth > 0) {
        reqNewline || (reqNewline = lines.reduce((sum, line) => sum + line.length + 2, 2) + (str.length + 2) > ctx.options.lineWidth);
      }
      if (reqNewline) {
        str += ",";
      }
    }
    if (comment)
      str += lineComment(str, itemIndent, commentString(comment));
    lines.push(str);
    linesAtValue = lines.length;
  }
  const { start, end } = flowChars;
  if (lines.length === 0) {
    return start + end;
  } else {
    if (!reqNewline) {
      const len = lines.reduce((sum, line) => sum + line.length + 2, 2);
      reqNewline = ctx.options.lineWidth > 0 && len > ctx.options.lineWidth;
    }
    if (reqNewline) {
      let str = start;
      for (const line of lines)
        str += line ? `
${indentStep}${indent}${line}` : `
`;
      return `${str}
${indent}${end}`;
    } else {
      return `${start}${fcPadding}${lines.join(" ")}${fcPadding}${end}`;
    }
  }
}
function addCommentBefore({ indent, options: { commentString } }, lines, comment, chompKeep) {
  if (comment && chompKeep)
    comment = comment.replace(/^\n+/, "");
  if (comment) {
    const ic = indentComment(commentString(comment), indent);
    lines.push(ic.trimStart());
  }
}

// node_modules/yaml/browser/dist/nodes/YAMLMap.js
function findPair(items, key) {
  const k2 = isScalar(key) ? key.value : key;
  for (const it of items) {
    if (isPair(it)) {
      if (it.key === key || it.key === k2)
        return it;
      if (isScalar(it.key) && it.key.value === k2)
        return it;
    }
  }
  return;
}

class YAMLMap extends Collection {
  static get tagName() {
    return "tag:yaml.org,2002:map";
  }
  constructor(schema) {
    super(MAP, schema);
    this.items = [];
  }
  static from(schema, obj, ctx) {
    const { keepUndefined, replacer } = ctx;
    const map = new this(schema);
    const add = (key, value) => {
      if (typeof replacer === "function")
        value = replacer.call(obj, key, value);
      else if (Array.isArray(replacer) && !replacer.includes(key))
        return;
      if (value !== undefined || keepUndefined)
        map.items.push(createPair(key, value, ctx));
    };
    if (obj instanceof Map) {
      for (const [key, value] of obj)
        add(key, value);
    } else if (obj && typeof obj === "object") {
      for (const key of Object.keys(obj))
        add(key, obj[key]);
    }
    if (typeof schema.sortMapEntries === "function") {
      map.items.sort(schema.sortMapEntries);
    }
    return map;
  }
  add(pair, overwrite) {
    let _pair;
    if (isPair(pair))
      _pair = pair;
    else if (!pair || typeof pair !== "object" || !("key" in pair)) {
      _pair = new Pair(pair, pair?.value);
    } else
      _pair = new Pair(pair.key, pair.value);
    const prev = findPair(this.items, _pair.key);
    const sortEntries = this.schema?.sortMapEntries;
    if (prev) {
      if (!overwrite)
        throw new Error(`Key ${_pair.key} already set`);
      if (isScalar(prev.value) && isScalarValue(_pair.value))
        prev.value.value = _pair.value;
      else
        prev.value = _pair.value;
    } else if (sortEntries) {
      const i7 = this.items.findIndex((item) => sortEntries(_pair, item) < 0);
      if (i7 === -1)
        this.items.push(_pair);
      else
        this.items.splice(i7, 0, _pair);
    } else {
      this.items.push(_pair);
    }
  }
  delete(key) {
    const it = findPair(this.items, key);
    if (!it)
      return false;
    const del = this.items.splice(this.items.indexOf(it), 1);
    return del.length > 0;
  }
  get(key, keepScalar) {
    const it = findPair(this.items, key);
    const node = it?.value;
    return (!keepScalar && isScalar(node) ? node.value : node) ?? undefined;
  }
  has(key) {
    return !!findPair(this.items, key);
  }
  set(key, value) {
    this.add(new Pair(key, value), true);
  }
  toJSON(_2, ctx, Type) {
    const map = Type ? new Type : ctx?.mapAsMap ? new Map : {};
    if (ctx?.onCreate)
      ctx.onCreate(map);
    for (const item of this.items)
      addPairToJSMap(ctx, map, item);
    return map;
  }
  toString(ctx, onComment, onChompKeep) {
    if (!ctx)
      return JSON.stringify(this);
    for (const item of this.items) {
      if (!isPair(item))
        throw new Error(`Map items must all be pairs; found ${JSON.stringify(item)} instead`);
    }
    if (!ctx.allNullValues && this.hasAllNullValues(false))
      ctx = Object.assign({}, ctx, { allNullValues: true });
    return stringifyCollection(this, ctx, {
      blockItemPrefix: "",
      flowChars: { start: "{", end: "}" },
      itemIndent: ctx.indent || "",
      onChompKeep,
      onComment
    });
  }
}

// node_modules/yaml/browser/dist/schema/common/map.js
var map = {
  collection: "map",
  default: true,
  nodeClass: YAMLMap,
  tag: "tag:yaml.org,2002:map",
  resolve(map2, onError) {
    if (!isMap(map2))
      onError("Expected a mapping for this tag");
    return map2;
  },
  createNode: (schema, obj, ctx) => YAMLMap.from(schema, obj, ctx)
};

// node_modules/yaml/browser/dist/nodes/YAMLSeq.js
class YAMLSeq extends Collection {
  static get tagName() {
    return "tag:yaml.org,2002:seq";
  }
  constructor(schema) {
    super(SEQ, schema);
    this.items = [];
  }
  add(value) {
    this.items.push(value);
  }
  delete(key) {
    const idx = asItemIndex(key);
    if (typeof idx !== "number")
      return false;
    const del = this.items.splice(idx, 1);
    return del.length > 0;
  }
  get(key, keepScalar) {
    const idx = asItemIndex(key);
    if (typeof idx !== "number")
      return;
    const it = this.items[idx];
    return !keepScalar && isScalar(it) ? it.value : it;
  }
  has(key) {
    const idx = asItemIndex(key);
    return typeof idx === "number" && idx < this.items.length;
  }
  set(key, value) {
    const idx = asItemIndex(key);
    if (typeof idx !== "number")
      throw new Error(`Expected a valid index, not ${key}.`);
    const prev = this.items[idx];
    if (isScalar(prev) && isScalarValue(value))
      prev.value = value;
    else
      this.items[idx] = value;
  }
  toJSON(_2, ctx) {
    const seq = [];
    if (ctx?.onCreate)
      ctx.onCreate(seq);
    let i7 = 0;
    for (const item of this.items)
      seq.push(toJS(item, String(i7++), ctx));
    return seq;
  }
  toString(ctx, onComment, onChompKeep) {
    if (!ctx)
      return JSON.stringify(this);
    return stringifyCollection(this, ctx, {
      blockItemPrefix: "- ",
      flowChars: { start: "[", end: "]" },
      itemIndent: (ctx.indent || "") + "  ",
      onChompKeep,
      onComment
    });
  }
  static from(schema, obj, ctx) {
    const { replacer } = ctx;
    const seq = new this(schema);
    if (obj && Symbol.iterator in Object(obj)) {
      let i7 = 0;
      for (let it of obj) {
        if (typeof replacer === "function") {
          const key = obj instanceof Set ? it : String(i7++);
          it = replacer.call(obj, key, it);
        }
        seq.items.push(createNode(it, undefined, ctx));
      }
    }
    return seq;
  }
}
function asItemIndex(key) {
  let idx = isScalar(key) ? key.value : key;
  if (idx && typeof idx === "string")
    idx = Number(idx);
  return typeof idx === "number" && Number.isInteger(idx) && idx >= 0 ? idx : null;
}

// node_modules/yaml/browser/dist/schema/common/seq.js
var seq = {
  collection: "seq",
  default: true,
  nodeClass: YAMLSeq,
  tag: "tag:yaml.org,2002:seq",
  resolve(seq2, onError) {
    if (!isSeq(seq2))
      onError("Expected a sequence for this tag");
    return seq2;
  },
  createNode: (schema, obj, ctx) => YAMLSeq.from(schema, obj, ctx)
};

// node_modules/yaml/browser/dist/schema/common/string.js
var string2 = {
  identify: (value) => typeof value === "string",
  default: true,
  tag: "tag:yaml.org,2002:str",
  resolve: (str) => str,
  stringify(item, ctx, onComment, onChompKeep) {
    ctx = Object.assign({ actualString: true }, ctx);
    return stringifyString(item, ctx, onComment, onChompKeep);
  }
};

// node_modules/yaml/browser/dist/schema/common/null.js
var nullTag = {
  identify: (value) => value == null,
  createNode: () => new Scalar(null),
  default: true,
  tag: "tag:yaml.org,2002:null",
  test: /^(?:~|[Nn]ull|NULL)?$/,
  resolve: () => new Scalar(null),
  stringify: ({ source }, ctx) => typeof source === "string" && nullTag.test.test(source) ? source : ctx.options.nullStr
};

// node_modules/yaml/browser/dist/schema/core/bool.js
var boolTag = {
  identify: (value) => typeof value === "boolean",
  default: true,
  tag: "tag:yaml.org,2002:bool",
  test: /^(?:[Tt]rue|TRUE|[Ff]alse|FALSE)$/,
  resolve: (str) => new Scalar(str[0] === "t" || str[0] === "T"),
  stringify({ source, value }, ctx) {
    if (source && boolTag.test.test(source)) {
      const sv = source[0] === "t" || source[0] === "T";
      if (value === sv)
        return source;
    }
    return value ? ctx.options.trueStr : ctx.options.falseStr;
  }
};

// node_modules/yaml/browser/dist/stringify/stringifyNumber.js
function stringifyNumber({ format, minFractionDigits, tag, value }) {
  if (typeof value === "bigint")
    return String(value);
  const num = typeof value === "number" ? value : Number(value);
  if (!isFinite(num))
    return isNaN(num) ? ".nan" : num < 0 ? "-.inf" : ".inf";
  let n4 = Object.is(value, -0) ? "-0" : JSON.stringify(value);
  if (!format && minFractionDigits && (!tag || tag === "tag:yaml.org,2002:float") && /^-?\d/.test(n4) && !n4.includes("e")) {
    let i7 = n4.indexOf(".");
    if (i7 < 0) {
      i7 = n4.length;
      n4 += ".";
    }
    let d3 = minFractionDigits - (n4.length - i7 - 1);
    while (d3-- > 0)
      n4 += "0";
  }
  return n4;
}

// node_modules/yaml/browser/dist/schema/core/float.js
var floatNaN = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  test: /^(?:[-+]?\.(?:inf|Inf|INF)|\.nan|\.NaN|\.NAN)$/,
  resolve: (str) => str.slice(-3).toLowerCase() === "nan" ? NaN : str[0] === "-" ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY,
  stringify: stringifyNumber
};
var floatExp = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  format: "EXP",
  test: /^[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)[eE][-+]?[0-9]+$/,
  resolve: (str) => parseFloat(str),
  stringify(node) {
    const num = Number(node.value);
    return isFinite(num) ? num.toExponential() : stringifyNumber(node);
  }
};
var float = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  test: /^[-+]?(?:\.[0-9]+|[0-9]+\.[0-9]*)$/,
  resolve(str) {
    const node = new Scalar(parseFloat(str));
    const dot = str.indexOf(".");
    if (dot !== -1 && str[str.length - 1] === "0")
      node.minFractionDigits = str.length - dot - 1;
    return node;
  },
  stringify: stringifyNumber
};

// node_modules/yaml/browser/dist/schema/core/int.js
var intIdentify = (value) => typeof value === "bigint" || Number.isInteger(value);
var intResolve = (str, offset, radix, { intAsBigInt }) => intAsBigInt ? BigInt(str) : parseInt(str.substring(offset), radix);
function intStringify(node, radix, prefix) {
  const { value } = node;
  if (intIdentify(value) && value >= 0)
    return prefix + value.toString(radix);
  return stringifyNumber(node);
}
var intOct = {
  identify: (value) => intIdentify(value) && value >= 0,
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "OCT",
  test: /^0o[0-7]+$/,
  resolve: (str, _onError, opt) => intResolve(str, 2, 8, opt),
  stringify: (node) => intStringify(node, 8, "0o")
};
var int = {
  identify: intIdentify,
  default: true,
  tag: "tag:yaml.org,2002:int",
  test: /^[-+]?[0-9]+$/,
  resolve: (str, _onError, opt) => intResolve(str, 0, 10, opt),
  stringify: stringifyNumber
};
var intHex = {
  identify: (value) => intIdentify(value) && value >= 0,
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "HEX",
  test: /^0x[0-9a-fA-F]+$/,
  resolve: (str, _onError, opt) => intResolve(str, 2, 16, opt),
  stringify: (node) => intStringify(node, 16, "0x")
};

// node_modules/yaml/browser/dist/schema/core/schema.js
var schema = [
  map,
  seq,
  string2,
  nullTag,
  boolTag,
  intOct,
  int,
  intHex,
  floatNaN,
  floatExp,
  float
];

// node_modules/yaml/browser/dist/schema/json/schema.js
function intIdentify2(value) {
  return typeof value === "bigint" || Number.isInteger(value);
}
var stringifyJSON = ({ value }) => JSON.stringify(value);
var jsonScalars = [
  {
    identify: (value) => typeof value === "string",
    default: true,
    tag: "tag:yaml.org,2002:str",
    resolve: (str) => str,
    stringify: stringifyJSON
  },
  {
    identify: (value) => value == null,
    createNode: () => new Scalar(null),
    default: true,
    tag: "tag:yaml.org,2002:null",
    test: /^null$/,
    resolve: () => null,
    stringify: stringifyJSON
  },
  {
    identify: (value) => typeof value === "boolean",
    default: true,
    tag: "tag:yaml.org,2002:bool",
    test: /^true$|^false$/,
    resolve: (str) => str === "true",
    stringify: stringifyJSON
  },
  {
    identify: intIdentify2,
    default: true,
    tag: "tag:yaml.org,2002:int",
    test: /^-?(?:0|[1-9][0-9]*)$/,
    resolve: (str, _onError, { intAsBigInt }) => intAsBigInt ? BigInt(str) : parseInt(str, 10),
    stringify: ({ value }) => intIdentify2(value) ? value.toString() : JSON.stringify(value)
  },
  {
    identify: (value) => typeof value === "number",
    default: true,
    tag: "tag:yaml.org,2002:float",
    test: /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?$/,
    resolve: (str) => parseFloat(str),
    stringify: stringifyJSON
  }
];
var jsonError = {
  default: true,
  tag: "",
  test: /^/,
  resolve(str, onError) {
    onError(`Unresolved plain scalar ${JSON.stringify(str)}`);
    return str;
  }
};
var schema2 = [map, seq].concat(jsonScalars, jsonError);

// node_modules/yaml/browser/dist/schema/yaml-1.1/binary.js
var binary = {
  identify: (value) => value instanceof Uint8Array,
  default: false,
  tag: "tag:yaml.org,2002:binary",
  resolve(src, onError) {
    if (typeof atob === "function") {
      const str = atob(src.replace(/[\n\r]/g, ""));
      const buffer = new Uint8Array(str.length);
      for (let i7 = 0;i7 < str.length; ++i7)
        buffer[i7] = str.charCodeAt(i7);
      return buffer;
    } else {
      onError("This environment does not support reading binary tags; either Buffer or atob is required");
      return src;
    }
  },
  stringify({ comment, type, value }, ctx, onComment, onChompKeep) {
    if (!value)
      return "";
    const buf = value;
    let str;
    if (typeof btoa === "function") {
      let s5 = "";
      for (let i7 = 0;i7 < buf.length; ++i7)
        s5 += String.fromCharCode(buf[i7]);
      str = btoa(s5);
    } else {
      throw new Error("This environment does not support writing binary tags; either Buffer or btoa is required");
    }
    type ?? (type = Scalar.BLOCK_LITERAL);
    if (type !== Scalar.QUOTE_DOUBLE) {
      const lineWidth = Math.max(ctx.options.lineWidth - ctx.indent.length, ctx.options.minContentWidth);
      const n4 = Math.ceil(str.length / lineWidth);
      const lines = new Array(n4);
      for (let i7 = 0, o6 = 0;i7 < n4; ++i7, o6 += lineWidth) {
        lines[i7] = str.substr(o6, lineWidth);
      }
      str = lines.join(type === Scalar.BLOCK_LITERAL ? `
` : " ");
    }
    return stringifyString({ comment, type, value: str }, ctx, onComment, onChompKeep);
  }
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/pairs.js
function resolvePairs(seq2, onError) {
  if (isSeq(seq2)) {
    for (let i7 = 0;i7 < seq2.items.length; ++i7) {
      let item = seq2.items[i7];
      if (isPair(item))
        continue;
      else if (isMap(item)) {
        if (item.items.length > 1)
          onError("Each pair must have its own sequence indicator");
        const pair = item.items[0] || new Pair(new Scalar(null));
        if (item.commentBefore)
          pair.key.commentBefore = pair.key.commentBefore ? `${item.commentBefore}
${pair.key.commentBefore}` : item.commentBefore;
        if (item.comment) {
          const cn = pair.value ?? pair.key;
          cn.comment = cn.comment ? `${item.comment}
${cn.comment}` : item.comment;
        }
        item = pair;
      }
      seq2.items[i7] = isPair(item) ? item : new Pair(item);
    }
  } else
    onError("Expected a sequence for this tag");
  return seq2;
}
function createPairs(schema3, iterable, ctx) {
  const { replacer } = ctx;
  const pairs = new YAMLSeq(schema3);
  pairs.tag = "tag:yaml.org,2002:pairs";
  let i7 = 0;
  if (iterable && Symbol.iterator in Object(iterable))
    for (let it of iterable) {
      if (typeof replacer === "function")
        it = replacer.call(iterable, String(i7++), it);
      let key, value;
      if (Array.isArray(it)) {
        if (it.length === 2) {
          key = it[0];
          value = it[1];
        } else
          throw new TypeError(`Expected [key, value] tuple: ${it}`);
      } else if (it && it instanceof Object) {
        const keys = Object.keys(it);
        if (keys.length === 1) {
          key = keys[0];
          value = it[key];
        } else {
          throw new TypeError(`Expected tuple with one key, not ${keys.length} keys`);
        }
      } else {
        key = it;
      }
      pairs.items.push(createPair(key, value, ctx));
    }
  return pairs;
}
var pairs = {
  collection: "seq",
  default: false,
  tag: "tag:yaml.org,2002:pairs",
  resolve: resolvePairs,
  createNode: createPairs
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/omap.js
class YAMLOMap extends YAMLSeq {
  constructor() {
    super();
    this.add = YAMLMap.prototype.add.bind(this);
    this.delete = YAMLMap.prototype.delete.bind(this);
    this.get = YAMLMap.prototype.get.bind(this);
    this.has = YAMLMap.prototype.has.bind(this);
    this.set = YAMLMap.prototype.set.bind(this);
    this.tag = YAMLOMap.tag;
  }
  toJSON(_2, ctx) {
    if (!ctx)
      return super.toJSON(_2);
    const map2 = new Map;
    if (ctx?.onCreate)
      ctx.onCreate(map2);
    for (const pair of this.items) {
      let key, value;
      if (isPair(pair)) {
        key = toJS(pair.key, "", ctx);
        value = toJS(pair.value, key, ctx);
      } else {
        key = toJS(pair, "", ctx);
      }
      if (map2.has(key))
        throw new Error("Ordered maps must not include duplicate keys");
      map2.set(key, value);
    }
    return map2;
  }
  static from(schema3, iterable, ctx) {
    const pairs2 = createPairs(schema3, iterable, ctx);
    const omap = new this;
    omap.items = pairs2.items;
    return omap;
  }
}
YAMLOMap.tag = "tag:yaml.org,2002:omap";
var omap = {
  collection: "seq",
  identify: (value) => value instanceof Map,
  nodeClass: YAMLOMap,
  default: false,
  tag: "tag:yaml.org,2002:omap",
  resolve(seq2, onError) {
    const pairs2 = resolvePairs(seq2, onError);
    const seenKeys = [];
    for (const { key } of pairs2.items) {
      if (isScalar(key)) {
        if (seenKeys.includes(key.value)) {
          onError(`Ordered maps must not include duplicate keys: ${key.value}`);
        } else {
          seenKeys.push(key.value);
        }
      }
    }
    return Object.assign(new YAMLOMap, pairs2);
  },
  createNode: (schema3, iterable, ctx) => YAMLOMap.from(schema3, iterable, ctx)
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/bool.js
function boolStringify({ value, source }, ctx) {
  const boolObj = value ? trueTag : falseTag;
  if (source && boolObj.test.test(source))
    return source;
  return value ? ctx.options.trueStr : ctx.options.falseStr;
}
var trueTag = {
  identify: (value) => value === true,
  default: true,
  tag: "tag:yaml.org,2002:bool",
  test: /^(?:Y|y|[Yy]es|YES|[Tt]rue|TRUE|[Oo]n|ON)$/,
  resolve: () => new Scalar(true),
  stringify: boolStringify
};
var falseTag = {
  identify: (value) => value === false,
  default: true,
  tag: "tag:yaml.org,2002:bool",
  test: /^(?:N|n|[Nn]o|NO|[Ff]alse|FALSE|[Oo]ff|OFF)$/,
  resolve: () => new Scalar(false),
  stringify: boolStringify
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/float.js
var floatNaN2 = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  test: /^(?:[-+]?\.(?:inf|Inf|INF)|\.nan|\.NaN|\.NAN)$/,
  resolve: (str) => str.slice(-3).toLowerCase() === "nan" ? NaN : str[0] === "-" ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY,
  stringify: stringifyNumber
};
var floatExp2 = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  format: "EXP",
  test: /^[-+]?(?:[0-9][0-9_]*)?(?:\.[0-9_]*)?[eE][-+]?[0-9]+$/,
  resolve: (str) => parseFloat(str.replace(/_/g, "")),
  stringify(node) {
    const num = Number(node.value);
    return isFinite(num) ? num.toExponential() : stringifyNumber(node);
  }
};
var float2 = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  test: /^[-+]?(?:[0-9][0-9_]*)?\.[0-9_]*$/,
  resolve(str) {
    const node = new Scalar(parseFloat(str.replace(/_/g, "")));
    const dot = str.indexOf(".");
    if (dot !== -1) {
      const f3 = str.substring(dot + 1).replace(/_/g, "");
      if (f3[f3.length - 1] === "0")
        node.minFractionDigits = f3.length;
    }
    return node;
  },
  stringify: stringifyNumber
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/int.js
var intIdentify3 = (value) => typeof value === "bigint" || Number.isInteger(value);
function intResolve2(str, offset, radix, { intAsBigInt }) {
  const sign = str[0];
  if (sign === "-" || sign === "+")
    offset += 1;
  str = str.substring(offset).replace(/_/g, "");
  if (intAsBigInt) {
    switch (radix) {
      case 2:
        str = `0b${str}`;
        break;
      case 8:
        str = `0o${str}`;
        break;
      case 16:
        str = `0x${str}`;
        break;
    }
    const n5 = BigInt(str);
    return sign === "-" ? BigInt(-1) * n5 : n5;
  }
  const n4 = parseInt(str, radix);
  return sign === "-" ? -1 * n4 : n4;
}
function intStringify2(node, radix, prefix) {
  const { value } = node;
  if (intIdentify3(value)) {
    const str = value.toString(radix);
    return value < 0 ? "-" + prefix + str.substr(1) : prefix + str;
  }
  return stringifyNumber(node);
}
var intBin = {
  identify: intIdentify3,
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "BIN",
  test: /^[-+]?0b[0-1_]+$/,
  resolve: (str, _onError, opt) => intResolve2(str, 2, 2, opt),
  stringify: (node) => intStringify2(node, 2, "0b")
};
var intOct2 = {
  identify: intIdentify3,
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "OCT",
  test: /^[-+]?0[0-7_]+$/,
  resolve: (str, _onError, opt) => intResolve2(str, 1, 8, opt),
  stringify: (node) => intStringify2(node, 8, "0")
};
var int2 = {
  identify: intIdentify3,
  default: true,
  tag: "tag:yaml.org,2002:int",
  test: /^[-+]?[0-9][0-9_]*$/,
  resolve: (str, _onError, opt) => intResolve2(str, 0, 10, opt),
  stringify: stringifyNumber
};
var intHex2 = {
  identify: intIdentify3,
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "HEX",
  test: /^[-+]?0x[0-9a-fA-F_]+$/,
  resolve: (str, _onError, opt) => intResolve2(str, 2, 16, opt),
  stringify: (node) => intStringify2(node, 16, "0x")
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/set.js
class YAMLSet extends YAMLMap {
  constructor(schema3) {
    super(schema3);
    this.tag = YAMLSet.tag;
  }
  add(key) {
    let pair;
    if (isPair(key))
      pair = key;
    else if (key && typeof key === "object" && "key" in key && "value" in key && key.value === null)
      pair = new Pair(key.key, null);
    else
      pair = new Pair(key, null);
    const prev = findPair(this.items, pair.key);
    if (!prev)
      this.items.push(pair);
  }
  get(key, keepPair) {
    const pair = findPair(this.items, key);
    return !keepPair && isPair(pair) ? isScalar(pair.key) ? pair.key.value : pair.key : pair;
  }
  set(key, value) {
    if (typeof value !== "boolean")
      throw new Error(`Expected boolean value for set(key, value) in a YAML set, not ${typeof value}`);
    const prev = findPair(this.items, key);
    if (prev && !value) {
      this.items.splice(this.items.indexOf(prev), 1);
    } else if (!prev && value) {
      this.items.push(new Pair(key));
    }
  }
  toJSON(_2, ctx) {
    return super.toJSON(_2, ctx, Set);
  }
  toString(ctx, onComment, onChompKeep) {
    if (!ctx)
      return JSON.stringify(this);
    if (this.hasAllNullValues(true))
      return super.toString(Object.assign({}, ctx, { allNullValues: true }), onComment, onChompKeep);
    else
      throw new Error("Set items must all have null values");
  }
  static from(schema3, iterable, ctx) {
    const { replacer } = ctx;
    const set = new this(schema3);
    if (iterable && Symbol.iterator in Object(iterable))
      for (let value of iterable) {
        if (typeof replacer === "function")
          value = replacer.call(iterable, value, value);
        set.items.push(createPair(value, null, ctx));
      }
    return set;
  }
}
YAMLSet.tag = "tag:yaml.org,2002:set";
var set = {
  collection: "map",
  identify: (value) => value instanceof Set,
  nodeClass: YAMLSet,
  default: false,
  tag: "tag:yaml.org,2002:set",
  createNode: (schema3, iterable, ctx) => YAMLSet.from(schema3, iterable, ctx),
  resolve(map2, onError) {
    if (isMap(map2)) {
      if (map2.hasAllNullValues(true))
        return Object.assign(new YAMLSet, map2);
      else
        onError("Set items must all have null values");
    } else
      onError("Expected a mapping for this tag");
    return map2;
  }
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/timestamp.js
function parseSexagesimal(str, asBigInt) {
  const sign = str[0];
  const parts = sign === "-" || sign === "+" ? str.substring(1) : str;
  const num = (n4) => asBigInt ? BigInt(n4) : Number(n4);
  const res = parts.replace(/_/g, "").split(":").reduce((res2, p4) => res2 * num(60) + num(p4), num(0));
  return sign === "-" ? num(-1) * res : res;
}
function stringifySexagesimal(node) {
  let { value } = node;
  let num = (n4) => n4;
  if (typeof value === "bigint")
    num = (n4) => BigInt(n4);
  else if (isNaN(value) || !isFinite(value))
    return stringifyNumber(node);
  let sign = "";
  if (value < 0) {
    sign = "-";
    value *= num(-1);
  }
  const _60 = num(60);
  const parts = [value % _60];
  if (value < 60) {
    parts.unshift(0);
  } else {
    value = (value - parts[0]) / _60;
    parts.unshift(value % _60);
    if (value >= 60) {
      value = (value - parts[0]) / _60;
      parts.unshift(value);
    }
  }
  return sign + parts.map((n4) => String(n4).padStart(2, "0")).join(":").replace(/000000\d*$/, "");
}
var intTime = {
  identify: (value) => typeof value === "bigint" || Number.isInteger(value),
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "TIME",
  test: /^[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+$/,
  resolve: (str, _onError, { intAsBigInt }) => parseSexagesimal(str, intAsBigInt),
  stringify: stringifySexagesimal
};
var floatTime = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  format: "TIME",
  test: /^[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*$/,
  resolve: (str) => parseSexagesimal(str, false),
  stringify: stringifySexagesimal
};
var timestamp = {
  identify: (value) => value instanceof Date,
  default: true,
  tag: "tag:yaml.org,2002:timestamp",
  test: RegExp("^([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})" + "(?:" + "(?:t|T|[ \\t]+)" + "([0-9]{1,2}):([0-9]{1,2}):([0-9]{1,2}(\\.[0-9]+)?)" + "(?:[ \\t]*(Z|[-+][012]?[0-9](?::[0-9]{2})?))?" + ")?$"),
  resolve(str) {
    const match = str.match(timestamp.test);
    if (!match)
      throw new Error("!!timestamp expects a date, starting with yyyy-mm-dd");
    const [, year, month, day, hour, minute, second] = match.map(Number);
    const millisec = match[7] ? Number((match[7] + "00").substr(1, 3)) : 0;
    let date = Date.UTC(year, month - 1, day, hour || 0, minute || 0, second || 0, millisec);
    const tz = match[8];
    if (tz && tz !== "Z") {
      let d3 = parseSexagesimal(tz, false);
      if (Math.abs(d3) < 30)
        d3 *= 60;
      date -= 60000 * d3;
    }
    return new Date(date);
  },
  stringify: ({ value }) => value?.toISOString().replace(/(T00:00:00)?\.000Z$/, "") ?? ""
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/schema.js
var schema3 = [
  map,
  seq,
  string2,
  nullTag,
  trueTag,
  falseTag,
  intBin,
  intOct2,
  int2,
  intHex2,
  floatNaN2,
  floatExp2,
  float2,
  binary,
  merge,
  omap,
  pairs,
  set,
  intTime,
  floatTime,
  timestamp
];

// node_modules/yaml/browser/dist/schema/tags.js
var schemas = new Map([
  ["core", schema],
  ["failsafe", [map, seq, string2]],
  ["json", schema2],
  ["yaml11", schema3],
  ["yaml-1.1", schema3]
]);
var tagsByName = {
  binary,
  bool: boolTag,
  float,
  floatExp,
  floatNaN,
  floatTime,
  int,
  intHex,
  intOct,
  intTime,
  map,
  merge,
  null: nullTag,
  omap,
  pairs,
  seq,
  set,
  timestamp
};
var coreKnownTags = {
  "tag:yaml.org,2002:binary": binary,
  "tag:yaml.org,2002:merge": merge,
  "tag:yaml.org,2002:omap": omap,
  "tag:yaml.org,2002:pairs": pairs,
  "tag:yaml.org,2002:set": set,
  "tag:yaml.org,2002:timestamp": timestamp
};
function getTags(customTags, schemaName, addMergeTag) {
  const schemaTags = schemas.get(schemaName);
  if (schemaTags && !customTags) {
    return addMergeTag && !schemaTags.includes(merge) ? schemaTags.concat(merge) : schemaTags.slice();
  }
  let tags = schemaTags;
  if (!tags) {
    if (Array.isArray(customTags))
      tags = [];
    else {
      const keys = Array.from(schemas.keys()).filter((key) => key !== "yaml11").map((key) => JSON.stringify(key)).join(", ");
      throw new Error(`Unknown schema "${schemaName}"; use one of ${keys} or define customTags array`);
    }
  }
  if (Array.isArray(customTags)) {
    for (const tag of customTags)
      tags = tags.concat(tag);
  } else if (typeof customTags === "function") {
    tags = customTags(tags.slice());
  }
  if (addMergeTag)
    tags = tags.concat(merge);
  return tags.reduce((tags2, tag) => {
    const tagObj = typeof tag === "string" ? tagsByName[tag] : tag;
    if (!tagObj) {
      const tagName = JSON.stringify(tag);
      const keys = Object.keys(tagsByName).map((key) => JSON.stringify(key)).join(", ");
      throw new Error(`Unknown custom tag ${tagName}; use one of ${keys}`);
    }
    if (!tags2.includes(tagObj))
      tags2.push(tagObj);
    return tags2;
  }, []);
}

// node_modules/yaml/browser/dist/schema/Schema.js
var sortMapEntriesByKey = (a3, b3) => a3.key < b3.key ? -1 : a3.key > b3.key ? 1 : 0;

class Schema {
  constructor({ compat, customTags, merge: merge2, resolveKnownTags, schema: schema4, sortMapEntries, toStringDefaults }) {
    this.compat = Array.isArray(compat) ? getTags(compat, "compat") : compat ? getTags(null, compat) : null;
    this.name = typeof schema4 === "string" && schema4 || "core";
    this.knownTags = resolveKnownTags ? coreKnownTags : {};
    this.tags = getTags(customTags, this.name, merge2);
    this.toStringOptions = toStringDefaults ?? null;
    Object.defineProperty(this, MAP, { value: map });
    Object.defineProperty(this, SCALAR, { value: string2 });
    Object.defineProperty(this, SEQ, { value: seq });
    this.sortMapEntries = typeof sortMapEntries === "function" ? sortMapEntries : sortMapEntries === true ? sortMapEntriesByKey : null;
  }
  clone() {
    const copy = Object.create(Schema.prototype, Object.getOwnPropertyDescriptors(this));
    copy.tags = this.tags.slice();
    return copy;
  }
}

// node_modules/yaml/browser/dist/stringify/stringifyDocument.js
function stringifyDocument(doc, options) {
  const lines = [];
  let hasDirectives = options.directives === true;
  if (options.directives !== false && doc.directives) {
    const dir = doc.directives.toString(doc);
    if (dir) {
      lines.push(dir);
      hasDirectives = true;
    } else if (doc.directives.docStart)
      hasDirectives = true;
  }
  if (hasDirectives)
    lines.push("---");
  const ctx = createStringifyContext(doc, options);
  const { commentString } = ctx.options;
  if (doc.commentBefore) {
    if (lines.length !== 1)
      lines.unshift("");
    const cs = commentString(doc.commentBefore);
    lines.unshift(indentComment(cs, ""));
  }
  let chompKeep = false;
  let contentComment = null;
  if (doc.contents) {
    if (isNode(doc.contents)) {
      if (doc.contents.spaceBefore && hasDirectives)
        lines.push("");
      if (doc.contents.commentBefore) {
        const cs = commentString(doc.contents.commentBefore);
        lines.push(indentComment(cs, ""));
      }
      ctx.forceBlockIndent = !!doc.comment;
      contentComment = doc.contents.comment;
    }
    const onChompKeep = contentComment ? undefined : () => chompKeep = true;
    let body = stringify(doc.contents, ctx, () => contentComment = null, onChompKeep);
    if (contentComment)
      body += lineComment(body, "", commentString(contentComment));
    if ((body[0] === "|" || body[0] === ">") && lines[lines.length - 1] === "---") {
      lines[lines.length - 1] = `--- ${body}`;
    } else
      lines.push(body);
  } else {
    lines.push(stringify(doc.contents, ctx));
  }
  if (doc.directives?.docEnd) {
    if (doc.comment) {
      const cs = commentString(doc.comment);
      if (cs.includes(`
`)) {
        lines.push("...");
        lines.push(indentComment(cs, ""));
      } else {
        lines.push(`... ${cs}`);
      }
    } else {
      lines.push("...");
    }
  } else {
    let dc = doc.comment;
    if (dc && chompKeep)
      dc = dc.replace(/^\n+/, "");
    if (dc) {
      if ((!chompKeep || contentComment) && lines[lines.length - 1] !== "")
        lines.push("");
      lines.push(indentComment(commentString(dc), ""));
    }
  }
  return lines.join(`
`) + `
`;
}

// node_modules/yaml/browser/dist/doc/Document.js
class Document2 {
  constructor(value, replacer, options) {
    this.commentBefore = null;
    this.comment = null;
    this.errors = [];
    this.warnings = [];
    Object.defineProperty(this, NODE_TYPE, { value: DOC });
    let _replacer = null;
    if (typeof replacer === "function" || Array.isArray(replacer)) {
      _replacer = replacer;
    } else if (options === undefined && replacer) {
      options = replacer;
      replacer = undefined;
    }
    const opt = Object.assign({
      intAsBigInt: false,
      keepSourceTokens: false,
      logLevel: "warn",
      prettyErrors: true,
      strict: true,
      stringKeys: false,
      uniqueKeys: true,
      version: "1.2"
    }, options);
    this.options = opt;
    let { version } = opt;
    if (options?._directives) {
      this.directives = options._directives.atDocument();
      if (this.directives.yaml.explicit)
        version = this.directives.yaml.version;
    } else
      this.directives = new Directives({ version });
    this.setSchema(version, options);
    this.contents = value === undefined ? null : this.createNode(value, _replacer, options);
  }
  clone() {
    const copy = Object.create(Document2.prototype, {
      [NODE_TYPE]: { value: DOC }
    });
    copy.commentBefore = this.commentBefore;
    copy.comment = this.comment;
    copy.errors = this.errors.slice();
    copy.warnings = this.warnings.slice();
    copy.options = Object.assign({}, this.options);
    if (this.directives)
      copy.directives = this.directives.clone();
    copy.schema = this.schema.clone();
    copy.contents = isNode(this.contents) ? this.contents.clone(copy.schema) : this.contents;
    if (this.range)
      copy.range = this.range.slice();
    return copy;
  }
  add(value) {
    if (assertCollection(this.contents))
      this.contents.add(value);
  }
  addIn(path, value) {
    if (assertCollection(this.contents))
      this.contents.addIn(path, value);
  }
  createAlias(node, name) {
    if (!node.anchor) {
      const prev = anchorNames(this);
      node.anchor = !name || prev.has(name) ? findNewAnchor(name || "a", prev) : name;
    }
    return new Alias(node.anchor);
  }
  createNode(value, replacer, options) {
    let _replacer = undefined;
    if (typeof replacer === "function") {
      value = replacer.call({ "": value }, "", value);
      _replacer = replacer;
    } else if (Array.isArray(replacer)) {
      const keyToStr = (v3) => typeof v3 === "number" || v3 instanceof String || v3 instanceof Number;
      const asStr = replacer.filter(keyToStr).map(String);
      if (asStr.length > 0)
        replacer = replacer.concat(asStr);
      _replacer = replacer;
    } else if (options === undefined && replacer) {
      options = replacer;
      replacer = undefined;
    }
    const { aliasDuplicateObjects, anchorPrefix, flow, keepUndefined, onTagObj, tag } = options ?? {};
    const { onAnchor, setAnchors, sourceObjects } = createNodeAnchors(this, anchorPrefix || "a");
    const ctx = {
      aliasDuplicateObjects: aliasDuplicateObjects ?? true,
      keepUndefined: keepUndefined ?? false,
      onAnchor,
      onTagObj,
      replacer: _replacer,
      schema: this.schema,
      sourceObjects
    };
    const node = createNode(value, tag, ctx);
    if (flow && isCollection(node))
      node.flow = true;
    setAnchors();
    return node;
  }
  createPair(key, value, options = {}) {
    const k2 = this.createNode(key, null, options);
    const v3 = this.createNode(value, null, options);
    return new Pair(k2, v3);
  }
  delete(key) {
    return assertCollection(this.contents) ? this.contents.delete(key) : false;
  }
  deleteIn(path) {
    if (isEmptyPath(path)) {
      if (this.contents == null)
        return false;
      this.contents = null;
      return true;
    }
    return assertCollection(this.contents) ? this.contents.deleteIn(path) : false;
  }
  get(key, keepScalar) {
    return isCollection(this.contents) ? this.contents.get(key, keepScalar) : undefined;
  }
  getIn(path, keepScalar) {
    if (isEmptyPath(path))
      return !keepScalar && isScalar(this.contents) ? this.contents.value : this.contents;
    return isCollection(this.contents) ? this.contents.getIn(path, keepScalar) : undefined;
  }
  has(key) {
    return isCollection(this.contents) ? this.contents.has(key) : false;
  }
  hasIn(path) {
    if (isEmptyPath(path))
      return this.contents !== undefined;
    return isCollection(this.contents) ? this.contents.hasIn(path) : false;
  }
  set(key, value) {
    if (this.contents == null) {
      this.contents = collectionFromPath(this.schema, [key], value);
    } else if (assertCollection(this.contents)) {
      this.contents.set(key, value);
    }
  }
  setIn(path, value) {
    if (isEmptyPath(path)) {
      this.contents = value;
    } else if (this.contents == null) {
      this.contents = collectionFromPath(this.schema, Array.from(path), value);
    } else if (assertCollection(this.contents)) {
      this.contents.setIn(path, value);
    }
  }
  setSchema(version, options = {}) {
    if (typeof version === "number")
      version = String(version);
    let opt;
    switch (version) {
      case "1.1":
        if (this.directives)
          this.directives.yaml.version = "1.1";
        else
          this.directives = new Directives({ version: "1.1" });
        opt = { resolveKnownTags: false, schema: "yaml-1.1" };
        break;
      case "1.2":
      case "next":
        if (this.directives)
          this.directives.yaml.version = version;
        else
          this.directives = new Directives({ version });
        opt = { resolveKnownTags: true, schema: "core" };
        break;
      case null:
        if (this.directives)
          delete this.directives;
        opt = null;
        break;
      default: {
        const sv = JSON.stringify(version);
        throw new Error(`Expected '1.1', '1.2' or null as first argument, but found: ${sv}`);
      }
    }
    if (options.schema instanceof Object)
      this.schema = options.schema;
    else if (opt)
      this.schema = new Schema(Object.assign(opt, options));
    else
      throw new Error(`With a null YAML version, the { schema: Schema } option is required`);
  }
  toJS({ json, jsonArg, mapAsMap, maxAliasCount, onAnchor, reviver } = {}) {
    const ctx = {
      anchors: new Map,
      doc: this,
      keep: !json,
      mapAsMap: mapAsMap === true,
      mapKeyWarned: false,
      maxAliasCount: typeof maxAliasCount === "number" ? maxAliasCount : 100
    };
    const res = toJS(this.contents, jsonArg ?? "", ctx);
    if (typeof onAnchor === "function")
      for (const { count, res: res2 } of ctx.anchors.values())
        onAnchor(res2, count);
    return typeof reviver === "function" ? applyReviver(reviver, { "": res }, "", res) : res;
  }
  toJSON(jsonArg, onAnchor) {
    return this.toJS({ json: true, jsonArg, mapAsMap: false, onAnchor });
  }
  toString(options = {}) {
    if (this.errors.length > 0)
      throw new Error("Document with errors cannot be stringified");
    if ("indent" in options && (!Number.isInteger(options.indent) || Number(options.indent) <= 0)) {
      const s5 = JSON.stringify(options.indent);
      throw new Error(`"indent" option must be a positive integer, not ${s5}`);
    }
    return stringifyDocument(this, options);
  }
}
function assertCollection(contents) {
  if (isCollection(contents))
    return true;
  throw new Error("Expected a YAML collection as document contents");
}

// node_modules/yaml/browser/dist/errors.js
class YAMLError extends Error {
  constructor(name, pos, code, message) {
    super();
    this.name = name;
    this.code = code;
    this.message = message;
    this.pos = pos;
  }
}

class YAMLParseError extends YAMLError {
  constructor(pos, code, message) {
    super("YAMLParseError", pos, code, message);
  }
}

class YAMLWarning extends YAMLError {
  constructor(pos, code, message) {
    super("YAMLWarning", pos, code, message);
  }
}
var prettifyError = (src, lc) => (error) => {
  if (error.pos[0] === -1)
    return;
  error.linePos = error.pos.map((pos) => lc.linePos(pos));
  const { line, col } = error.linePos[0];
  error.message += ` at line ${line}, column ${col}`;
  let ci = col - 1;
  let lineStr = src.substring(lc.lineStarts[line - 1], lc.lineStarts[line]).replace(/[\n\r]+$/, "");
  if (ci >= 60 && lineStr.length > 80) {
    const trimStart = Math.min(ci - 39, lineStr.length - 79);
    lineStr = "…" + lineStr.substring(trimStart);
    ci -= trimStart - 1;
  }
  if (lineStr.length > 80)
    lineStr = lineStr.substring(0, 79) + "…";
  if (line > 1 && /^ *$/.test(lineStr.substring(0, ci))) {
    let prev = src.substring(lc.lineStarts[line - 2], lc.lineStarts[line - 1]);
    if (prev.length > 80)
      prev = prev.substring(0, 79) + `…
`;
    lineStr = prev + lineStr;
  }
  if (/[^ ]/.test(lineStr)) {
    let count = 1;
    const end = error.linePos[1];
    if (end?.line === line && end.col > col) {
      count = Math.max(1, Math.min(end.col - col, 80 - ci));
    }
    const pointer = " ".repeat(ci) + "^".repeat(count);
    error.message += `:

${lineStr}
${pointer}
`;
  }
};

// node_modules/yaml/browser/dist/compose/resolve-props.js
function resolveProps(tokens, { flow, indicator, next, offset, onError, parentIndent, startOnNewline }) {
  let spaceBefore = false;
  let atNewline = startOnNewline;
  let hasSpace = startOnNewline;
  let comment = "";
  let commentSep = "";
  let hasNewline = false;
  let reqSpace = false;
  let tab = null;
  let anchor = null;
  let tag = null;
  let newlineAfterProp = null;
  let comma = null;
  let found = null;
  let start = null;
  for (const token of tokens) {
    if (reqSpace) {
      if (token.type !== "space" && token.type !== "newline" && token.type !== "comma")
        onError(token.offset, "MISSING_CHAR", "Tags and anchors must be separated from the next token by white space");
      reqSpace = false;
    }
    if (tab) {
      if (atNewline && token.type !== "comment" && token.type !== "newline") {
        onError(tab, "TAB_AS_INDENT", "Tabs are not allowed as indentation");
      }
      tab = null;
    }
    switch (token.type) {
      case "space":
        if (!flow && (indicator !== "doc-start" || next?.type !== "flow-collection") && token.source.includes("\t")) {
          tab = token;
        }
        hasSpace = true;
        break;
      case "comment": {
        if (!hasSpace)
          onError(token, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters");
        const cb = token.source.substring(1) || " ";
        if (!comment)
          comment = cb;
        else
          comment += commentSep + cb;
        commentSep = "";
        atNewline = false;
        break;
      }
      case "newline":
        if (atNewline) {
          if (comment)
            comment += token.source;
          else if (!found || indicator !== "seq-item-ind")
            spaceBefore = true;
        } else
          commentSep += token.source;
        atNewline = true;
        hasNewline = true;
        if (anchor || tag)
          newlineAfterProp = token;
        hasSpace = true;
        break;
      case "anchor":
        if (anchor)
          onError(token, "MULTIPLE_ANCHORS", "A node can have at most one anchor");
        if (token.source.endsWith(":"))
          onError(token.offset + token.source.length - 1, "BAD_ALIAS", "Anchor ending in : is ambiguous", true);
        anchor = token;
        start ?? (start = token.offset);
        atNewline = false;
        hasSpace = false;
        reqSpace = true;
        break;
      case "tag": {
        if (tag)
          onError(token, "MULTIPLE_TAGS", "A node can have at most one tag");
        tag = token;
        start ?? (start = token.offset);
        atNewline = false;
        hasSpace = false;
        reqSpace = true;
        break;
      }
      case indicator:
        if (anchor || tag)
          onError(token, "BAD_PROP_ORDER", `Anchors and tags must be after the ${token.source} indicator`);
        if (found)
          onError(token, "UNEXPECTED_TOKEN", `Unexpected ${token.source} in ${flow ?? "collection"}`);
        found = token;
        atNewline = indicator === "seq-item-ind" || indicator === "explicit-key-ind";
        hasSpace = false;
        break;
      case "comma":
        if (flow) {
          if (comma)
            onError(token, "UNEXPECTED_TOKEN", `Unexpected , in ${flow}`);
          comma = token;
          atNewline = false;
          hasSpace = false;
          break;
        }
      default:
        onError(token, "UNEXPECTED_TOKEN", `Unexpected ${token.type} token`);
        atNewline = false;
        hasSpace = false;
    }
  }
  const last = tokens[tokens.length - 1];
  const end = last ? last.offset + last.source.length : offset;
  if (reqSpace && next && next.type !== "space" && next.type !== "newline" && next.type !== "comma" && (next.type !== "scalar" || next.source !== "")) {
    onError(next.offset, "MISSING_CHAR", "Tags and anchors must be separated from the next token by white space");
  }
  if (tab && (atNewline && tab.indent <= parentIndent || next?.type === "block-map" || next?.type === "block-seq"))
    onError(tab, "TAB_AS_INDENT", "Tabs are not allowed as indentation");
  return {
    comma,
    found,
    spaceBefore,
    comment,
    hasNewline,
    anchor,
    tag,
    newlineAfterProp,
    end,
    start: start ?? end
  };
}

// node_modules/yaml/browser/dist/compose/util-contains-newline.js
function containsNewline(key) {
  if (!key)
    return null;
  switch (key.type) {
    case "alias":
    case "scalar":
    case "double-quoted-scalar":
    case "single-quoted-scalar":
      if (key.source.includes(`
`))
        return true;
      if (key.end) {
        for (const st of key.end)
          if (st.type === "newline")
            return true;
      }
      return false;
    case "flow-collection":
      for (const it of key.items) {
        for (const st of it.start)
          if (st.type === "newline")
            return true;
        if (it.sep) {
          for (const st of it.sep)
            if (st.type === "newline")
              return true;
        }
        if (containsNewline(it.key) || containsNewline(it.value))
          return true;
      }
      return false;
    default:
      return true;
  }
}

// node_modules/yaml/browser/dist/compose/util-flow-indent-check.js
function flowIndentCheck(indent, fc, onError) {
  if (fc?.type === "flow-collection") {
    const end = fc.end[0];
    if (end.indent === indent && (end.source === "]" || end.source === "}") && containsNewline(fc)) {
      const msg = "Flow end indicator should be more indented than parent";
      onError(end, "BAD_INDENT", msg, true);
    }
  }
}

// node_modules/yaml/browser/dist/compose/util-map-includes.js
function mapIncludes(ctx, items, search) {
  const { uniqueKeys } = ctx.options;
  if (uniqueKeys === false)
    return false;
  const isEqual = typeof uniqueKeys === "function" ? uniqueKeys : (a3, b3) => a3 === b3 || isScalar(a3) && isScalar(b3) && a3.value === b3.value;
  return items.some((pair) => isEqual(pair.key, search));
}

// node_modules/yaml/browser/dist/compose/resolve-block-map.js
var startColMsg = "All mapping items must start at the same column";
function resolveBlockMap({ composeNode, composeEmptyNode }, ctx, bm, onError, tag) {
  const NodeClass = tag?.nodeClass ?? YAMLMap;
  const map2 = new NodeClass(ctx.schema);
  if (ctx.atRoot)
    ctx.atRoot = false;
  let offset = bm.offset;
  let commentEnd = null;
  for (const collItem of bm.items) {
    const { start, key, sep, value } = collItem;
    const keyProps = resolveProps(start, {
      indicator: "explicit-key-ind",
      next: key ?? sep?.[0],
      offset,
      onError,
      parentIndent: bm.indent,
      startOnNewline: true
    });
    const implicitKey = !keyProps.found;
    if (implicitKey) {
      if (key) {
        if (key.type === "block-seq")
          onError(offset, "BLOCK_AS_IMPLICIT_KEY", "A block sequence may not be used as an implicit map key");
        else if ("indent" in key && key.indent !== bm.indent)
          onError(offset, "BAD_INDENT", startColMsg);
      }
      if (!keyProps.anchor && !keyProps.tag && !sep) {
        commentEnd = keyProps.end;
        if (keyProps.comment) {
          if (map2.comment)
            map2.comment += `
` + keyProps.comment;
          else
            map2.comment = keyProps.comment;
        }
        continue;
      }
      if (keyProps.newlineAfterProp || containsNewline(key)) {
        onError(key ?? start[start.length - 1], "MULTILINE_IMPLICIT_KEY", "Implicit keys need to be on a single line");
      }
    } else if (keyProps.found?.indent !== bm.indent) {
      onError(offset, "BAD_INDENT", startColMsg);
    }
    ctx.atKey = true;
    const keyStart = keyProps.end;
    const keyNode = key ? composeNode(ctx, key, keyProps, onError) : composeEmptyNode(ctx, keyStart, start, null, keyProps, onError);
    if (ctx.schema.compat)
      flowIndentCheck(bm.indent, key, onError);
    ctx.atKey = false;
    if (mapIncludes(ctx, map2.items, keyNode))
      onError(keyStart, "DUPLICATE_KEY", "Map keys must be unique");
    const valueProps = resolveProps(sep ?? [], {
      indicator: "map-value-ind",
      next: value,
      offset: keyNode.range[2],
      onError,
      parentIndent: bm.indent,
      startOnNewline: !key || key.type === "block-scalar"
    });
    offset = valueProps.end;
    if (valueProps.found) {
      if (implicitKey) {
        if (value?.type === "block-map" && !valueProps.hasNewline)
          onError(offset, "BLOCK_AS_IMPLICIT_KEY", "Nested mappings are not allowed in compact mappings");
        if (ctx.options.strict && keyProps.start < valueProps.found.offset - 1024)
          onError(keyNode.range, "KEY_OVER_1024_CHARS", "The : indicator must be at most 1024 chars after the start of an implicit block mapping key");
      }
      const valueNode = value ? composeNode(ctx, value, valueProps, onError) : composeEmptyNode(ctx, offset, sep, null, valueProps, onError);
      if (ctx.schema.compat)
        flowIndentCheck(bm.indent, value, onError);
      offset = valueNode.range[2];
      const pair = new Pair(keyNode, valueNode);
      if (ctx.options.keepSourceTokens)
        pair.srcToken = collItem;
      map2.items.push(pair);
    } else {
      if (implicitKey)
        onError(keyNode.range, "MISSING_CHAR", "Implicit map keys need to be followed by map values");
      if (valueProps.comment) {
        if (keyNode.comment)
          keyNode.comment += `
` + valueProps.comment;
        else
          keyNode.comment = valueProps.comment;
      }
      const pair = new Pair(keyNode);
      if (ctx.options.keepSourceTokens)
        pair.srcToken = collItem;
      map2.items.push(pair);
    }
  }
  if (commentEnd && commentEnd < offset)
    onError(commentEnd, "IMPOSSIBLE", "Map comment with trailing content");
  map2.range = [bm.offset, offset, commentEnd ?? offset];
  return map2;
}

// node_modules/yaml/browser/dist/compose/resolve-block-seq.js
function resolveBlockSeq({ composeNode, composeEmptyNode }, ctx, bs, onError, tag) {
  const NodeClass = tag?.nodeClass ?? YAMLSeq;
  const seq2 = new NodeClass(ctx.schema);
  if (ctx.atRoot)
    ctx.atRoot = false;
  if (ctx.atKey)
    ctx.atKey = false;
  let offset = bs.offset;
  let commentEnd = null;
  for (const { start, value } of bs.items) {
    const props = resolveProps(start, {
      indicator: "seq-item-ind",
      next: value,
      offset,
      onError,
      parentIndent: bs.indent,
      startOnNewline: true
    });
    if (!props.found) {
      if (props.anchor || props.tag || value) {
        if (value?.type === "block-seq")
          onError(props.end, "BAD_INDENT", "All sequence items must start at the same column");
        else
          onError(offset, "MISSING_CHAR", "Sequence item without - indicator");
      } else {
        commentEnd = props.end;
        if (props.comment)
          seq2.comment = props.comment;
        continue;
      }
    }
    const node = value ? composeNode(ctx, value, props, onError) : composeEmptyNode(ctx, props.end, start, null, props, onError);
    if (ctx.schema.compat)
      flowIndentCheck(bs.indent, value, onError);
    offset = node.range[2];
    seq2.items.push(node);
  }
  seq2.range = [bs.offset, offset, commentEnd ?? offset];
  return seq2;
}

// node_modules/yaml/browser/dist/compose/resolve-end.js
function resolveEnd(end, offset, reqSpace, onError) {
  let comment = "";
  if (end) {
    let hasSpace = false;
    let sep = "";
    for (const token of end) {
      const { source, type } = token;
      switch (type) {
        case "space":
          hasSpace = true;
          break;
        case "comment": {
          if (reqSpace && !hasSpace)
            onError(token, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters");
          const cb = source.substring(1) || " ";
          if (!comment)
            comment = cb;
          else
            comment += sep + cb;
          sep = "";
          break;
        }
        case "newline":
          if (comment)
            sep += source;
          hasSpace = true;
          break;
        default:
          onError(token, "UNEXPECTED_TOKEN", `Unexpected ${type} at node end`);
      }
      offset += source.length;
    }
  }
  return { comment, offset };
}

// node_modules/yaml/browser/dist/compose/resolve-flow-collection.js
var blockMsg = "Block collections are not allowed within flow collections";
var isBlock = (token) => token && (token.type === "block-map" || token.type === "block-seq");
function resolveFlowCollection({ composeNode, composeEmptyNode }, ctx, fc, onError, tag) {
  const isMap2 = fc.start.source === "{";
  const fcName = isMap2 ? "flow map" : "flow sequence";
  const NodeClass = tag?.nodeClass ?? (isMap2 ? YAMLMap : YAMLSeq);
  const coll = new NodeClass(ctx.schema);
  coll.flow = true;
  const atRoot = ctx.atRoot;
  if (atRoot)
    ctx.atRoot = false;
  if (ctx.atKey)
    ctx.atKey = false;
  let offset = fc.offset + fc.start.source.length;
  for (let i7 = 0;i7 < fc.items.length; ++i7) {
    const collItem = fc.items[i7];
    const { start, key, sep, value } = collItem;
    const props = resolveProps(start, {
      flow: fcName,
      indicator: "explicit-key-ind",
      next: key ?? sep?.[0],
      offset,
      onError,
      parentIndent: fc.indent,
      startOnNewline: false
    });
    if (!props.found) {
      if (!props.anchor && !props.tag && !sep && !value) {
        if (i7 === 0 && props.comma)
          onError(props.comma, "UNEXPECTED_TOKEN", `Unexpected , in ${fcName}`);
        else if (i7 < fc.items.length - 1)
          onError(props.start, "UNEXPECTED_TOKEN", `Unexpected empty item in ${fcName}`);
        if (props.comment) {
          if (coll.comment)
            coll.comment += `
` + props.comment;
          else
            coll.comment = props.comment;
        }
        offset = props.end;
        continue;
      }
      if (!isMap2 && ctx.options.strict && containsNewline(key))
        onError(key, "MULTILINE_IMPLICIT_KEY", "Implicit keys of flow sequence pairs need to be on a single line");
    }
    if (i7 === 0) {
      if (props.comma)
        onError(props.comma, "UNEXPECTED_TOKEN", `Unexpected , in ${fcName}`);
    } else {
      if (!props.comma)
        onError(props.start, "MISSING_CHAR", `Missing , between ${fcName} items`);
      if (props.comment) {
        let prevItemComment = "";
        loop:
          for (const st of start) {
            switch (st.type) {
              case "comma":
              case "space":
                break;
              case "comment":
                prevItemComment = st.source.substring(1);
                break loop;
              default:
                break loop;
            }
          }
        if (prevItemComment) {
          let prev = coll.items[coll.items.length - 1];
          if (isPair(prev))
            prev = prev.value ?? prev.key;
          if (prev.comment)
            prev.comment += `
` + prevItemComment;
          else
            prev.comment = prevItemComment;
          props.comment = props.comment.substring(prevItemComment.length + 1);
        }
      }
    }
    if (!isMap2 && !sep && !props.found) {
      const valueNode = value ? composeNode(ctx, value, props, onError) : composeEmptyNode(ctx, props.end, sep, null, props, onError);
      coll.items.push(valueNode);
      offset = valueNode.range[2];
      if (isBlock(value))
        onError(valueNode.range, "BLOCK_IN_FLOW", blockMsg);
    } else {
      ctx.atKey = true;
      const keyStart = props.end;
      const keyNode = key ? composeNode(ctx, key, props, onError) : composeEmptyNode(ctx, keyStart, start, null, props, onError);
      if (isBlock(key))
        onError(keyNode.range, "BLOCK_IN_FLOW", blockMsg);
      ctx.atKey = false;
      const valueProps = resolveProps(sep ?? [], {
        flow: fcName,
        indicator: "map-value-ind",
        next: value,
        offset: keyNode.range[2],
        onError,
        parentIndent: fc.indent,
        startOnNewline: false
      });
      if (valueProps.found) {
        if (!isMap2 && !props.found && ctx.options.strict) {
          if (sep)
            for (const st of sep) {
              if (st === valueProps.found)
                break;
              if (st.type === "newline") {
                onError(st, "MULTILINE_IMPLICIT_KEY", "Implicit keys of flow sequence pairs need to be on a single line");
                break;
              }
            }
          if (props.start < valueProps.found.offset - 1024)
            onError(valueProps.found, "KEY_OVER_1024_CHARS", "The : indicator must be at most 1024 chars after the start of an implicit flow sequence key");
        }
      } else if (value) {
        if ("source" in value && value.source?.[0] === ":")
          onError(value, "MISSING_CHAR", `Missing space after : in ${fcName}`);
        else
          onError(valueProps.start, "MISSING_CHAR", `Missing , or : between ${fcName} items`);
      }
      const valueNode = value ? composeNode(ctx, value, valueProps, onError) : valueProps.found ? composeEmptyNode(ctx, valueProps.end, sep, null, valueProps, onError) : null;
      if (valueNode) {
        if (isBlock(value))
          onError(valueNode.range, "BLOCK_IN_FLOW", blockMsg);
      } else if (valueProps.comment) {
        if (keyNode.comment)
          keyNode.comment += `
` + valueProps.comment;
        else
          keyNode.comment = valueProps.comment;
      }
      const pair = new Pair(keyNode, valueNode);
      if (ctx.options.keepSourceTokens)
        pair.srcToken = collItem;
      if (isMap2) {
        const map2 = coll;
        if (mapIncludes(ctx, map2.items, keyNode))
          onError(keyStart, "DUPLICATE_KEY", "Map keys must be unique");
        map2.items.push(pair);
      } else {
        const map2 = new YAMLMap(ctx.schema);
        map2.flow = true;
        map2.items.push(pair);
        const endRange = (valueNode ?? keyNode).range;
        map2.range = [keyNode.range[0], endRange[1], endRange[2]];
        coll.items.push(map2);
      }
      offset = valueNode ? valueNode.range[2] : valueProps.end;
    }
  }
  const expectedEnd = isMap2 ? "}" : "]";
  const [ce, ...ee] = fc.end;
  let cePos = offset;
  if (ce?.source === expectedEnd)
    cePos = ce.offset + ce.source.length;
  else {
    const name = fcName[0].toUpperCase() + fcName.substring(1);
    const msg = atRoot ? `${name} must end with a ${expectedEnd}` : `${name} in block collection must be sufficiently indented and end with a ${expectedEnd}`;
    onError(offset, atRoot ? "MISSING_CHAR" : "BAD_INDENT", msg);
    if (ce && ce.source.length !== 1)
      ee.unshift(ce);
  }
  if (ee.length > 0) {
    const end = resolveEnd(ee, cePos, ctx.options.strict, onError);
    if (end.comment) {
      if (coll.comment)
        coll.comment += `
` + end.comment;
      else
        coll.comment = end.comment;
    }
    coll.range = [fc.offset, cePos, end.offset];
  } else {
    coll.range = [fc.offset, cePos, cePos];
  }
  return coll;
}

// node_modules/yaml/browser/dist/compose/compose-collection.js
function resolveCollection(CN, ctx, token, onError, tagName, tag) {
  const coll = token.type === "block-map" ? resolveBlockMap(CN, ctx, token, onError, tag) : token.type === "block-seq" ? resolveBlockSeq(CN, ctx, token, onError, tag) : resolveFlowCollection(CN, ctx, token, onError, tag);
  const Coll = coll.constructor;
  if (tagName === "!" || tagName === Coll.tagName) {
    coll.tag = Coll.tagName;
    return coll;
  }
  if (tagName)
    coll.tag = tagName;
  return coll;
}
function composeCollection(CN, ctx, token, props, onError) {
  const tagToken = props.tag;
  const tagName = !tagToken ? null : ctx.directives.tagName(tagToken.source, (msg) => onError(tagToken, "TAG_RESOLVE_FAILED", msg));
  if (token.type === "block-seq") {
    const { anchor, newlineAfterProp: nl } = props;
    const lastProp = anchor && tagToken ? anchor.offset > tagToken.offset ? anchor : tagToken : anchor ?? tagToken;
    if (lastProp && (!nl || nl.offset < lastProp.offset)) {
      const message = "Missing newline after block sequence props";
      onError(lastProp, "MISSING_CHAR", message);
    }
  }
  const expType = token.type === "block-map" ? "map" : token.type === "block-seq" ? "seq" : token.start.source === "{" ? "map" : "seq";
  if (!tagToken || !tagName || tagName === "!" || tagName === YAMLMap.tagName && expType === "map" || tagName === YAMLSeq.tagName && expType === "seq") {
    return resolveCollection(CN, ctx, token, onError, tagName);
  }
  let tag = ctx.schema.tags.find((t5) => t5.tag === tagName && t5.collection === expType);
  if (!tag) {
    const kt = ctx.schema.knownTags[tagName];
    if (kt?.collection === expType) {
      ctx.schema.tags.push(Object.assign({}, kt, { default: false }));
      tag = kt;
    } else {
      if (kt) {
        onError(tagToken, "BAD_COLLECTION_TYPE", `${kt.tag} used for ${expType} collection, but expects ${kt.collection ?? "scalar"}`, true);
      } else {
        onError(tagToken, "TAG_RESOLVE_FAILED", `Unresolved tag: ${tagName}`, true);
      }
      return resolveCollection(CN, ctx, token, onError, tagName);
    }
  }
  const coll = resolveCollection(CN, ctx, token, onError, tagName, tag);
  const res = tag.resolve?.(coll, (msg) => onError(tagToken, "TAG_RESOLVE_FAILED", msg), ctx.options) ?? coll;
  const node = isNode(res) ? res : new Scalar(res);
  node.range = coll.range;
  node.tag = tagName;
  if (tag?.format)
    node.format = tag.format;
  return node;
}

// node_modules/yaml/browser/dist/compose/resolve-block-scalar.js
function resolveBlockScalar(ctx, scalar, onError) {
  const start = scalar.offset;
  const header = parseBlockScalarHeader(scalar, ctx.options.strict, onError);
  if (!header)
    return { value: "", type: null, comment: "", range: [start, start, start] };
  const type = header.mode === ">" ? Scalar.BLOCK_FOLDED : Scalar.BLOCK_LITERAL;
  const lines = scalar.source ? splitLines(scalar.source) : [];
  let chompStart = lines.length;
  for (let i7 = lines.length - 1;i7 >= 0; --i7) {
    const content = lines[i7][1];
    if (content === "" || content === "\r")
      chompStart = i7;
    else
      break;
  }
  if (chompStart === 0) {
    const value2 = header.chomp === "+" && lines.length > 0 ? `
`.repeat(Math.max(1, lines.length - 1)) : "";
    let end2 = start + header.length;
    if (scalar.source)
      end2 += scalar.source.length;
    return { value: value2, type, comment: header.comment, range: [start, end2, end2] };
  }
  let trimIndent = scalar.indent + header.indent;
  let offset = scalar.offset + header.length;
  let contentStart = 0;
  for (let i7 = 0;i7 < chompStart; ++i7) {
    const [indent, content] = lines[i7];
    if (content === "" || content === "\r") {
      if (header.indent === 0 && indent.length > trimIndent)
        trimIndent = indent.length;
    } else {
      if (indent.length < trimIndent) {
        const message = "Block scalars with more-indented leading empty lines must use an explicit indentation indicator";
        onError(offset + indent.length, "MISSING_CHAR", message);
      }
      if (header.indent === 0)
        trimIndent = indent.length;
      contentStart = i7;
      if (trimIndent === 0 && !ctx.atRoot) {
        const message = "Block scalar values in collections must be indented";
        onError(offset, "BAD_INDENT", message);
      }
      break;
    }
    offset += indent.length + content.length + 1;
  }
  for (let i7 = lines.length - 1;i7 >= chompStart; --i7) {
    if (lines[i7][0].length > trimIndent)
      chompStart = i7 + 1;
  }
  let value = "";
  let sep = "";
  let prevMoreIndented = false;
  for (let i7 = 0;i7 < contentStart; ++i7)
    value += lines[i7][0].slice(trimIndent) + `
`;
  for (let i7 = contentStart;i7 < chompStart; ++i7) {
    let [indent, content] = lines[i7];
    offset += indent.length + content.length + 1;
    const crlf = content[content.length - 1] === "\r";
    if (crlf)
      content = content.slice(0, -1);
    if (content && indent.length < trimIndent) {
      const src = header.indent ? "explicit indentation indicator" : "first line";
      const message = `Block scalar lines must not be less indented than their ${src}`;
      onError(offset - content.length - (crlf ? 2 : 1), "BAD_INDENT", message);
      indent = "";
    }
    if (type === Scalar.BLOCK_LITERAL) {
      value += sep + indent.slice(trimIndent) + content;
      sep = `
`;
    } else if (indent.length > trimIndent || content[0] === "\t") {
      if (sep === " ")
        sep = `
`;
      else if (!prevMoreIndented && sep === `
`)
        sep = `

`;
      value += sep + indent.slice(trimIndent) + content;
      sep = `
`;
      prevMoreIndented = true;
    } else if (content === "") {
      if (sep === `
`)
        value += `
`;
      else
        sep = `
`;
    } else {
      value += sep + content;
      sep = " ";
      prevMoreIndented = false;
    }
  }
  switch (header.chomp) {
    case "-":
      break;
    case "+":
      for (let i7 = chompStart;i7 < lines.length; ++i7)
        value += `
` + lines[i7][0].slice(trimIndent);
      if (value[value.length - 1] !== `
`)
        value += `
`;
      break;
    default:
      value += `
`;
  }
  const end = start + header.length + scalar.source.length;
  return { value, type, comment: header.comment, range: [start, end, end] };
}
function parseBlockScalarHeader({ offset, props }, strict, onError) {
  if (props[0].type !== "block-scalar-header") {
    onError(props[0], "IMPOSSIBLE", "Block scalar header not found");
    return null;
  }
  const { source } = props[0];
  const mode = source[0];
  let indent = 0;
  let chomp = "";
  let error = -1;
  for (let i7 = 1;i7 < source.length; ++i7) {
    const ch = source[i7];
    if (!chomp && (ch === "-" || ch === "+"))
      chomp = ch;
    else {
      const n4 = Number(ch);
      if (!indent && n4)
        indent = n4;
      else if (error === -1)
        error = offset + i7;
    }
  }
  if (error !== -1)
    onError(error, "UNEXPECTED_TOKEN", `Block scalar header includes extra characters: ${source}`);
  let hasSpace = false;
  let comment = "";
  let length = source.length;
  for (let i7 = 1;i7 < props.length; ++i7) {
    const token = props[i7];
    switch (token.type) {
      case "space":
        hasSpace = true;
      case "newline":
        length += token.source.length;
        break;
      case "comment":
        if (strict && !hasSpace) {
          const message = "Comments must be separated from other tokens by white space characters";
          onError(token, "MISSING_CHAR", message);
        }
        length += token.source.length;
        comment = token.source.substring(1);
        break;
      case "error":
        onError(token, "UNEXPECTED_TOKEN", token.message);
        length += token.source.length;
        break;
      default: {
        const message = `Unexpected token in block scalar header: ${token.type}`;
        onError(token, "UNEXPECTED_TOKEN", message);
        const ts = token.source;
        if (ts && typeof ts === "string")
          length += ts.length;
      }
    }
  }
  return { mode, indent, chomp, comment, length };
}
function splitLines(source) {
  const split = source.split(/\n( *)/);
  const first = split[0];
  const m3 = first.match(/^( *)/);
  const line0 = m3?.[1] ? [m3[1], first.slice(m3[1].length)] : ["", first];
  const lines = [line0];
  for (let i7 = 1;i7 < split.length; i7 += 2)
    lines.push([split[i7], split[i7 + 1]]);
  return lines;
}

// node_modules/yaml/browser/dist/compose/resolve-flow-scalar.js
function resolveFlowScalar(scalar, strict, onError) {
  const { offset, type, source, end } = scalar;
  let _type;
  let value;
  const _onError = (rel, code, msg) => onError(offset + rel, code, msg);
  switch (type) {
    case "scalar":
      _type = Scalar.PLAIN;
      value = plainValue(source, _onError);
      break;
    case "single-quoted-scalar":
      _type = Scalar.QUOTE_SINGLE;
      value = singleQuotedValue(source, _onError);
      break;
    case "double-quoted-scalar":
      _type = Scalar.QUOTE_DOUBLE;
      value = doubleQuotedValue(source, _onError);
      break;
    default:
      onError(scalar, "UNEXPECTED_TOKEN", `Expected a flow scalar value, but found: ${type}`);
      return {
        value: "",
        type: null,
        comment: "",
        range: [offset, offset + source.length, offset + source.length]
      };
  }
  const valueEnd = offset + source.length;
  const re = resolveEnd(end, valueEnd, strict, onError);
  return {
    value,
    type: _type,
    comment: re.comment,
    range: [offset, valueEnd, re.offset]
  };
}
function plainValue(source, onError) {
  let badChar = "";
  switch (source[0]) {
    case "\t":
      badChar = "a tab character";
      break;
    case ",":
      badChar = "flow indicator character ,";
      break;
    case "%":
      badChar = "directive indicator character %";
      break;
    case "|":
    case ">": {
      badChar = `block scalar indicator ${source[0]}`;
      break;
    }
    case "@":
    case "`": {
      badChar = `reserved character ${source[0]}`;
      break;
    }
  }
  if (badChar)
    onError(0, "BAD_SCALAR_START", `Plain value cannot start with ${badChar}`);
  return unfoldLines(source);
}
function singleQuotedValue(source, onError) {
  if (source[source.length - 1] !== "'" || source.length === 1)
    onError(source.length, "MISSING_CHAR", "Missing closing 'quote");
  return unfoldLines(source.slice(1, -1)).replace(/''/g, "'");
}
function unfoldLines(source) {
  const line = /(.*?)\r?\n/sy;
  let match = line.exec(source);
  if (!match)
    return source;
  let trimEnd, trimBoth;
  try {
    trimEnd = new RegExp("(?<![ \t])[ \t]+$");
    trimBoth = new RegExp("^[ \t]+|(?<![ \t])[ \t]+$", "g");
  } catch {
    trimEnd = /[ \t]+$/;
    trimBoth = /^[ \t]+|[ \t]+$/g;
  }
  let res = match[1].replace(trimEnd, "");
  let sep = " ";
  let pos = line.lastIndex;
  while (match = line.exec(source)) {
    const lm = match[1].replace(trimBoth, "");
    if (lm === "") {
      if (sep === `
`)
        res += sep;
      else
        sep = `
`;
    } else {
      res += sep + lm;
      sep = " ";
    }
    pos = line.lastIndex;
  }
  const last = /[ \t]*(.*)/sy;
  last.lastIndex = pos;
  match = last.exec(source);
  return res + sep + (match?.[1] ?? "");
}
function doubleQuotedValue(source, onError) {
  let res = "";
  for (let i7 = 1;i7 < source.length - 1; ++i7) {
    const ch = source[i7];
    if (ch === "\r" && source[i7 + 1] === `
`)
      continue;
    if (ch === `
`) {
      const { fold, offset } = foldNewline(source, i7);
      res += fold;
      i7 = offset;
    } else if (ch === "\\") {
      let next = source[++i7];
      const cc = escapeCodes[next];
      if (cc)
        res += cc;
      else if (next === `
`) {
        next = source[i7 + 1];
        while (next === " " || next === "\t")
          next = source[++i7 + 1];
      } else if (next === "\r" && source[i7 + 1] === `
`) {
        next = source[++i7 + 1];
        while (next === " " || next === "\t")
          next = source[++i7 + 1];
      } else if (next === "x" || next === "u" || next === "U") {
        const length = next === "x" ? 2 : next === "u" ? 4 : 8;
        res += parseCharCode(source, i7 + 1, length, onError);
        i7 += length;
      } else {
        const raw = source.substr(i7 - 1, 2);
        onError(i7 - 1, "BAD_DQ_ESCAPE", `Invalid escape sequence ${raw}`);
        res += raw;
      }
    } else if (ch === " " || ch === "\t") {
      const wsStart = i7;
      let next = source[i7 + 1];
      while (next === " " || next === "\t")
        next = source[++i7 + 1];
      if (next !== `
` && !(next === "\r" && source[i7 + 2] === `
`))
        res += i7 > wsStart ? source.slice(wsStart, i7 + 1) : ch;
    } else {
      res += ch;
    }
  }
  if (source[source.length - 1] !== '"' || source.length === 1)
    onError(source.length, "MISSING_CHAR", 'Missing closing "quote');
  return res;
}
function foldNewline(source, offset) {
  let fold = "";
  let ch = source[offset + 1];
  while (ch === " " || ch === "\t" || ch === `
` || ch === "\r") {
    if (ch === "\r" && source[offset + 2] !== `
`)
      break;
    if (ch === `
`)
      fold += `
`;
    offset += 1;
    ch = source[offset + 1];
  }
  if (!fold)
    fold = " ";
  return { fold, offset };
}
var escapeCodes = {
  "0": "\x00",
  a: "\x07",
  b: "\b",
  e: "\x1B",
  f: "\f",
  n: `
`,
  r: "\r",
  t: "\t",
  v: "\v",
  N: "",
  _: " ",
  L: "\u2028",
  P: "\u2029",
  " ": " ",
  '"': '"',
  "/": "/",
  "\\": "\\",
  "\t": "\t"
};
function parseCharCode(source, offset, length, onError) {
  const cc = source.substr(offset, length);
  const ok = cc.length === length && /^[0-9a-fA-F]+$/.test(cc);
  const code = ok ? parseInt(cc, 16) : NaN;
  try {
    return String.fromCodePoint(code);
  } catch {
    const raw = source.substr(offset - 2, length + 2);
    onError(offset - 2, "BAD_DQ_ESCAPE", `Invalid escape sequence ${raw}`);
    return raw;
  }
}

// node_modules/yaml/browser/dist/compose/compose-scalar.js
function composeScalar(ctx, token, tagToken, onError) {
  const { value, type, comment, range } = token.type === "block-scalar" ? resolveBlockScalar(ctx, token, onError) : resolveFlowScalar(token, ctx.options.strict, onError);
  const tagName = tagToken ? ctx.directives.tagName(tagToken.source, (msg) => onError(tagToken, "TAG_RESOLVE_FAILED", msg)) : null;
  let tag;
  if (ctx.options.stringKeys && ctx.atKey) {
    tag = ctx.schema[SCALAR];
  } else if (tagName)
    tag = findScalarTagByName(ctx.schema, value, tagName, tagToken, onError);
  else if (token.type === "scalar")
    tag = findScalarTagByTest(ctx, value, token, onError);
  else
    tag = ctx.schema[SCALAR];
  let scalar;
  try {
    const res = tag.resolve(value, (msg) => onError(tagToken ?? token, "TAG_RESOLVE_FAILED", msg), ctx.options);
    scalar = isScalar(res) ? res : new Scalar(res);
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    onError(tagToken ?? token, "TAG_RESOLVE_FAILED", msg);
    scalar = new Scalar(value);
  }
  scalar.range = range;
  scalar.source = value;
  if (type)
    scalar.type = type;
  if (tagName)
    scalar.tag = tagName;
  if (tag.format)
    scalar.format = tag.format;
  if (comment)
    scalar.comment = comment;
  return scalar;
}
function findScalarTagByName(schema4, value, tagName, tagToken, onError) {
  if (tagName === "!")
    return schema4[SCALAR];
  const matchWithTest = [];
  for (const tag of schema4.tags) {
    if (!tag.collection && tag.tag === tagName) {
      if (tag.default && tag.test)
        matchWithTest.push(tag);
      else
        return tag;
    }
  }
  for (const tag of matchWithTest)
    if (tag.test?.test(value))
      return tag;
  const kt = schema4.knownTags[tagName];
  if (kt && !kt.collection) {
    schema4.tags.push(Object.assign({}, kt, { default: false, test: undefined }));
    return kt;
  }
  onError(tagToken, "TAG_RESOLVE_FAILED", `Unresolved tag: ${tagName}`, tagName !== "tag:yaml.org,2002:str");
  return schema4[SCALAR];
}
function findScalarTagByTest({ atKey, directives, schema: schema4 }, value, token, onError) {
  const tag = schema4.tags.find((tag2) => (tag2.default === true || atKey && tag2.default === "key") && tag2.test?.test(value)) || schema4[SCALAR];
  if (schema4.compat) {
    const compat = schema4.compat.find((tag2) => tag2.default && tag2.test?.test(value)) ?? schema4[SCALAR];
    if (tag.tag !== compat.tag) {
      const ts = directives.tagString(tag.tag);
      const cs = directives.tagString(compat.tag);
      const msg = `Value may be parsed as either ${ts} or ${cs}`;
      onError(token, "TAG_RESOLVE_FAILED", msg, true);
    }
  }
  return tag;
}

// node_modules/yaml/browser/dist/compose/util-empty-scalar-position.js
function emptyScalarPosition(offset, before, pos) {
  if (before) {
    pos ?? (pos = before.length);
    for (let i7 = pos - 1;i7 >= 0; --i7) {
      let st = before[i7];
      switch (st.type) {
        case "space":
        case "comment":
        case "newline":
          offset -= st.source.length;
          continue;
      }
      st = before[++i7];
      while (st?.type === "space") {
        offset += st.source.length;
        st = before[++i7];
      }
      break;
    }
  }
  return offset;
}

// node_modules/yaml/browser/dist/compose/compose-node.js
var CN = { composeNode, composeEmptyNode };
function composeNode(ctx, token, props, onError) {
  const atKey = ctx.atKey;
  const { spaceBefore, comment, anchor, tag } = props;
  let node;
  let isSrcToken = true;
  switch (token.type) {
    case "alias":
      node = composeAlias(ctx, token, onError);
      if (anchor || tag)
        onError(token, "ALIAS_PROPS", "An alias node must not specify any properties");
      break;
    case "scalar":
    case "single-quoted-scalar":
    case "double-quoted-scalar":
    case "block-scalar":
      node = composeScalar(ctx, token, tag, onError);
      if (anchor)
        node.anchor = anchor.source.substring(1);
      break;
    case "block-map":
    case "block-seq":
    case "flow-collection":
      try {
        node = composeCollection(CN, ctx, token, props, onError);
        if (anchor)
          node.anchor = anchor.source.substring(1);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        onError(token, "RESOURCE_EXHAUSTION", message);
      }
      break;
    default: {
      const message = token.type === "error" ? token.message : `Unsupported token (type: ${token.type})`;
      onError(token, "UNEXPECTED_TOKEN", message);
      isSrcToken = false;
    }
  }
  node ?? (node = composeEmptyNode(ctx, token.offset, undefined, null, props, onError));
  if (anchor && node.anchor === "")
    onError(anchor, "BAD_ALIAS", "Anchor cannot be an empty string");
  if (atKey && ctx.options.stringKeys && (!isScalar(node) || typeof node.value !== "string" || node.tag && node.tag !== "tag:yaml.org,2002:str")) {
    const msg = "With stringKeys, all keys must be strings";
    onError(tag ?? token, "NON_STRING_KEY", msg);
  }
  if (spaceBefore)
    node.spaceBefore = true;
  if (comment) {
    if (token.type === "scalar" && token.source === "")
      node.comment = comment;
    else
      node.commentBefore = comment;
  }
  if (ctx.options.keepSourceTokens && isSrcToken)
    node.srcToken = token;
  return node;
}
function composeEmptyNode(ctx, offset, before, pos, { spaceBefore, comment, anchor, tag, end }, onError) {
  const token = {
    type: "scalar",
    offset: emptyScalarPosition(offset, before, pos),
    indent: -1,
    source: ""
  };
  const node = composeScalar(ctx, token, tag, onError);
  if (anchor) {
    node.anchor = anchor.source.substring(1);
    if (node.anchor === "")
      onError(anchor, "BAD_ALIAS", "Anchor cannot be an empty string");
  }
  if (spaceBefore)
    node.spaceBefore = true;
  if (comment) {
    node.comment = comment;
    node.range[2] = end;
  }
  return node;
}
function composeAlias({ options }, { offset, source, end }, onError) {
  const alias = new Alias(source.substring(1));
  if (alias.source === "")
    onError(offset, "BAD_ALIAS", "Alias cannot be an empty string");
  if (alias.source.endsWith(":"))
    onError(offset + source.length - 1, "BAD_ALIAS", "Alias ending in : is ambiguous", true);
  const valueEnd = offset + source.length;
  const re = resolveEnd(end, valueEnd, options.strict, onError);
  alias.range = [offset, valueEnd, re.offset];
  if (re.comment)
    alias.comment = re.comment;
  return alias;
}

// node_modules/yaml/browser/dist/compose/compose-doc.js
function composeDoc(options, directives, { offset, start, value, end }, onError) {
  const opts = Object.assign({ _directives: directives }, options);
  const doc = new Document2(undefined, opts);
  const ctx = {
    atKey: false,
    atRoot: true,
    directives: doc.directives,
    options: doc.options,
    schema: doc.schema
  };
  const props = resolveProps(start, {
    indicator: "doc-start",
    next: value ?? end?.[0],
    offset,
    onError,
    parentIndent: 0,
    startOnNewline: true
  });
  if (props.found) {
    doc.directives.docStart = true;
    if (value && (value.type === "block-map" || value.type === "block-seq") && !props.hasNewline)
      onError(props.end, "MISSING_CHAR", "Block collection cannot start on same line with directives-end marker");
  }
  doc.contents = value ? composeNode(ctx, value, props, onError) : composeEmptyNode(ctx, props.end, start, null, props, onError);
  const contentEnd = doc.contents.range[2];
  const re = resolveEnd(end, contentEnd, false, onError);
  if (re.comment)
    doc.comment = re.comment;
  doc.range = [offset, contentEnd, re.offset];
  return doc;
}

// node_modules/yaml/browser/dist/compose/composer.js
function getErrorPos(src) {
  if (typeof src === "number")
    return [src, src + 1];
  if (Array.isArray(src))
    return src.length === 2 ? src : [src[0], src[1]];
  const { offset, source } = src;
  return [offset, offset + (typeof source === "string" ? source.length : 1)];
}
function parsePrelude(prelude) {
  let comment = "";
  let atComment = false;
  let afterEmptyLine = false;
  for (let i7 = 0;i7 < prelude.length; ++i7) {
    const source = prelude[i7];
    switch (source[0]) {
      case "#":
        comment += (comment === "" ? "" : afterEmptyLine ? `

` : `
`) + (source.substring(1) || " ");
        atComment = true;
        afterEmptyLine = false;
        break;
      case "%":
        if (prelude[i7 + 1]?.[0] !== "#")
          i7 += 1;
        atComment = false;
        break;
      default:
        if (!atComment)
          afterEmptyLine = true;
        atComment = false;
    }
  }
  return { comment, afterEmptyLine };
}

class Composer {
  constructor(options = {}) {
    this.doc = null;
    this.atDirectives = false;
    this.prelude = [];
    this.errors = [];
    this.warnings = [];
    this.onError = (source, code, message, warning) => {
      const pos = getErrorPos(source);
      if (warning)
        this.warnings.push(new YAMLWarning(pos, code, message));
      else
        this.errors.push(new YAMLParseError(pos, code, message));
    };
    this.directives = new Directives({ version: options.version || "1.2" });
    this.options = options;
  }
  decorate(doc, afterDoc) {
    const { comment, afterEmptyLine } = parsePrelude(this.prelude);
    if (comment) {
      const dc = doc.contents;
      if (afterDoc) {
        doc.comment = doc.comment ? `${doc.comment}
${comment}` : comment;
      } else if (afterEmptyLine || doc.directives.docStart || !dc) {
        doc.commentBefore = comment;
      } else if (isCollection(dc) && !dc.flow && dc.items.length > 0) {
        let it = dc.items[0];
        if (isPair(it))
          it = it.key;
        const cb = it.commentBefore;
        it.commentBefore = cb ? `${comment}
${cb}` : comment;
      } else {
        const cb = dc.commentBefore;
        dc.commentBefore = cb ? `${comment}
${cb}` : comment;
      }
    }
    if (afterDoc) {
      for (let i7 = 0;i7 < this.errors.length; ++i7)
        doc.errors.push(this.errors[i7]);
      for (let i7 = 0;i7 < this.warnings.length; ++i7)
        doc.warnings.push(this.warnings[i7]);
    } else {
      doc.errors = this.errors;
      doc.warnings = this.warnings;
    }
    this.prelude = [];
    this.errors = [];
    this.warnings = [];
  }
  streamInfo() {
    return {
      comment: parsePrelude(this.prelude).comment,
      directives: this.directives,
      errors: this.errors,
      warnings: this.warnings
    };
  }
  *compose(tokens, forceDoc = false, endOffset = -1) {
    for (const token of tokens)
      yield* this.next(token);
    yield* this.end(forceDoc, endOffset);
  }
  *next(token) {
    switch (token.type) {
      case "directive":
        this.directives.add(token.source, (offset, message, warning) => {
          const pos = getErrorPos(token);
          pos[0] += offset;
          this.onError(pos, "BAD_DIRECTIVE", message, warning);
        });
        this.prelude.push(token.source);
        this.atDirectives = true;
        break;
      case "document": {
        const doc = composeDoc(this.options, this.directives, token, this.onError);
        if (this.atDirectives && !doc.directives.docStart)
          this.onError(token, "MISSING_CHAR", "Missing directives-end/doc-start indicator line");
        this.decorate(doc, false);
        if (this.doc)
          yield this.doc;
        this.doc = doc;
        this.atDirectives = false;
        break;
      }
      case "byte-order-mark":
      case "space":
        break;
      case "comment":
      case "newline":
        this.prelude.push(token.source);
        break;
      case "error": {
        const msg = token.source ? `${token.message}: ${JSON.stringify(token.source)}` : token.message;
        const error = new YAMLParseError(getErrorPos(token), "UNEXPECTED_TOKEN", msg);
        if (this.atDirectives || !this.doc)
          this.errors.push(error);
        else
          this.doc.errors.push(error);
        break;
      }
      case "doc-end": {
        if (!this.doc) {
          const msg = "Unexpected doc-end without preceding document";
          this.errors.push(new YAMLParseError(getErrorPos(token), "UNEXPECTED_TOKEN", msg));
          break;
        }
        this.doc.directives.docEnd = true;
        const end = resolveEnd(token.end, token.offset + token.source.length, this.doc.options.strict, this.onError);
        this.decorate(this.doc, true);
        if (end.comment) {
          const dc = this.doc.comment;
          this.doc.comment = dc ? `${dc}
${end.comment}` : end.comment;
        }
        this.doc.range[2] = end.offset;
        break;
      }
      default:
        this.errors.push(new YAMLParseError(getErrorPos(token), "UNEXPECTED_TOKEN", `Unsupported token ${token.type}`));
    }
  }
  *end(forceDoc = false, endOffset = -1) {
    if (this.doc) {
      this.decorate(this.doc, true);
      yield this.doc;
      this.doc = null;
    } else if (forceDoc) {
      const opts = Object.assign({ _directives: this.directives }, this.options);
      const doc = new Document2(undefined, opts);
      if (this.atDirectives)
        this.onError(endOffset, "MISSING_CHAR", "Missing directives-end indicator line");
      doc.range = [0, endOffset, endOffset];
      this.decorate(doc, false);
      yield doc;
    }
  }
}
// node_modules/yaml/browser/dist/parse/cst-visit.js
var BREAK2 = Symbol("break visit");
var SKIP2 = Symbol("skip children");
var REMOVE2 = Symbol("remove item");
function visit2(cst, visitor) {
  if ("type" in cst && cst.type === "document")
    cst = { start: cst.start, value: cst.value };
  _visit(Object.freeze([]), cst, visitor);
}
visit2.BREAK = BREAK2;
visit2.SKIP = SKIP2;
visit2.REMOVE = REMOVE2;
visit2.itemAtPath = (cst, path) => {
  let item = cst;
  for (const [field, index] of path) {
    const tok = item?.[field];
    if (tok && "items" in tok) {
      item = tok.items[index];
    } else
      return;
  }
  return item;
};
visit2.parentCollection = (cst, path) => {
  const parent = visit2.itemAtPath(cst, path.slice(0, -1));
  const field = path[path.length - 1][0];
  const coll = parent?.[field];
  if (coll && "items" in coll)
    return coll;
  throw new Error("Parent collection not found");
};
function _visit(path, item, visitor) {
  let ctrl = visitor(item, path);
  if (typeof ctrl === "symbol")
    return ctrl;
  for (const field of ["key", "value"]) {
    const token = item[field];
    if (token && "items" in token) {
      for (let i7 = 0;i7 < token.items.length; ++i7) {
        const ci = _visit(Object.freeze(path.concat([[field, i7]])), token.items[i7], visitor);
        if (typeof ci === "number")
          i7 = ci - 1;
        else if (ci === BREAK2)
          return BREAK2;
        else if (ci === REMOVE2) {
          token.items.splice(i7, 1);
          i7 -= 1;
        }
      }
      if (typeof ctrl === "function" && field === "key")
        ctrl = ctrl(item, path);
    }
  }
  return typeof ctrl === "function" ? ctrl(item, path) : ctrl;
}

// node_modules/yaml/browser/dist/parse/cst.js
var BOM = "\uFEFF";
var DOCUMENT = "\x02";
var FLOW_END = "\x18";
var SCALAR2 = "\x1F";
function tokenType(source) {
  switch (source) {
    case BOM:
      return "byte-order-mark";
    case DOCUMENT:
      return "doc-mode";
    case FLOW_END:
      return "flow-error-end";
    case SCALAR2:
      return "scalar";
    case "---":
      return "doc-start";
    case "...":
      return "doc-end";
    case "":
    case `
`:
    case `\r
`:
      return "newline";
    case "-":
      return "seq-item-ind";
    case "?":
      return "explicit-key-ind";
    case ":":
      return "map-value-ind";
    case "{":
      return "flow-map-start";
    case "}":
      return "flow-map-end";
    case "[":
      return "flow-seq-start";
    case "]":
      return "flow-seq-end";
    case ",":
      return "comma";
  }
  switch (source[0]) {
    case " ":
    case "\t":
      return "space";
    case "#":
      return "comment";
    case "%":
      return "directive-line";
    case "*":
      return "alias";
    case "&":
      return "anchor";
    case "!":
      return "tag";
    case "'":
      return "single-quoted-scalar";
    case '"':
      return "double-quoted-scalar";
    case "|":
    case ">":
      return "block-scalar-header";
  }
  return null;
}

// node_modules/yaml/browser/dist/parse/lexer.js
function isEmpty(ch) {
  switch (ch) {
    case undefined:
    case " ":
    case `
`:
    case "\r":
    case "\t":
      return true;
    default:
      return false;
  }
}
var hexDigits = new Set("0123456789ABCDEFabcdef");
var tagChars = new Set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-#;/?:@&=+$_.!~*'()");
var flowIndicatorChars = new Set(",[]{}");
var invalidAnchorChars = new Set(` ,[]{}
\r	`);
var isNotAnchorChar = (ch) => !ch || invalidAnchorChars.has(ch);

class Lexer {
  constructor() {
    this.atEnd = false;
    this.blockScalarIndent = -1;
    this.blockScalarKeep = false;
    this.buffer = "";
    this.flowKey = false;
    this.flowLevel = 0;
    this.indentNext = 0;
    this.indentValue = 0;
    this.lineEndPos = null;
    this.next = null;
    this.pos = 0;
  }
  *lex(source, incomplete = false) {
    if (source) {
      if (typeof source !== "string")
        throw TypeError("source is not a string");
      this.buffer = this.buffer ? this.buffer + source : source;
      this.lineEndPos = null;
    }
    this.atEnd = !incomplete;
    let next = this.next ?? "stream";
    while (next && (incomplete || this.hasChars(1)))
      next = yield* this.parseNext(next);
  }
  atLineEnd() {
    let i7 = this.pos;
    let ch = this.buffer[i7];
    while (ch === " " || ch === "\t")
      ch = this.buffer[++i7];
    if (!ch || ch === "#" || ch === `
`)
      return true;
    if (ch === "\r")
      return this.buffer[i7 + 1] === `
`;
    return false;
  }
  charAt(n4) {
    return this.buffer[this.pos + n4];
  }
  continueScalar(offset) {
    let ch = this.buffer[offset];
    if (this.indentNext > 0) {
      let indent = 0;
      while (ch === " ")
        ch = this.buffer[++indent + offset];
      if (ch === "\r") {
        const next = this.buffer[indent + offset + 1];
        if (next === `
` || !next && !this.atEnd)
          return offset + indent + 1;
      }
      return ch === `
` || indent >= this.indentNext || !ch && !this.atEnd ? offset + indent : -1;
    }
    if (ch === "-" || ch === ".") {
      const dt = this.buffer.substr(offset, 3);
      if ((dt === "---" || dt === "...") && isEmpty(this.buffer[offset + 3]))
        return -1;
    }
    return offset;
  }
  getLine() {
    let end = this.lineEndPos;
    if (typeof end !== "number" || end !== -1 && end < this.pos) {
      end = this.buffer.indexOf(`
`, this.pos);
      this.lineEndPos = end;
    }
    if (end === -1)
      return this.atEnd ? this.buffer.substring(this.pos) : null;
    if (this.buffer[end - 1] === "\r")
      end -= 1;
    return this.buffer.substring(this.pos, end);
  }
  hasChars(n4) {
    return this.pos + n4 <= this.buffer.length;
  }
  setNext(state) {
    this.buffer = this.buffer.substring(this.pos);
    this.pos = 0;
    this.lineEndPos = null;
    this.next = state;
    return null;
  }
  peek(n4) {
    return this.buffer.substr(this.pos, n4);
  }
  *parseNext(next) {
    switch (next) {
      case "stream":
        return yield* this.parseStream();
      case "line-start":
        return yield* this.parseLineStart();
      case "block-start":
        return yield* this.parseBlockStart();
      case "doc":
        return yield* this.parseDocument();
      case "flow":
        return yield* this.parseFlowCollection();
      case "quoted-scalar":
        return yield* this.parseQuotedScalar();
      case "block-scalar":
        return yield* this.parseBlockScalar();
      case "plain-scalar":
        return yield* this.parsePlainScalar();
    }
  }
  *parseStream() {
    let line = this.getLine();
    if (line === null)
      return this.setNext("stream");
    if (line[0] === BOM) {
      yield* this.pushCount(1);
      line = line.substring(1);
    }
    if (line[0] === "%") {
      let dirEnd = line.length;
      let cs = line.indexOf("#");
      while (cs !== -1) {
        const ch = line[cs - 1];
        if (ch === " " || ch === "\t") {
          dirEnd = cs - 1;
          break;
        } else {
          cs = line.indexOf("#", cs + 1);
        }
      }
      while (true) {
        const ch = line[dirEnd - 1];
        if (ch === " " || ch === "\t")
          dirEnd -= 1;
        else
          break;
      }
      const n4 = (yield* this.pushCount(dirEnd)) + (yield* this.pushSpaces(true));
      yield* this.pushCount(line.length - n4);
      this.pushNewline();
      return "stream";
    }
    if (this.atLineEnd()) {
      const sp = yield* this.pushSpaces(true);
      yield* this.pushCount(line.length - sp);
      yield* this.pushNewline();
      return "stream";
    }
    yield DOCUMENT;
    return yield* this.parseLineStart();
  }
  *parseLineStart() {
    const ch = this.charAt(0);
    if (!ch && !this.atEnd)
      return this.setNext("line-start");
    if (ch === "-" || ch === ".") {
      if (!this.atEnd && !this.hasChars(4))
        return this.setNext("line-start");
      const s5 = this.peek(3);
      if ((s5 === "---" || s5 === "...") && isEmpty(this.charAt(3))) {
        yield* this.pushCount(3);
        this.indentValue = 0;
        this.indentNext = 0;
        return s5 === "---" ? "doc" : "stream";
      }
    }
    this.indentValue = yield* this.pushSpaces(false);
    if (this.indentNext > this.indentValue && !isEmpty(this.charAt(1)))
      this.indentNext = this.indentValue;
    return yield* this.parseBlockStart();
  }
  *parseBlockStart() {
    const [ch0, ch1] = this.peek(2);
    if (!ch1 && !this.atEnd)
      return this.setNext("block-start");
    if ((ch0 === "-" || ch0 === "?" || ch0 === ":") && isEmpty(ch1)) {
      const n4 = (yield* this.pushCount(1)) + (yield* this.pushSpaces(true));
      this.indentNext = this.indentValue + 1;
      this.indentValue += n4;
      return "block-start";
    }
    return "doc";
  }
  *parseDocument() {
    yield* this.pushSpaces(true);
    const line = this.getLine();
    if (line === null)
      return this.setNext("doc");
    let n4 = yield* this.pushIndicators();
    switch (line[n4]) {
      case "#":
        yield* this.pushCount(line.length - n4);
      case undefined:
        yield* this.pushNewline();
        return yield* this.parseLineStart();
      case "{":
      case "[":
        yield* this.pushCount(1);
        this.flowKey = false;
        this.flowLevel = 1;
        return "flow";
      case "}":
      case "]":
        yield* this.pushCount(1);
        return "doc";
      case "*":
        yield* this.pushUntil(isNotAnchorChar);
        return "doc";
      case '"':
      case "'":
        return yield* this.parseQuotedScalar();
      case "|":
      case ">":
        n4 += yield* this.parseBlockScalarHeader();
        n4 += yield* this.pushSpaces(true);
        yield* this.pushCount(line.length - n4);
        yield* this.pushNewline();
        return yield* this.parseBlockScalar();
      default:
        return yield* this.parsePlainScalar();
    }
  }
  *parseFlowCollection() {
    let nl, sp;
    let indent = -1;
    do {
      nl = yield* this.pushNewline();
      if (nl > 0) {
        sp = yield* this.pushSpaces(false);
        this.indentValue = indent = sp;
      } else {
        sp = 0;
      }
      sp += yield* this.pushSpaces(true);
    } while (nl + sp > 0);
    const line = this.getLine();
    if (line === null)
      return this.setNext("flow");
    if (indent !== -1 && indent < this.indentNext && line[0] !== "#" || indent === 0 && (line.startsWith("---") || line.startsWith("...")) && isEmpty(line[3])) {
      const atFlowEndMarker = indent === this.indentNext - 1 && this.flowLevel === 1 && (line[0] === "]" || line[0] === "}");
      if (!atFlowEndMarker) {
        this.flowLevel = 0;
        yield FLOW_END;
        return yield* this.parseLineStart();
      }
    }
    let n4 = 0;
    while (line[n4] === ",") {
      n4 += yield* this.pushCount(1);
      n4 += yield* this.pushSpaces(true);
      this.flowKey = false;
    }
    n4 += yield* this.pushIndicators();
    switch (line[n4]) {
      case undefined:
        return "flow";
      case "#":
        yield* this.pushCount(line.length - n4);
        return "flow";
      case "{":
      case "[":
        yield* this.pushCount(1);
        this.flowKey = false;
        this.flowLevel += 1;
        return "flow";
      case "}":
      case "]":
        yield* this.pushCount(1);
        this.flowKey = true;
        this.flowLevel -= 1;
        return this.flowLevel ? "flow" : "doc";
      case "*":
        yield* this.pushUntil(isNotAnchorChar);
        return "flow";
      case '"':
      case "'":
        this.flowKey = true;
        return yield* this.parseQuotedScalar();
      case ":": {
        const next = this.charAt(1);
        if (this.flowKey || isEmpty(next) || next === ",") {
          this.flowKey = false;
          yield* this.pushCount(1);
          yield* this.pushSpaces(true);
          return "flow";
        }
      }
      default:
        this.flowKey = false;
        return yield* this.parsePlainScalar();
    }
  }
  *parseQuotedScalar() {
    const quote = this.charAt(0);
    let end = this.buffer.indexOf(quote, this.pos + 1);
    if (quote === "'") {
      while (end !== -1 && this.buffer[end + 1] === "'")
        end = this.buffer.indexOf("'", end + 2);
    } else {
      while (end !== -1) {
        let n4 = 0;
        while (this.buffer[end - 1 - n4] === "\\")
          n4 += 1;
        if (n4 % 2 === 0)
          break;
        end = this.buffer.indexOf('"', end + 1);
      }
    }
    const qb = this.buffer.substring(0, end);
    let nl = qb.indexOf(`
`, this.pos);
    if (nl !== -1) {
      while (nl !== -1) {
        const cs = this.continueScalar(nl + 1);
        if (cs === -1)
          break;
        nl = qb.indexOf(`
`, cs);
      }
      if (nl !== -1) {
        end = nl - (qb[nl - 1] === "\r" ? 2 : 1);
      }
    }
    if (end === -1) {
      if (!this.atEnd)
        return this.setNext("quoted-scalar");
      end = this.buffer.length;
    }
    yield* this.pushToIndex(end + 1, false);
    return this.flowLevel ? "flow" : "doc";
  }
  *parseBlockScalarHeader() {
    this.blockScalarIndent = -1;
    this.blockScalarKeep = false;
    let i7 = this.pos;
    while (true) {
      const ch = this.buffer[++i7];
      if (ch === "+")
        this.blockScalarKeep = true;
      else if (ch > "0" && ch <= "9")
        this.blockScalarIndent = Number(ch) - 1;
      else if (ch !== "-")
        break;
    }
    return yield* this.pushUntil((ch) => isEmpty(ch) || ch === "#");
  }
  *parseBlockScalar() {
    let nl = this.pos - 1;
    let indent = 0;
    let ch;
    loop:
      for (let i8 = this.pos;ch = this.buffer[i8]; ++i8) {
        switch (ch) {
          case " ":
            indent += 1;
            break;
          case `
`:
            nl = i8;
            indent = 0;
            break;
          case "\r": {
            const next = this.buffer[i8 + 1];
            if (!next && !this.atEnd)
              return this.setNext("block-scalar");
            if (next === `
`)
              break;
          }
          default:
            break loop;
        }
      }
    if (!ch && !this.atEnd)
      return this.setNext("block-scalar");
    if (indent >= this.indentNext) {
      if (this.blockScalarIndent === -1)
        this.indentNext = indent;
      else {
        this.indentNext = this.blockScalarIndent + (this.indentNext === 0 ? 1 : this.indentNext);
      }
      do {
        const cs = this.continueScalar(nl + 1);
        if (cs === -1)
          break;
        nl = this.buffer.indexOf(`
`, cs);
      } while (nl !== -1);
      if (nl === -1) {
        if (!this.atEnd)
          return this.setNext("block-scalar");
        nl = this.buffer.length;
      }
    }
    let i7 = nl + 1;
    ch = this.buffer[i7];
    while (ch === " ")
      ch = this.buffer[++i7];
    if (ch === "\t") {
      while (ch === "\t" || ch === " " || ch === "\r" || ch === `
`)
        ch = this.buffer[++i7];
      nl = i7 - 1;
    } else if (!this.blockScalarKeep) {
      do {
        let i8 = nl - 1;
        let ch2 = this.buffer[i8];
        if (ch2 === "\r")
          ch2 = this.buffer[--i8];
        const lastChar = i8;
        while (ch2 === " ")
          ch2 = this.buffer[--i8];
        if (ch2 === `
` && i8 >= this.pos && i8 + 1 + indent > lastChar)
          nl = i8;
        else
          break;
      } while (true);
    }
    yield SCALAR2;
    yield* this.pushToIndex(nl + 1, true);
    return yield* this.parseLineStart();
  }
  *parsePlainScalar() {
    const inFlow = this.flowLevel > 0;
    let end = this.pos - 1;
    let i7 = this.pos - 1;
    let ch;
    while (ch = this.buffer[++i7]) {
      if (ch === ":") {
        const next = this.buffer[i7 + 1];
        if (isEmpty(next) || inFlow && flowIndicatorChars.has(next))
          break;
        end = i7;
      } else if (isEmpty(ch)) {
        let next = this.buffer[i7 + 1];
        if (ch === "\r") {
          if (next === `
`) {
            i7 += 1;
            ch = `
`;
            next = this.buffer[i7 + 1];
          } else
            end = i7;
        }
        if (next === "#" || inFlow && flowIndicatorChars.has(next))
          break;
        if (ch === `
`) {
          const cs = this.continueScalar(i7 + 1);
          if (cs === -1)
            break;
          i7 = Math.max(i7, cs - 2);
        }
      } else {
        if (inFlow && flowIndicatorChars.has(ch))
          break;
        end = i7;
      }
    }
    if (!ch && !this.atEnd)
      return this.setNext("plain-scalar");
    yield SCALAR2;
    yield* this.pushToIndex(end + 1, true);
    return inFlow ? "flow" : "doc";
  }
  *pushCount(n4) {
    if (n4 > 0) {
      yield this.buffer.substr(this.pos, n4);
      this.pos += n4;
      return n4;
    }
    return 0;
  }
  *pushToIndex(i7, allowEmpty) {
    const s5 = this.buffer.slice(this.pos, i7);
    if (s5) {
      yield s5;
      this.pos += s5.length;
      return s5.length;
    } else if (allowEmpty)
      yield "";
    return 0;
  }
  *pushIndicators() {
    let n4 = 0;
    loop:
      while (true) {
        switch (this.charAt(0)) {
          case "!":
            n4 += yield* this.pushTag();
            n4 += yield* this.pushSpaces(true);
            continue loop;
          case "&":
            n4 += yield* this.pushUntil(isNotAnchorChar);
            n4 += yield* this.pushSpaces(true);
            continue loop;
          case "-":
          case "?":
          case ":": {
            const inFlow = this.flowLevel > 0;
            const ch1 = this.charAt(1);
            if (isEmpty(ch1) || inFlow && flowIndicatorChars.has(ch1)) {
              if (!inFlow)
                this.indentNext = this.indentValue + 1;
              else if (this.flowKey)
                this.flowKey = false;
              n4 += yield* this.pushCount(1);
              n4 += yield* this.pushSpaces(true);
              continue loop;
            }
          }
        }
        break loop;
      }
    return n4;
  }
  *pushTag() {
    if (this.charAt(1) === "<") {
      let i7 = this.pos + 2;
      let ch = this.buffer[i7];
      while (!isEmpty(ch) && ch !== ">")
        ch = this.buffer[++i7];
      return yield* this.pushToIndex(ch === ">" ? i7 + 1 : i7, false);
    } else {
      let i7 = this.pos + 1;
      let ch = this.buffer[i7];
      while (ch) {
        if (tagChars.has(ch))
          ch = this.buffer[++i7];
        else if (ch === "%" && hexDigits.has(this.buffer[i7 + 1]) && hexDigits.has(this.buffer[i7 + 2])) {
          ch = this.buffer[i7 += 3];
        } else
          break;
      }
      return yield* this.pushToIndex(i7, false);
    }
  }
  *pushNewline() {
    const ch = this.buffer[this.pos];
    if (ch === `
`)
      return yield* this.pushCount(1);
    else if (ch === "\r" && this.charAt(1) === `
`)
      return yield* this.pushCount(2);
    else
      return 0;
  }
  *pushSpaces(allowTabs) {
    let i7 = this.pos - 1;
    let ch;
    do {
      ch = this.buffer[++i7];
    } while (ch === " " || allowTabs && ch === "\t");
    const n4 = i7 - this.pos;
    if (n4 > 0) {
      yield this.buffer.substr(this.pos, n4);
      this.pos = i7;
    }
    return n4;
  }
  *pushUntil(test) {
    let i7 = this.pos;
    let ch = this.buffer[i7];
    while (!test(ch))
      ch = this.buffer[++i7];
    return yield* this.pushToIndex(i7, false);
  }
}
// node_modules/yaml/browser/dist/parse/line-counter.js
class LineCounter {
  constructor() {
    this.lineStarts = [];
    this.addNewLine = (offset) => this.lineStarts.push(offset);
    this.linePos = (offset) => {
      let low = 0;
      let high = this.lineStarts.length;
      while (low < high) {
        const mid = low + high >> 1;
        if (this.lineStarts[mid] < offset)
          low = mid + 1;
        else
          high = mid;
      }
      if (this.lineStarts[low] === offset)
        return { line: low + 1, col: 1 };
      if (low === 0)
        return { line: 0, col: offset };
      const start = this.lineStarts[low - 1];
      return { line: low, col: offset - start + 1 };
    };
  }
}
// node_modules/yaml/browser/dist/parse/parser.js
function includesToken(list, type) {
  for (let i7 = 0;i7 < list.length; ++i7)
    if (list[i7].type === type)
      return true;
  return false;
}
function findNonEmptyIndex(list) {
  for (let i7 = 0;i7 < list.length; ++i7) {
    switch (list[i7].type) {
      case "space":
      case "comment":
      case "newline":
        break;
      default:
        return i7;
    }
  }
  return -1;
}
function isFlowToken(token) {
  switch (token?.type) {
    case "alias":
    case "scalar":
    case "single-quoted-scalar":
    case "double-quoted-scalar":
    case "flow-collection":
      return true;
    default:
      return false;
  }
}
function getPrevProps(parent) {
  switch (parent.type) {
    case "document":
      return parent.start;
    case "block-map": {
      const it = parent.items[parent.items.length - 1];
      return it.sep ?? it.start;
    }
    case "block-seq":
      return parent.items[parent.items.length - 1].start;
    default:
      return [];
  }
}
function getFirstKeyStartProps(prev) {
  if (prev.length === 0)
    return [];
  let i7 = prev.length;
  loop:
    while (--i7 >= 0) {
      switch (prev[i7].type) {
        case "doc-start":
        case "explicit-key-ind":
        case "map-value-ind":
        case "seq-item-ind":
        case "newline":
          break loop;
      }
    }
  while (prev[++i7]?.type === "space") {}
  return prev.splice(i7, prev.length);
}
function arrayPushArray(target, source) {
  if (source.length < 1e5)
    Array.prototype.push.apply(target, source);
  else
    for (let i7 = 0;i7 < source.length; ++i7)
      target.push(source[i7]);
}
function fixFlowSeqItems(fc) {
  if (fc.start.type === "flow-seq-start") {
    for (const it of fc.items) {
      if (it.sep && !it.value && !includesToken(it.start, "explicit-key-ind") && !includesToken(it.sep, "map-value-ind")) {
        if (it.key)
          it.value = it.key;
        delete it.key;
        if (isFlowToken(it.value)) {
          if (it.value.end)
            arrayPushArray(it.value.end, it.sep);
          else
            it.value.end = it.sep;
        } else
          arrayPushArray(it.start, it.sep);
        delete it.sep;
      }
    }
  }
}

class Parser {
  constructor(onNewLine) {
    this.atNewLine = true;
    this.atScalar = false;
    this.indent = 0;
    this.offset = 0;
    this.onKeyLine = false;
    this.stack = [];
    this.source = "";
    this.type = "";
    this.lexer = new Lexer;
    this.onNewLine = onNewLine;
  }
  *parse(source, incomplete = false) {
    if (this.onNewLine && this.offset === 0)
      this.onNewLine(0);
    for (const lexeme of this.lexer.lex(source, incomplete))
      yield* this.next(lexeme);
    if (!incomplete)
      yield* this.end();
  }
  *next(source) {
    this.source = source;
    if (this.atScalar) {
      this.atScalar = false;
      yield* this.step();
      this.offset += source.length;
      return;
    }
    const type = tokenType(source);
    if (!type) {
      const message = `Not a YAML token: ${source}`;
      yield* this.pop({ type: "error", offset: this.offset, message, source });
      this.offset += source.length;
    } else if (type === "scalar") {
      this.atNewLine = false;
      this.atScalar = true;
      this.type = "scalar";
    } else {
      this.type = type;
      yield* this.step();
      switch (type) {
        case "newline":
          this.atNewLine = true;
          this.indent = 0;
          if (this.onNewLine)
            this.onNewLine(this.offset + source.length);
          break;
        case "space":
          if (this.atNewLine && source[0] === " ")
            this.indent += source.length;
          break;
        case "explicit-key-ind":
        case "map-value-ind":
        case "seq-item-ind":
          if (this.atNewLine)
            this.indent += source.length;
          break;
        case "doc-mode":
        case "flow-error-end":
          return;
        default:
          this.atNewLine = false;
      }
      this.offset += source.length;
    }
  }
  *end() {
    while (this.stack.length > 0)
      yield* this.pop();
  }
  get sourceToken() {
    const st = {
      type: this.type,
      offset: this.offset,
      indent: this.indent,
      source: this.source
    };
    return st;
  }
  *step() {
    const top = this.peek(1);
    if (this.type === "doc-end" && top?.type !== "doc-end") {
      while (this.stack.length > 0)
        yield* this.pop();
      this.stack.push({
        type: "doc-end",
        offset: this.offset,
        source: this.source
      });
      return;
    }
    if (!top)
      return yield* this.stream();
    switch (top.type) {
      case "document":
        return yield* this.document(top);
      case "alias":
      case "scalar":
      case "single-quoted-scalar":
      case "double-quoted-scalar":
        return yield* this.scalar(top);
      case "block-scalar":
        return yield* this.blockScalar(top);
      case "block-map":
        return yield* this.blockMap(top);
      case "block-seq":
        return yield* this.blockSequence(top);
      case "flow-collection":
        return yield* this.flowCollection(top);
      case "doc-end":
        return yield* this.documentEnd(top);
    }
    yield* this.pop();
  }
  peek(n4) {
    return this.stack[this.stack.length - n4];
  }
  *pop(error) {
    const token = error ?? this.stack.pop();
    if (!token) {
      const message = "Tried to pop an empty stack";
      yield { type: "error", offset: this.offset, source: "", message };
    } else if (this.stack.length === 0) {
      yield token;
    } else {
      const top = this.peek(1);
      if (token.type === "block-scalar") {
        token.indent = "indent" in top ? top.indent : 0;
      } else if (token.type === "flow-collection" && top.type === "document") {
        token.indent = 0;
      }
      if (token.type === "flow-collection")
        fixFlowSeqItems(token);
      switch (top.type) {
        case "document":
          top.value = token;
          break;
        case "block-scalar":
          top.props.push(token);
          break;
        case "block-map": {
          const it = top.items[top.items.length - 1];
          if (it.value) {
            top.items.push({ start: [], key: token, sep: [] });
            this.onKeyLine = true;
            return;
          } else if (it.sep) {
            it.value = token;
          } else {
            Object.assign(it, { key: token, sep: [] });
            this.onKeyLine = !it.explicitKey;
            return;
          }
          break;
        }
        case "block-seq": {
          const it = top.items[top.items.length - 1];
          if (it.value)
            top.items.push({ start: [], value: token });
          else
            it.value = token;
          break;
        }
        case "flow-collection": {
          const it = top.items[top.items.length - 1];
          if (!it || it.value)
            top.items.push({ start: [], key: token, sep: [] });
          else if (it.sep)
            it.value = token;
          else
            Object.assign(it, { key: token, sep: [] });
          return;
        }
        default:
          yield* this.pop();
          yield* this.pop(token);
      }
      if ((top.type === "document" || top.type === "block-map" || top.type === "block-seq") && (token.type === "block-map" || token.type === "block-seq")) {
        const last = token.items[token.items.length - 1];
        if (last && !last.sep && !last.value && last.start.length > 0 && findNonEmptyIndex(last.start) === -1 && (token.indent === 0 || last.start.every((st) => st.type !== "comment" || st.indent < token.indent))) {
          if (top.type === "document")
            top.end = last.start;
          else
            top.items.push({ start: last.start });
          token.items.splice(-1, 1);
        }
      }
    }
  }
  *stream() {
    switch (this.type) {
      case "directive-line":
        yield { type: "directive", offset: this.offset, source: this.source };
        return;
      case "byte-order-mark":
      case "space":
      case "comment":
      case "newline":
        yield this.sourceToken;
        return;
      case "doc-mode":
      case "doc-start": {
        const doc = {
          type: "document",
          offset: this.offset,
          start: []
        };
        if (this.type === "doc-start")
          doc.start.push(this.sourceToken);
        this.stack.push(doc);
        return;
      }
    }
    yield {
      type: "error",
      offset: this.offset,
      message: `Unexpected ${this.type} token in YAML stream`,
      source: this.source
    };
  }
  *document(doc) {
    if (doc.value)
      return yield* this.lineEnd(doc);
    switch (this.type) {
      case "doc-start": {
        if (findNonEmptyIndex(doc.start) !== -1) {
          yield* this.pop();
          yield* this.step();
        } else
          doc.start.push(this.sourceToken);
        return;
      }
      case "anchor":
      case "tag":
      case "space":
      case "comment":
      case "newline":
        doc.start.push(this.sourceToken);
        return;
    }
    const bv = this.startBlockValue(doc);
    if (bv)
      this.stack.push(bv);
    else {
      yield {
        type: "error",
        offset: this.offset,
        message: `Unexpected ${this.type} token in YAML document`,
        source: this.source
      };
    }
  }
  *scalar(scalar) {
    if (this.type === "map-value-ind") {
      const prev = getPrevProps(this.peek(2));
      const start = getFirstKeyStartProps(prev);
      let sep;
      if (scalar.end) {
        sep = scalar.end;
        sep.push(this.sourceToken);
        delete scalar.end;
      } else
        sep = [this.sourceToken];
      const map2 = {
        type: "block-map",
        offset: scalar.offset,
        indent: scalar.indent,
        items: [{ start, key: scalar, sep }]
      };
      this.onKeyLine = true;
      this.stack[this.stack.length - 1] = map2;
    } else
      yield* this.lineEnd(scalar);
  }
  *blockScalar(scalar) {
    switch (this.type) {
      case "space":
      case "comment":
      case "newline":
        scalar.props.push(this.sourceToken);
        return;
      case "scalar":
        scalar.source = this.source;
        this.atNewLine = true;
        this.indent = 0;
        if (this.onNewLine) {
          let nl = this.source.indexOf(`
`) + 1;
          while (nl !== 0) {
            this.onNewLine(this.offset + nl);
            nl = this.source.indexOf(`
`, nl) + 1;
          }
        }
        yield* this.pop();
        break;
      default:
        yield* this.pop();
        yield* this.step();
    }
  }
  *blockMap(map2) {
    const it = map2.items[map2.items.length - 1];
    switch (this.type) {
      case "newline":
        this.onKeyLine = false;
        if (it.value) {
          const end = "end" in it.value ? it.value.end : undefined;
          const last = Array.isArray(end) ? end[end.length - 1] : undefined;
          if (last?.type === "comment")
            end?.push(this.sourceToken);
          else
            map2.items.push({ start: [this.sourceToken] });
        } else if (it.sep) {
          it.sep.push(this.sourceToken);
        } else {
          it.start.push(this.sourceToken);
        }
        return;
      case "space":
      case "comment":
        if (it.value) {
          map2.items.push({ start: [this.sourceToken] });
        } else if (it.sep) {
          it.sep.push(this.sourceToken);
        } else {
          if (this.atIndentedComment(it.start, map2.indent)) {
            const prev = map2.items[map2.items.length - 2];
            const end = prev?.value?.end;
            if (Array.isArray(end)) {
              arrayPushArray(end, it.start);
              end.push(this.sourceToken);
              map2.items.pop();
              return;
            }
          }
          it.start.push(this.sourceToken);
        }
        return;
    }
    if (this.indent >= map2.indent) {
      const atMapIndent = !this.onKeyLine && this.indent === map2.indent;
      const atNextItem = atMapIndent && (it.sep || it.explicitKey) && this.type !== "seq-item-ind";
      let start = [];
      if (atNextItem && it.sep && !it.value) {
        const nl = [];
        for (let i7 = 0;i7 < it.sep.length; ++i7) {
          const st = it.sep[i7];
          switch (st.type) {
            case "newline":
              nl.push(i7);
              break;
            case "space":
              break;
            case "comment":
              if (st.indent > map2.indent)
                nl.length = 0;
              break;
            default:
              nl.length = 0;
          }
        }
        if (nl.length >= 2)
          start = it.sep.splice(nl[1]);
      }
      switch (this.type) {
        case "anchor":
        case "tag":
          if (atNextItem || it.value) {
            start.push(this.sourceToken);
            map2.items.push({ start });
            this.onKeyLine = true;
          } else if (it.sep) {
            it.sep.push(this.sourceToken);
          } else {
            it.start.push(this.sourceToken);
          }
          return;
        case "explicit-key-ind":
          if (!it.sep && !it.explicitKey) {
            it.start.push(this.sourceToken);
            it.explicitKey = true;
          } else if (atNextItem || it.value) {
            start.push(this.sourceToken);
            map2.items.push({ start, explicitKey: true });
          } else {
            this.stack.push({
              type: "block-map",
              offset: this.offset,
              indent: this.indent,
              items: [{ start: [this.sourceToken], explicitKey: true }]
            });
          }
          this.onKeyLine = true;
          return;
        case "map-value-ind":
          if (it.explicitKey) {
            if (!it.sep) {
              if (includesToken(it.start, "newline")) {
                Object.assign(it, { key: null, sep: [this.sourceToken] });
              } else {
                const start2 = getFirstKeyStartProps(it.start);
                this.stack.push({
                  type: "block-map",
                  offset: this.offset,
                  indent: this.indent,
                  items: [{ start: start2, key: null, sep: [this.sourceToken] }]
                });
              }
            } else if (it.value) {
              map2.items.push({ start: [], key: null, sep: [this.sourceToken] });
            } else if (includesToken(it.sep, "map-value-ind")) {
              this.stack.push({
                type: "block-map",
                offset: this.offset,
                indent: this.indent,
                items: [{ start, key: null, sep: [this.sourceToken] }]
              });
            } else if (isFlowToken(it.key) && !includesToken(it.sep, "newline")) {
              const start2 = getFirstKeyStartProps(it.start);
              const key = it.key;
              const sep = it.sep;
              sep.push(this.sourceToken);
              delete it.key;
              delete it.sep;
              this.stack.push({
                type: "block-map",
                offset: this.offset,
                indent: this.indent,
                items: [{ start: start2, key, sep }]
              });
            } else if (start.length > 0) {
              it.sep = it.sep.concat(start, this.sourceToken);
            } else {
              it.sep.push(this.sourceToken);
            }
          } else {
            if (!it.sep) {
              Object.assign(it, { key: null, sep: [this.sourceToken] });
            } else if (it.value || atNextItem) {
              map2.items.push({ start, key: null, sep: [this.sourceToken] });
            } else if (includesToken(it.sep, "map-value-ind")) {
              this.stack.push({
                type: "block-map",
                offset: this.offset,
                indent: this.indent,
                items: [{ start: [], key: null, sep: [this.sourceToken] }]
              });
            } else {
              it.sep.push(this.sourceToken);
            }
          }
          this.onKeyLine = true;
          return;
        case "alias":
        case "scalar":
        case "single-quoted-scalar":
        case "double-quoted-scalar": {
          const fs = this.flowScalar(this.type);
          if (atNextItem || it.value) {
            map2.items.push({ start, key: fs, sep: [] });
            this.onKeyLine = true;
          } else if (it.sep) {
            this.stack.push(fs);
          } else {
            Object.assign(it, { key: fs, sep: [] });
            this.onKeyLine = true;
          }
          return;
        }
        default: {
          const bv = this.startBlockValue(map2);
          if (bv) {
            if (bv.type === "block-seq") {
              if (!it.explicitKey && it.sep && !includesToken(it.sep, "newline")) {
                yield* this.pop({
                  type: "error",
                  offset: this.offset,
                  message: "Unexpected block-seq-ind on same line with key",
                  source: this.source
                });
                return;
              }
            } else if (atMapIndent) {
              map2.items.push({ start });
            }
            this.stack.push(bv);
            return;
          }
        }
      }
    }
    yield* this.pop();
    yield* this.step();
  }
  *blockSequence(seq2) {
    const it = seq2.items[seq2.items.length - 1];
    switch (this.type) {
      case "newline":
        if (it.value) {
          const end = "end" in it.value ? it.value.end : undefined;
          const last = Array.isArray(end) ? end[end.length - 1] : undefined;
          if (last?.type === "comment")
            end?.push(this.sourceToken);
          else
            seq2.items.push({ start: [this.sourceToken] });
        } else
          it.start.push(this.sourceToken);
        return;
      case "space":
      case "comment":
        if (it.value)
          seq2.items.push({ start: [this.sourceToken] });
        else {
          if (this.atIndentedComment(it.start, seq2.indent)) {
            const prev = seq2.items[seq2.items.length - 2];
            const end = prev?.value?.end;
            if (Array.isArray(end)) {
              arrayPushArray(end, it.start);
              end.push(this.sourceToken);
              seq2.items.pop();
              return;
            }
          }
          it.start.push(this.sourceToken);
        }
        return;
      case "anchor":
      case "tag":
        if (it.value || this.indent <= seq2.indent)
          break;
        it.start.push(this.sourceToken);
        return;
      case "seq-item-ind":
        if (this.indent !== seq2.indent)
          break;
        if (it.value || includesToken(it.start, "seq-item-ind"))
          seq2.items.push({ start: [this.sourceToken] });
        else
          it.start.push(this.sourceToken);
        return;
    }
    if (this.indent > seq2.indent) {
      const bv = this.startBlockValue(seq2);
      if (bv) {
        this.stack.push(bv);
        return;
      }
    }
    yield* this.pop();
    yield* this.step();
  }
  *flowCollection(fc) {
    const it = fc.items[fc.items.length - 1];
    if (this.type === "flow-error-end") {
      let top;
      do {
        yield* this.pop();
        top = this.peek(1);
      } while (top?.type === "flow-collection");
    } else if (fc.end.length === 0) {
      switch (this.type) {
        case "comma":
        case "explicit-key-ind":
          if (!it || it.sep)
            fc.items.push({ start: [this.sourceToken] });
          else
            it.start.push(this.sourceToken);
          return;
        case "map-value-ind":
          if (!it || it.value)
            fc.items.push({ start: [], key: null, sep: [this.sourceToken] });
          else if (it.sep)
            it.sep.push(this.sourceToken);
          else
            Object.assign(it, { key: null, sep: [this.sourceToken] });
          return;
        case "space":
        case "comment":
        case "newline":
        case "anchor":
        case "tag":
          if (!it || it.value)
            fc.items.push({ start: [this.sourceToken] });
          else if (it.sep)
            it.sep.push(this.sourceToken);
          else
            it.start.push(this.sourceToken);
          return;
        case "alias":
        case "scalar":
        case "single-quoted-scalar":
        case "double-quoted-scalar": {
          const fs = this.flowScalar(this.type);
          if (!it || it.value)
            fc.items.push({ start: [], key: fs, sep: [] });
          else if (it.sep)
            this.stack.push(fs);
          else
            Object.assign(it, { key: fs, sep: [] });
          return;
        }
        case "flow-map-end":
        case "flow-seq-end":
          fc.end.push(this.sourceToken);
          return;
      }
      const bv = this.startBlockValue(fc);
      if (bv)
        this.stack.push(bv);
      else {
        yield* this.pop();
        yield* this.step();
      }
    } else {
      const parent = this.peek(2);
      if (parent.type === "block-map" && (this.type === "map-value-ind" && parent.indent === fc.indent || this.type === "newline" && !parent.items[parent.items.length - 1].sep)) {
        yield* this.pop();
        yield* this.step();
      } else if (this.type === "map-value-ind" && parent.type !== "flow-collection") {
        const prev = getPrevProps(parent);
        const start = getFirstKeyStartProps(prev);
        fixFlowSeqItems(fc);
        const sep = fc.end.splice(1, fc.end.length);
        sep.push(this.sourceToken);
        const map2 = {
          type: "block-map",
          offset: fc.offset,
          indent: fc.indent,
          items: [{ start, key: fc, sep }]
        };
        this.onKeyLine = true;
        this.stack[this.stack.length - 1] = map2;
      } else {
        yield* this.lineEnd(fc);
      }
    }
  }
  flowScalar(type) {
    if (this.onNewLine) {
      let nl = this.source.indexOf(`
`) + 1;
      while (nl !== 0) {
        this.onNewLine(this.offset + nl);
        nl = this.source.indexOf(`
`, nl) + 1;
      }
    }
    return {
      type,
      offset: this.offset,
      indent: this.indent,
      source: this.source
    };
  }
  startBlockValue(parent) {
    switch (this.type) {
      case "alias":
      case "scalar":
      case "single-quoted-scalar":
      case "double-quoted-scalar":
        return this.flowScalar(this.type);
      case "block-scalar-header":
        return {
          type: "block-scalar",
          offset: this.offset,
          indent: this.indent,
          props: [this.sourceToken],
          source: ""
        };
      case "flow-map-start":
      case "flow-seq-start":
        return {
          type: "flow-collection",
          offset: this.offset,
          indent: this.indent,
          start: this.sourceToken,
          items: [],
          end: []
        };
      case "seq-item-ind":
        return {
          type: "block-seq",
          offset: this.offset,
          indent: this.indent,
          items: [{ start: [this.sourceToken] }]
        };
      case "explicit-key-ind": {
        this.onKeyLine = true;
        const prev = getPrevProps(parent);
        const start = getFirstKeyStartProps(prev);
        start.push(this.sourceToken);
        return {
          type: "block-map",
          offset: this.offset,
          indent: this.indent,
          items: [{ start, explicitKey: true }]
        };
      }
      case "map-value-ind": {
        this.onKeyLine = true;
        const prev = getPrevProps(parent);
        const start = getFirstKeyStartProps(prev);
        return {
          type: "block-map",
          offset: this.offset,
          indent: this.indent,
          items: [{ start, key: null, sep: [this.sourceToken] }]
        };
      }
    }
    return null;
  }
  atIndentedComment(start, indent) {
    if (this.type !== "comment")
      return false;
    if (this.indent <= indent)
      return false;
    return start.every((st) => st.type === "newline" || st.type === "space");
  }
  *documentEnd(docEnd) {
    if (this.type !== "doc-mode") {
      if (docEnd.end)
        docEnd.end.push(this.sourceToken);
      else
        docEnd.end = [this.sourceToken];
      if (this.type === "newline")
        yield* this.pop();
    }
  }
  *lineEnd(token) {
    switch (this.type) {
      case "comma":
      case "doc-start":
      case "doc-end":
      case "flow-seq-end":
      case "flow-map-end":
      case "map-value-ind":
        yield* this.pop();
        yield* this.step();
        break;
      case "newline":
        this.onKeyLine = false;
      case "space":
      case "comment":
      default:
        if (token.end)
          token.end.push(this.sourceToken);
        else
          token.end = [this.sourceToken];
        if (this.type === "newline")
          yield* this.pop();
    }
  }
}
// node_modules/yaml/browser/dist/public-api.js
function parseOptions(options) {
  const prettyErrors = options.prettyErrors !== false;
  const lineCounter = options.lineCounter || prettyErrors && new LineCounter || null;
  return { lineCounter, prettyErrors };
}
function parseDocument(source, options = {}) {
  const { lineCounter, prettyErrors } = parseOptions(options);
  const parser = new Parser(lineCounter?.addNewLine);
  const composer = new Composer(options);
  let doc = null;
  for (const _doc of composer.compose(parser.parse(source), true, source.length)) {
    if (!doc)
      doc = _doc;
    else if (doc.options.logLevel !== "silent") {
      doc.errors.push(new YAMLParseError(_doc.range.slice(0, 2), "MULTIPLE_DOCS", "Source contains multiple documents; please use YAML.parseAllDocuments()"));
      break;
    }
  }
  if (prettyErrors && lineCounter) {
    doc.errors.forEach(prettifyError(source, lineCounter));
    doc.warnings.forEach(prettifyError(source, lineCounter));
  }
  return doc;
}
function parse(src, reviver, options) {
  let _reviver = undefined;
  if (typeof reviver === "function") {
    _reviver = reviver;
  } else if (options === undefined && reviver && typeof reviver === "object") {
    options = reviver;
  }
  const doc = parseDocument(src, options);
  if (!doc)
    return null;
  doc.warnings.forEach((warning) => warn(doc.options.logLevel, warning));
  if (doc.errors.length > 0) {
    if (doc.options.logLevel !== "silent")
      throw doc.errors[0];
    else
      doc.errors = [];
  }
  return doc.toJS(Object.assign({ reviver: _reviver }, options));
}
function stringify3(value, replacer, options) {
  let _replacer = null;
  if (typeof replacer === "function" || Array.isArray(replacer)) {
    _replacer = replacer;
  } else if (options === undefined && replacer) {
    options = replacer;
  }
  if (typeof options === "string")
    options = options.length;
  if (typeof options === "number") {
    const indent = Math.round(options);
    options = indent < 1 ? undefined : indent > 8 ? { indent: 8 } : { indent };
  }
  if (value === undefined) {
    const { keepUndefined } = options ?? replacer ?? {};
    if (!keepUndefined)
      return;
  }
  if (isDocument(value) && !_replacer)
    return value.toString(options);
  return new Document2(value, _replacer, options).toString(options);
}
// custom_components/llm_gateway/frontend/voice-harness-portability.ts
var gatewayFields = [
  "routing_mode",
  "models",
  "max_tokens",
  "timeouts",
  "temperature",
  "top_p",
  "diagnostic_traces",
  "trace_include_raw_messages",
  "trace_max_runs",
  "trace_retention_hours"
];
var audioFields = [
  "wake_cue_volume",
  "follow_up_cue_volume",
  "processing_volume",
  "tts_volume_day",
  "tts_volume_night",
  "fallback_volume",
  "audio_muted",
  "night_mode"
];
function tuningSnapshot(options, audio) {
  const gateway = {};
  for (const key of gatewayFields.filter((key2) => !["models", "max_tokens", "timeouts"].includes(key2)))
    if (options[key] !== undefined)
      gateway[key] = options[key];
  for (const [key, suffix] of [
    ["models", "model"],
    ["max_tokens", "max_tokens"],
    ["timeouts", "chat_timeout"]
  ]) {
    const values = Object.fromEntries(["fast", "mid", "deep"].flatMap((tier) => options[tier + "_" + suffix] === undefined ? [] : [[tier, options[tier + "_" + suffix]]]));
    if (Object.keys(values).length)
      gateway[key] = values;
  }
  return {
    gateway,
    audio: Object.fromEntries(audioFields.flatMap((key) => audio[key] === undefined ? [] : [[key, audio[key]]]))
  };
}
function parseTuning(text) {
  const value = parse(text);
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("Configuration must be an object / 配置必须是对象");
  const input = object(value);
  if (Object.keys(input).some((key) => !["gateway", "audio"].includes(key)))
    throw new Error("Import only gateway and audio tuning / 仅支持导入网关与音频调音参数");
  const result = {};
  for (const section of ["gateway", "audio"]) {
    if (input[section] === undefined)
      continue;
    if (!input[section] || typeof input[section] !== "object" || Array.isArray(input[section]))
      throw new Error(section + " must be an object");
    const values = object(input[section]);
    const allowed = section === "gateway" ? gatewayFields : audioFields;
    if (Object.keys(values).some((key) => !allowed.includes(key)))
      throw new Error("Unsupported tuning field / 不支持的调音字段");
    if (section === "audio") {
      for (const [key, value2] of Object.entries(values)) {
        if (["audio_muted", "night_mode"].includes(key) ? typeof value2 !== "boolean" : typeof value2 !== "number" || !Number.isFinite(value2) || value2 < 0 || value2 > 1)
          throw new Error("Invalid audio value: " + key);
      }
      result.audio = { ...values };
    } else {
      result.gateway = JSON.parse(JSON.stringify(values));
    }
  }
  if (!Object.values(result).some((section) => section && Object.keys(section).length))
    throw new Error("No tuning values found / 未找到调音参数");
  return result;
}
function serializeTuning(config, format) {
  return format === "json" ? JSON.stringify(config, null, 2) + `
` : stringify3(config);
}

// custom_components/llm_gateway/frontend/voice-harness-settings.ts
class VoiceHarnessSettings extends i4 {
  static properties = {
    hass: { attribute: false },
    language: {},
    section: { reflect: true },
    entries: { attribute: false },
    configuration: { attribute: false },
    applyTuning: { attribute: false },
    pending: { state: true },
    message: { state: true },
    error: { state: true },
    busy: { state: true },
    entryId: { state: true },
    probeResult: { state: true },
    probing: { state: true }
  };
  constructor() {
    super();
    this.language = "en";
    this.section = "audio";
    this.entries = [];
    this.configuration = {};
    this.pending = null;
    this.message = "";
    this.error = "";
    this.busy = false;
    this.entryId = "";
    this.probeResult = {};
    this.probing = "";
  }
  t(en, zh) {
    return this.language.startsWith("zh") ? zh : en;
  }
  render() {
    const t5 = this.t.bind(this);
    const groups2 = [
      {
        id: "audio",
        icon: "mdi:tune-variant",
        title: t5("Acoustic tuning", "声学调音"),
        hint: t5("Scenes, cues & speech", "场景、提示音与播报")
      },
      {
        id: "routing",
        icon: "mdi:source-branch",
        title: t5("Models & routing", "大模型路由策略"),
        hint: t5("Providers, models & API", "服务商、模型与 API")
      },
      {
        id: "pipeline",
        icon: "mdi:waveform",
        title: t5("ASR / TTS & Wyoming", "ASR / TTS 与 Wyoming"),
        hint: t5("From capture to playback", "从收音到播放")
      },
      {
        id: "system",
        icon: "mdi:database-outline",
        title: t5("System & storage", "系统与存储策略"),
        hint: t5("Retention & configuration", "保留周期与配置迁移")
      }
    ];
    return b2`
      <div class="section-head">
        <div>
          <span class="eyebrow">VOICE HARNESS / ${t5("SETTINGS", "设置")}</span>
          <h2>${t5("Make it feel like home.", "让声音，更懂你的生活。")}</h2>
          <p class="muted">
            ${t5("Thoughtful defaults. A little room to make them yours.", "从恰好的默认值出发，把细节调到适合自己。")}
          </p>
        </div>
      </div>
      <div class="layout">
        <nav class="groups" aria-label=${t5("Settings groups", "设置分组")}>
          ${groups2.map((group) => b2`<button
            aria-current=${this.section === group.id ? "page" : "false"}
            @click=${() => {
      this.section = group.id;
    }}
          >
            <ha-icon icon=${group.icon}></ha-icon
            ><span
              ><strong>${group.title}</strong><small>${group.hint}</small></span
            ><span class="arrow">›</span>
          </button>`)}
        </nav>
        <div class="content">
          <div ?hidden=${this.section !== "audio"}>
            <slot name="audio"></slot>
          </div>
          <div ?hidden=${this.section === "audio"}>
            <slot name="configuration"></slot>
          </div>
          <section
            class="surface probes"
            ?hidden=${this.section !== "pipeline"}
          >
            <div class="section-head">
              <div>
                <span class="eyebrow">LIVE CHECK</span>
                <h3>${t5("Listen to the connection", "看见链路是否畅通")}</h3>
                <p class="muted">
                  ${t5("Probe from Home Assistant and measure the response.", "通过 Home Assistant 发起探测，记录本次响应。")}
                </p>
              </div>
            </div>
            <div class="probe-grid">
              ${[
      ["wyoming", "Wyoming"],
      ["tts", "Edge TTS"],
      ["satellite", "Kukui"]
    ].map(([key, label]) => b2`<article>
                <strong>${label}</strong>
                <p class="muted" role="status">
                  ${this.probeResult[key] || t5("Not measured", "尚未测量")}
                </p>
                <button
                  ?disabled=${Boolean(this.probing)}
                  @click=${() => this.probe(key)}
                >
                  ${this.probing === key ? t5("Measuring…", "测量中…") : t5("Probe now", "立即探测")}
                </button>
              </article>`)}
            </div>
          </section>
          <div ?hidden=${this.section !== "pipeline"}>
            <slot name="pipeline"></slot>
          </div>
          <section
            class="surface portability"
            ?hidden=${this.section !== "system"}
          >
            <div class="section-head">
              <div>
                <span class="eyebrow">TAKE YOUR SETTINGS WITH YOU</span>
                <h3>
                  ${t5("Your tuning, wherever you need it", "把合适的调音，带到下一处")}
                </h3>
                <p class="muted">
                  ${t5("JSON or YAML. Saved tuning values only; API keys stay in Home Assistant.", "支持 JSON 与 YAML。导出已保存的调音参数，API 密钥留在 Home Assistant。")}
                </p>
              </div>
            </div>
            ${this.entries.length > 1 ? b2`<label
                    >${t5("Gateway", "网关")}<select
                      .value=${this.selectedEntry()}
                      @change=${(event) => {
      this.entryId = event.target.value;
      this.pending = null;
    }}
                    >
                      ${this.entries.map((entry) => b2`<option value=${String(entry.entry_id)}>${String(entry.title)}</option>`)}
                    </select></label
                  >` : A}
            <div class="portability-actions">
              <button
                ?disabled=${this.busy || !this.entries.length}
                @click=${() => this.export("json")}
              >
                ↓ ${t5("Export JSON", "导出 JSON")}</button
              ><button
                ?disabled=${this.busy || !this.entries.length}
                @click=${() => this.export("yaml")}
              >
                ↓ ${t5("Export YAML", "导出 YAML")}</button
              ><label class="import-button"
                ><span>↑ ${t5("Import tuning", "导入调音配置")}</span
                ><input
                  type="file"
                  accept=".json,.yaml,.yml,application/json,application/yaml"
                  ?disabled=${this.busy}
                  @change=${(event) => this.import(event.target.files?.[0])}
              /></label>
            </div>
            ${this.pending ? b2`<div class="import-preview">
                    <h3>${t5("Review imported values", "检查待导入参数")}</h3>
                    <pre>${JSON.stringify(this.pending, null, 2)}</pre>
                    <button
                      class="primary"
                      ?disabled=${this.busy}
                      @click=${() => this.apply()}
                    >
                      ${this.busy ? t5("Applying…", "应用中…") : t5("Apply these values", "应用这些参数")}</button
                    ><button
                      class="quiet"
                      ?disabled=${this.busy}
                      @click=${() => {
      this.pending = null;
    }}
                    >
                      ${t5("Cancel", "取消")}
                    </button>
                  </div>` : A}
            ${this.error ? b2`<p class="error" role="alert">${this.error}</p>` : A}${this.message ? b2`<p class="message" role="status">${this.message}</p>` : A}
          </section>
        </div>
      </div>
    `;
  }
  selectedEntry() {
    return this.entryId || String(this.entries[0]?.entry_id || "");
  }
  async export(format) {
    this.busy = true;
    this.error = "";
    this.message = "";
    try {
      const config = records(this.configuration.entries).find((entry) => entry.entry_id === this.selectedEntry());
      if (!config)
        throw new Error(this.t("Load the gateway settings before exporting.", "请先加载网关设置再导出。"));
      let audio = {};
      try {
        audio = (await voiceSettingsRequest(this.hass || {}, "read")).config || {};
      } catch {
        this.message = this.t("Satellite unavailable; exported gateway tuning only.", "卫星暂不可达，本次仅导出网关调音参数。");
      }
      const data = tuningSnapshot(object(config.options), audio);
      const url = URL.createObjectURL(new Blob([serializeTuning(data, format)], {
        type: format === "json" ? "application/json" : "application/yaml"
      }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "voice-harness-tuning." + format;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      this.message ||= this.t("Saved tuning exported.", "已导出保存的调音配置。");
    } catch (error) {
      this.error = error instanceof Error ? error.message : String(error);
    } finally {
      this.busy = false;
    }
  }
  async import(file) {
    if (!file)
      return;
    this.error = "";
    this.message = "";
    this.pending = null;
    try {
      this.pending = parseTuning(await file.text());
    } catch (error) {
      this.error = error instanceof Error ? error.message : String(error);
    }
  }
  async apply() {
    if (!this.pending || !this.applyTuning)
      return;
    this.busy = true;
    this.error = "";
    this.message = "";
    try {
      this.message = await this.applyTuning(this.selectedEntry(), this.pending);
      this.pending = null;
    } catch (error) {
      this.error = error instanceof Error ? error.message : String(error);
    } finally {
      this.busy = false;
    }
  }
  async probe(kind) {
    this.probing = kind;
    const started = performance.now();
    try {
      let detail = "";
      if (kind === "satellite") {
        await voiceSettingsRequest(this.hass || {}, "read");
        detail = this.t("Agent replied", "代理已响应");
      } else if (kind === "wyoming") {
        const result = await requestHarnessJson(this.hass, "POST", "llm_gateway/harness/probe-wyoming", {});
        if (!result.results.length)
          throw new Error(this.t("No Wyoming integration configured", "尚未配置 Wyoming 集成"));
        detail = result.results.map((probe) => probe.name + ": " + (probe.connected ? this.t("TCP reachable", "TCP 可达") + " · " + probe.latency_ms + " ms" : probe.error)).join(" · ");
        this.probeResult = { ...this.probeResult, [kind]: detail };
        return;
      } else {
        const candidates = this.entries.flatMap((entry) => records(object(object(entry.first_response_audio).candidates).tts));
        const entity = candidates.find((candidate) => candidate.usable)?.entity_id;
        if (!entity)
          throw new Error(this.t("No available TTS engine", "暂无可用 TTS 引擎"));
        const result = await requestHarnessJson(this.hass, "POST", "tts_get_url", {
          engine_id: entity,
          message: this.t("The voice connection is ready.", "语音链路已准备好。"),
          cache: false
        });
        if (!result.path?.startsWith("/api/tts_proxy/"))
          throw new Error("TTS did not return a local audio path");
        const response = await fetch(result.path);
        if (!response.ok)
          throw new Error("TTS synthesis returned HTTP " + response.status);
        const bytes = (await response.arrayBuffer()).byteLength;
        if (!bytes)
          throw new Error("TTS returned no audio");
        detail = this.t("Audio synthesized, not played", "已生成音频，未播放") + " · " + Math.round(bytes / 1024) + " KB";
      }
      this.probeResult = {
        ...this.probeResult,
        [kind]: detail + " · " + Math.round(performance.now() - started) + " ms " + this.t("round trip", "往返")
      };
    } catch (error) {
      this.probeResult = {
        ...this.probeResult,
        [kind]: this.t("Probe failed: ", "探测失败：") + (error instanceof Error ? error.message : String(error))
      };
    } finally {
      this.probing = "";
    }
  }
  static styles = [
    harnessFoundationStyles,
    harnessButtonStyles,
    harnessSurfaceStyles,
    i`
      :host {
        display: block;
      }
      .layout {
        display: grid;
        grid-template-columns: 242px minmax(0, 1fr);
        align-items: start;
        gap: 26px;
      }
      .groups {
        display: grid;
        gap: 8px;
        position: sticky;
        top: 20px;
      }
      .groups button {
        justify-content: flex-start;
        gap: 12px;
        border: 0;
        background: transparent;
        text-align: left;
        padding: 16px 14px;
        border-radius: 16px;
        color: var(--vh-muted);
      }
      .groups [aria-current="page"] {
        color: var(--vh-accent);
        background: var(--vh-soft);
      }
      .groups button > span:not(.arrow) {
        display: grid;
        gap: 4px;
        flex: 1;
      }
      .groups strong {
        font-size: 13px;
        font-weight: 580;
      }
      .groups small {
        font-size: 11px;
        font-weight: 400;
        color: var(--vh-muted);
      }
      .arrow {
        font-size: 20px;
        opacity: 0.6;
      }
      .content {
        display: grid;
        gap: 20px;
        min-width: 0;
      }
      .portability {
        display: grid;
        gap: 18px;
      }
      .portability-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }
      .import-button {
        position: relative;
        min-height: 44px;
        padding: 10px 16px;
        border: 1px solid var(--vh-line);
        border-radius: 12px;
        font-weight: 550;
        font-size: 14px;
        cursor: pointer;
        overflow: hidden;
      }
      .import-button input {
        position: absolute;
        inset: 0;
        opacity: 0;
        cursor: pointer;
        width: 100%;
      }
      .import-button:focus-within {
        outline: 3px solid var(--vh-accent);
        outline-offset: 3px;
      }
      .import-preview {
        padding: 18px;
        background: var(--vh-background);
        border-radius: 16px;
      }
      pre {
        max-height: 320px;
        overflow: auto;
        margin: 14px 0;
      }
      .message {
        font-size: 13px;
        color: var(--success-color);
      }
      .probe-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 16px;
      }
      .probe-grid article {
        display: grid;
        gap: 14px;
        align-content: start;
        min-width: 0;
      }
      .probe-grid p {
        font-size: 12px;
        overflow-wrap: anywhere;
      }
      .probe-grid button {
        margin-top: auto;
      }
      @media (max-width: 1100px) {
        .layout {
          grid-template-columns: 210px minmax(0, 1fr);
          gap: 18px;
        }
        .probe-grid {
          grid-template-columns: 1fr;
        }
      }
      @media (max-width: 850px) {
        .layout {
          grid-template-columns: 1fr;
        }
        .groups {
          grid-template-columns: 1fr 1fr;
          position: static;
          gap: 8px;
        }
        .groups button {
          background: var(--vh-surface);
          padding: 14px;
        }
        .arrow {
          display: none;
        }
      }
      @media (max-width: 600px) {
        .groups button {
          gap: 8px;
          padding: 12px;
        }
        .groups strong {
          font-size: 12px;
        }
        .groups small {
          font-size: 10px;
        }
        .groups ha-icon {
          width: 18px;
          height: 18px;
          --mdc-icon-size: 18px;
        }
        .portability-actions > * {
          flex: 1;
          white-space: nowrap;
        }
      }
    `
  ];
}
if (!customElements.get("voice-harness-settings"))
  customElements.define("voice-harness-settings", VoiceHarnessSettings);

// custom_components/llm_gateway/frontend/voice-harness-shell.ts
function renderHarnessShell(root, model, legacyStyles) {
  const zh = model.language.startsWith("zh");
  D(b2`
      <style>
        ${harnessFoundationStyles.cssText}${legacyStyles}${harnessButtonStyles.cssText}${shellStyles}
      </style>
      <main class="shell">
        <header class="topbar">
          <div class="brand">
            <span class="brand-icon" aria-hidden="true"
              ><i></i><i></i><i></i><i></i><i></i
            ></span>
            <div>
              <h1>Voice Harness</h1>
              <span class="subline"
                >${zh ? "让交互，回归自然。" : "A more natural connection."}</span
              >
            </div>
          </div>
          <voice-harness-navigation
            .active=${model.active}
            .items=${model.navigation}
            @harness-view-select=${(event) => model.select(event.detail.id)}
          ></voice-harness-navigation>
          <div class="refresh">
            <span class="subline" title=${model.statusLine}
              >${model.busy ? zh ? "同步中…" : "Syncing…" : model.updatedAt ? new Date(model.updatedAt).toLocaleTimeString(model.language, { hour: "2-digit", minute: "2-digit" }) : "—"}</span
            ><button
              class="quiet"
              ?disabled=${model.busy}
              aria-label=${zh ? "刷新观测" : "Refresh observations"}
              @click=${model.refresh}
            >
              <ha-icon icon="mdi:refresh"></ha-icon>
            </button>
          </div>
        </header>
        ${model.error ? b2`<div class="banner error" role="alert">${model.error}</div>` : A}
        <div
          class="content"
          role="region"
          aria-label=${model.navigation.find((view) => view.id === model.active)?.label || model.active}
        >
          ${!model.loaded ? b2`<div class="loading" role="status">${zh ? "正在连接你的语音空间…" : "Connecting to your voice space…"}</div>` : A}
          ${model.visited.has("overview") && model.loaded ? b2` <voice-harness-overview
                ?hidden=${model.active !== "overview"}
                .entries=${model.entries}
                .satellite=${model.satellite}
                .language=${model.language}
                @harness-overview-navigate=${(event) => model.select(event.detail.destination)}
              >
                <div slot="diagnostics">${o5(model.diagnostics)}</div>
                <div slot="memory">${o5(model.memory)}</div>
              </voice-harness-overview>` : A}
          ${model.visited.has("runs") && model.loaded ? b2`<voice-harness-runs ?hidden=${model.active !== "runs"} .entries=${model.entries} .language=${model.language} .loadDetail=${model.loadDetail} .replay=${model.replay}></voice-harness-runs>` : A}
          ${model.visited.has("test") && model.loaded ? b2`<voice-harness-playground ?hidden=${model.active !== "test"} .hass=${model.hass} .entries=${model.entries} .language=${model.language} .scenarios=${model.scenarios}><div slot="policies">${o5(model.policies)}</div></voice-harness-playground>` : A}
          ${model.visited.has("settings") && model.loaded ? b2`<voice-harness-settings
                ?hidden=${model.active !== "settings"}
                .hass=${model.hass}
                .entries=${model.entries}
                .language=${model.language}
                .configuration=${model.configuration}
                .applyTuning=${model.applyTuning}
              >
                <div slot="audio">
                  <voice-harness-audio-settings
                    .hass=${model.hass}
                    .language=${model.language}
                    .active=${model.active === "settings"}
                  ></voice-harness-audio-settings>
                  <details class="surface sound-library">
                    <summary>${zh ? "提示音素材库" : "Sound library"}</summary>
                    ${o5(model.earcons)}
                  </details>
                </div>
                <div slot="configuration">${o5(model.config)}</div>
                <div slot="pipeline">${o5(model.pipeline)}</div>
              </voice-harness-settings>` : A}
        </div>
        <footer class="shell-footer">
          <span>Voice Harness</span
          ><span
            >${zh ? "观测 · 理解 · 回应" : "Observe · Understand · Respond"}</span
          ><span>${zh ? "键盘快捷键 1–4" : "Keyboard shortcuts 1–4"}</span>
        </footer>
      </main>
    `, root);
}
var shellStyles = `
  :host { display:block; height:100%; overflow:auto; color-scheme:light dark; background:var(--vh-background); }
  .shell { max-width:1500px; margin:0 auto; padding:28px 42px 16px; box-sizing:border-box; font-family:inherit; min-height:100%; }
  .topbar { display:grid; grid-template-columns:1fr minmax(350px,480px) 1fr; align-items:center; gap:24px; margin:0 0 44px; padding:0 0 24px; border-bottom:1px solid var(--vh-line); }
  .brand {display:flex; align-items:center; gap:14px; min-width:0;}
  .brand-icon {display:flex; justify-content:center; align-items:center; gap:3px; width:44px; height:44px; border-radius:14px; background:var(--vh-accent); color:var(--text-primary-color,white); flex-shrink:0;}
  .brand-icon i {width:3px; height:12px; border-radius:3px; background:currentColor;}
  .brand-icon i:nth-child(2), .brand-icon i:nth-child(4) {height:20px;} .brand-icon i:nth-child(3) {height:28px;}
  .topbar h1 {font-size:20px; font-weight:630; letter-spacing:-.035em; line-height:1.3; margin:0; white-space:nowrap;}
  .subline {font-size:11px; color:var(--vh-muted); margin-top:5px; display:block;}
  .refresh {display:flex; gap:10px; justify-content:flex-end; align-items:center;}
  .refresh .subline {margin:0; font-variant-numeric:tabular-nums;}
  .content {view-transition-name:harness-content; min-width:0;}
  .loading {min-height:400px; display:grid; place-items:center; color:var(--vh-muted);}
  .shell-footer {display:flex; gap:24px; justify-content:space-between; margin-top:38px; padding:18px 0; color:var(--vh-muted); font-size:10px; letter-spacing:.06em; border-top:1px solid var(--vh-line);}
  .shell-footer > span:first-child {font-weight:650;}
  .surface {background:var(--vh-surface); border:1px solid var(--vh-line); border-radius:20px; box-shadow:none; padding:24px;}
  h2 {font-size:18px; letter-spacing:-.02em;} h3 {font-size:15px;}
  .meta, .settingsNote, .settingsDescription {font-size:12px; line-height:1.7; color:var(--vh-muted);}
  .sectionHead {margin-bottom:20px; gap:14px;}
  .settingsForm .sectionHead h2 {font-size:18px;}
  .settingsGrid {display:grid; grid-template-columns:1fr; gap:18px;}
  .settingsForm {padding:24px; min-width:0;}
  .settingsForm .configCard {border:1px solid var(--vh-line); border-radius:16px; margin-top:16px; overflow:visible;}
  .configCard > summary {min-height:56px; font-size:14px; padding:16px 20px;}
  .configCard fieldset {padding:18px 20px; border-color:var(--vh-line); margin:0; display:grid; gap:16px;}
  .configCard fieldset:last-child {border-bottom:0;}
  .configCard legend {font-size:12px; color:var(--vh-muted);}
  .settingsForm label {font-size:13px; line-height:1.6; gap:8px;}
  .settingsForm input:not([type=checkbox]), .settingsForm textarea, .settingsForm select {border-radius:10px; border:1px solid var(--vh-line); padding:12px; background:var(--vh-background);}
  .checkRow {min-height:44px; align-items:center;}
  .settingsTriples {gap:16px;}
  .modelPicker .pickerToggle {min-height:48px; border-radius:10px; border-color:var(--vh-line); background:var(--vh-background);}
  .pickerRow, .pickerPick, .pickerProbe {min-height:44px;}
  .pickerMenu {z-index:10; border-radius:14px;}
  .modelsToolbar {gap:10px;}
  button, select, summary {min-height:44px;}
  .sound-library {margin-top:20px; padding-top:0; padding-bottom:0;}
  .sound-library > summary {padding:18px 0; font-size:14px;}
  .earconGrid {grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px;}
  .earconGrid .surface {padding:18px; margin-bottom:18px;}
  voice-harness-settings[section=audio] [data-settings-section],
  voice-harness-settings[section=routing] [data-settings-section]:not([data-settings-section=routing]),
  voice-harness-settings[section=pipeline] [data-settings-section]:not([data-settings-section=pipeline]),
  voice-harness-settings[section=system] [data-settings-section]:not([data-settings-section=system]) {display:none;}
  .satelliteLayout {display:grid; grid-template-columns:1fr; gap:18px;}
  .satelliteLayout .surface {grid-column:auto;}
  .satelliteSummary {gap:12px;}
  [slot=policies] {padding-bottom:20px;}
  @media (max-width:1150px) {.shell {padding:24px;} .topbar {grid-template-columns:1fr auto; gap:20px; margin-bottom:30px;} .topbar voice-harness-navigation {grid-column:1 / -1; grid-row:2;} .topbar .refresh {grid-column:2; grid-row:1;} }
  @media (max-width:600px) {.shell {padding:18px 16px 12px;} .topbar {margin-bottom:28px; padding-bottom:16px; gap:18px;} .topbar h1 {font-size:18px;} .brand {gap:10px;} .brand-icon {width:40px; height:40px;} .refresh .subline {display:none;} .shell-footer {font-size:9px; gap:12px; flex-wrap:wrap; margin-top:28px;} .shell-footer > span:last-child {display:none;} .surface, .settingsForm {padding:18px;} .configCard > summary {padding:14px;} .configCard fieldset {padding:14px;} .settingsTriples, .settingsTriples.two {grid-template-columns:1fr;} .earconGrid {grid-template-columns:1fr;} .modelsToolbar {flex-wrap:wrap;} .sectionHead {flex-wrap:wrap;} }
  @media (prefers-reduced-motion:reduce) {.content {view-transition-name:none;} }
`;
export {
  voiceSettingsRequest,
  resolveReplayPair,
  renderHarnessShell
};
