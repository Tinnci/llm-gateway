import { afterAll, expect, test } from "bun:test";
import { Window } from "happy-dom";

const dom = new Window({ url: "http://localhost" });
for (const key of ["window", "document", "customElements", "HTMLElement", "HTMLInputElement", "HTMLDetailsElement", "CustomEvent", "Document", "CSSStyleSheet", "ShadowRoot", "Node", "navigator"]) {
  globalThis[key] = key === "window" ? dom : dom[key];
}
await import("../../custom_components/llm_gateway/frontend/voice-harness-panel.js");
afterAll(() => dom.close());
const createPanel = () => new (customElements.get("voice-harness-panel"))();

test("satellite save captures edits before loading render and preserves failures", async () => {
  const panel = createPanel();
  panel._data = { satellite: { states: { wake_threshold: { entity_id: "input_number.wake" } } } };
  panel.shadowRoot.innerHTML = '<input data-satellite-config="wake_threshold" value="0.8">';
  panel._render = () => { panel.shadowRoot.innerHTML = '<input data-satellite-config="wake_threshold" value="0.5">'; };
  const calls = [];
  panel.hass = { callService: async (...args) => { calls.push(args); } };
  panel._load = async () => {};
  await panel._satelliteAction("save-config");
  expect(calls[0][2].value).toBe(0.8);
  panel.hass.callService = async () => { throw new Error("offline"); };
  panel._load = async () => { throw new Error("must preserve action error"); };
  await panel._satelliteAction("save-config");
  expect(panel._error).toBe("offline");
});

test("detail loading leaves coarse records unchanged", async () => {
  const panel = createPanel();
  const summary = { run_id: "a", status: "ok" };
  const entry = { entry_id: "e", traces: { records: [summary] } };
  panel._api = async () => ({ record: { ...summary, timeline: [{ stage: "intent" }] } });
  await panel._loadRunDetail(entry, "a");
  expect(entry.traces.records[0]).toBe(summary);
  expect(panel._selectedRunRecord("e", entry.traces.records).timeline).toHaveLength(1);
});

test("settings fields survive full-root loading renders", () => {
  const panel = createPanel();
  panel._renderActive = () => '<form data-form="config" data-entry-id="e"><input name="base_url" value="saved"><input name="enabled" type="checkbox"></form>';
  panel._render();
  panel.shadowRoot.querySelector('[name="base_url"]').value = "draft";
  panel.shadowRoot.querySelector('[name="enabled"]').checked = true;
  panel._render();
  expect(panel.shadowRoot.querySelector('[name="base_url"]').value).toBe("draft");
  expect(panel.shadowRoot.querySelector('[name="enabled"]').checked).toBe(true);
});
