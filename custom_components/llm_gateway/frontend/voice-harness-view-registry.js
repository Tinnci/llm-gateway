// @ts-check

/**
 * Top-level Voice Harness view registry.
 *
 * DSH composes browser surfaces through keyed UI slots. Voice Harness uses the
 * same small pattern without importing a second runtime: a view registers its
 * metadata and pure dispatch function, and the panel renders the current
 * registry snapshot.
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

/** @type {Array<HarnessViewEntry>} */
const VIEWS = [];

/**
 * Register one top-level Harness view.
 *
 * @param {HarnessViewEntry} entry View metadata and renderer.
 * @returns {() => void} A disposer that removes this exact registration.
 */
export function registerHarnessView(entry) {
  if (!entry || typeof entry !== "object") {
    throw new TypeError("registerHarnessView requires an entry object");
  }
  const id = String(entry.id || "");
  if (!id) {
    throw new TypeError("registerHarnessView requires a non-empty id");
  }
  if (VIEWS.some((existing) => existing.id === id)) {
    throw new Error(`harness view "${id}" is already registered`);
  }
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
  const stored = {
    id,
    labelKey,
    icon,
    order,
    render: entry.render,
    ...(entry.visible ? { visible: entry.visible } : {}),
  };
  VIEWS.push(stored);
  VIEWS.sort((left, right) => left.order - right.order);
  return () => {
    const index = VIEWS.indexOf(stored);
    if (index >= 0) VIEWS.splice(index, 1);
  };
}

/**
 * Return a detached registry snapshot in navigation order.
 *
 * @returns {Array<HarnessViewEntry>}
 */
export function harnessViews() {
  return VIEWS.map((entry) => ({ ...entry }));
}

/** Remove all registrations. Intended for test isolation. */
export function resetHarnessViews() {
  VIEWS.length = 0;
}
