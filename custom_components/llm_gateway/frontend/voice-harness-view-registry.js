// @ts-check

/**
 * Top-level Voice Harness view registry.
 *
 * The panel composition root defines its complete view set once. This module
 * validates and orders that static definition while keeping view metadata and
 * rendering concerns outside the panel's navigation code.
 *
 * @module voice-harness-view-registry
 */

/**
 * @typedef {Object} HarnessViewEntry
 * @property {string} id Stable navigation and selection key.
 * @property {string} labelKey I18N key for the navigation label.
 * @property {string} icon Home Assistant icon identifier.
 * @property {number} order Ascending navigation order.
 * @property {(panel: any, entries: Array<Record<string, any>>) => string} render
 * @property {((panel: any) => boolean)=} visible Optional visibility predicate.
 */

/**
 * Define the complete top-level Harness view set.
 *
 * @param {ReadonlyArray<HarnessViewEntry>} entries View metadata and renderers.
 * @returns {ReadonlyArray<Readonly<HarnessViewEntry>>} Validated views in navigation order.
 */
export function defineHarnessViews(entries) {
  if (!Array.isArray(entries)) {
    throw new TypeError("defineHarnessViews requires an array");
  }
  const ids = new Set();
  const views = entries.map((entry, index) => {
    if (!entry || typeof entry !== "object") {
      throw new TypeError("defineHarnessViews requires entry objects");
    }
    const id = String(entry.id || "");
    if (!id) {
      throw new TypeError("harness view requires a non-empty id");
    }
    if (ids.has(id)) {
      throw new Error(`harness view "${id}" is already defined`);
    }
    ids.add(id);
    const labelKey = String(entry.labelKey || "");
    if (!labelKey) {
      throw new TypeError(`harness view "${id}" requires a non-empty labelKey`);
    }
    const icon = String(entry.icon || "");
    if (!icon) {
      throw new TypeError(`harness view "${id}" requires a non-empty icon`);
    }
    if (typeof entry.render !== "function") {
      throw new TypeError(`harness view "${id}" requires a render function`);
    }
    if (entry.visible !== undefined && typeof entry.visible !== "function") {
      throw new TypeError(`harness view "${id}" visible must be a function`);
    }
    const numericOrder = Number(entry.order);
    const order = Number.isFinite(numericOrder) ? numericOrder : Number.MAX_SAFE_INTEGER;
    return {
      index,
      view: Object.freeze({
        id,
        labelKey,
        icon,
        order,
        render: entry.render,
        ...(entry.visible ? { visible: entry.visible } : {}),
      }),
    };
  });
  views.sort((left, right) => left.view.order - right.view.order || left.index - right.index);
  return Object.freeze(views.map(({ view }) => view));
}
