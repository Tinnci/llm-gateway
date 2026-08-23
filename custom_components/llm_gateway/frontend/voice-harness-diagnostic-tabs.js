// @ts-check

/**
 * Keyed renderer registry for the Voice Harness diagnostic drawer tabs.
 *
 * This mirrors the Cordis pattern the kernel uses elsewhere: sections are
 * registered into a table instead of being hard-coded into one consumer. The
 * drawer iterates this registry, so a new diagnostic section is one
 * `registerDiagnosticTab()` call plus its render function — no drawer edits,
 * and unknown backend fields already fall through the generic raw-tab panels.
 *
 * Registration validates each entry in full before anything is stored, and a
 * duplicate id throws instead of silently replacing: a broken registration is
 * a loud failure at mount time, never a silent gap at render time.
 *
 * @module voice-harness-diagnostic-tabs
 */

/**
 * Everything a tab renderer may inspect. One shared context object is built
 * per record before rendering starts, so renderers stay pure functions of
 * (panel, record, ctx) and never reach back into drawer internals.
 *
 * @typedef {Object} DiagnosticTabContext
 * @property {Array<Record<string, any>>} timeline Timeline spans for this record.
 * @property {Array<Record<string, any>>} tools Tool event summaries.
 * @property {Array<Record<string, any>>} errors Error summaries.
 * @property {Array<Record<string, any>>} attempts Provider attempt summaries.
 * @property {Record<string, any>} firstResponse First-response decision summary.
 * @property {Record<string, any>} route Route kind/model summary.
 * @property {Record<string, any>} provider Provider status summary.
 * @property {Record<string, any>} rawMeta Raw payload storage metadata.
 * @property {Record<string, any>} causalChain Endpoint-to-stop chain summary.
 */

/**
 * @typedef {Object} DiagnosticTabEntry
 * @property {string} id Stable tab id; doubles as the persisted per-record selection key.
 * @property {string} labelKey I18N key resolved for the tab label.
 * @property {number} order Ascending sort position; ties keep registration order.
 * @property {(panel: any, record: Record<string, any>, ctx: DiagnosticTabContext) => string} render
 *   Returns the tab body HTML; returning only whitespace hides the tab.
 */

/** @type {Array<DiagnosticTabEntry>} */
const RENDERERS = [];

/**
 * Register one diagnostic tab renderer.
 *
 * @param {DiagnosticTabEntry} entry The renderer to add.
 * @returns {() => void} A disposer removing the registration.
 */
export function registerDiagnosticTab(entry) {
  if (!entry || typeof entry !== "object") {
    throw new TypeError("registerDiagnosticTab requires an entry object");
  }
  const id = String(entry.id || "");
  if (!id) {
    throw new TypeError("registerDiagnosticTab requires a non-empty id");
  }
  if (RENDERERS.some((existing) => existing.id === id)) {
    throw new Error(`diagnostic tab "${id}" is already registered`);
  }
  const labelKey = String(entry.labelKey || "");
  if (!labelKey) {
    throw new TypeError(`diagnostic tab "${id}" requires a non-empty labelKey`);
  }
  if (typeof entry.render !== "function") {
    throw new TypeError(`diagnostic tab "${id}" requires a render function`);
  }
  const numericOrder = Number(entry.order);
  const order = Number.isFinite(numericOrder) ? numericOrder : Number.MAX_SAFE_INTEGER;
  const stored = { id, labelKey, order, render: entry.render };
  // Insert then stable-sort: entries sharing an order keep registration order,
  // so mounting the same set always yields the same tab sequence.
  RENDERERS.push(stored);
  RENDERERS.sort((left, right) => left.order - right.order);
  return () => {
    const index = RENDERERS.indexOf(stored);
    if (index >= 0) RENDERERS.splice(index, 1);
  };
}

/**
 * Snapshot of registered renderers in render order.
 *
 * @returns {Array<DiagnosticTabEntry>} Detached copies in ascending order.
 */
export function diagnosticTabRenderers() {
  return RENDERERS.map((entry) => ({ ...entry }));
}

/** Remove every registration. Intended for test isolation. */
export function resetDiagnosticTabRenderers() {
  RENDERERS.length = 0;
}
