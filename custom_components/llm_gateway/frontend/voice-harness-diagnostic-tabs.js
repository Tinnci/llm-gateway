// @ts-check

/**
 * Static renderer composition for the Voice Harness diagnostic drawer tabs.
 *
 * This mirrors the Cordis pattern the kernel uses elsewhere: sections are
 * defined in a table instead of being hard-coded into one consumer. The drawer
 * iterates the composed definition, and unknown backend fields already fall
 * through the generic raw-tab panels.
 *
 * Composition validates every entry, and a duplicate id throws instead of
 * silently replacing a renderer.
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

/**
 * Define the complete diagnostic tab renderer set.
 *
 * @param {ReadonlyArray<DiagnosticTabEntry>} entries Tab metadata and renderers.
 * @returns {ReadonlyArray<Readonly<DiagnosticTabEntry>>} Validated tabs in render order.
 */
export function defineDiagnosticTabs(entries) {
  if (!Array.isArray(entries)) {
    throw new TypeError("defineDiagnosticTabs requires an array");
  }
  const ids = new Set();
  const tabs = entries.map((entry, index) => {
    if (!entry || typeof entry !== "object") {
      throw new TypeError("defineDiagnosticTabs requires entry objects");
    }
    const id = String(entry.id || "");
    if (!id) {
      throw new TypeError("diagnostic tab requires a non-empty id");
    }
    if (ids.has(id)) {
      throw new Error(`diagnostic tab "${id}" is already defined`);
    }
    ids.add(id);
    const labelKey = String(entry.labelKey || "");
    if (!labelKey) {
      throw new TypeError(`diagnostic tab "${id}" requires a non-empty labelKey`);
    }
    if (typeof entry.render !== "function") {
      throw new TypeError(`diagnostic tab "${id}" requires a render function`);
    }
    const numericOrder = Number(entry.order);
    const order = Number.isFinite(numericOrder) ? numericOrder : Number.MAX_SAFE_INTEGER;
    return {
      index,
      tab: Object.freeze({ id, labelKey, order, render: entry.render }),
    };
  });
  tabs.sort((left, right) => left.tab.order - right.tab.order || left.index - right.index);
  return Object.freeze(tabs.map(({ tab }) => tab));
}
