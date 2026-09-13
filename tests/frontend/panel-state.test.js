import { afterAll, expect, test } from "bun:test";
import { Window } from "happy-dom";

const dom = new Window({ url: "http://localhost" });
for (const key of [
  "window",
  "document",
  "customElements",
  "HTMLElement",
  "HTMLInputElement",
  "HTMLDetailsElement",
  "CustomEvent",
  "Document",
  "CSSStyleSheet",
  "ShadowRoot",
  "Node",
  "navigator",
]) {
  globalThis[key] = key === "window" ? dom : dom[key];
}
await import("../../custom_components/llm_gateway/frontend/voice-harness-panel.js");
afterAll(() => dom.close());
const createPanel = () => new (customElements.get("voice-harness-panel"))();

test("satellite save captures edits before loading render and preserves failures", async () => {
  const panel = createPanel();
  panel._data = {
    satellite: {
      states: { wake_threshold: { entity_id: "input_number.wake" } },
    },
  };
  panel.shadowRoot.innerHTML =
    '<input data-satellite-config="wake_threshold" value="0.8">';
  panel._render = () => {
    panel.shadowRoot.innerHTML =
      '<input data-satellite-config="wake_threshold" value="0.5">';
  };
  const calls = [];
  panel.hass = {
    callService: async (...args) => {
      calls.push(args);
    },
  };
  panel._load = async () => {};
  await panel._satelliteAction("save-config");
  expect(calls[0][2].value).toBe(0.8);
  panel.hass.callService = async () => {
    throw new Error("offline");
  };
  panel._load = async () => {
    throw new Error("must preserve action error");
  };
  await panel._satelliteAction("save-config");
  expect(panel._error).toBe("offline");
});

test("detail loading leaves coarse records unchanged", async () => {
  const panel = createPanel();
  const summary = { run_id: "a", status: "ok" };
  const entry = { entry_id: "e", traces: { records: [summary] } };
  panel._api = async () => ({
    record: { ...summary, timeline: [{ stage: "intent" }] },
  });
  await panel._loadRunDetail(entry, "a");
  expect(entry.traces.records[0]).toBe(summary);
  expect(panel._runDetails["e:a"].timeline).toHaveLength(1);
});

test("settings fields and their DOM nodes survive observation refreshes", () => {
  const panel = createPanel();
  panel._data = {
    entries: [
      {
        entry_id: "e",
        title: "Gateway",
        state: "loaded",
        traces: { records: [] },
      },
    ],
  };
  panel._configData = { entries: [] };
  panel._activeTab = "settings";
  panel._renderConfig = () =>
    '<form data-form="config" data-entry-id="e"><input name="base_url" value="saved"><input name="enabled" type="checkbox"></form>';
  panel._render();
  panel.shadowRoot.querySelector('[name="base_url"]').value = "draft";
  panel.shadowRoot.querySelector('[name="enabled"]').checked = true;
  const before = panel.shadowRoot.querySelector('[name="base_url"]');
  panel._render();
  expect(panel.shadowRoot.querySelector('[name="base_url"]')).toBe(before);
  expect(panel.shadowRoot.querySelector('[name="base_url"]').value).toBe(
    "draft",
  );
  expect(panel.shadowRoot.querySelector('[name="enabled"]').checked).toBe(true);
});

test("settings still load when opened during an observation request", async () => {
  const panel = createPanel();
  panel.hass = {};
  panel._busy = true;
  panel._api = async () => ({
    entries: [{ entry_id: "e", revision: "current" }],
  });
  panel._render = () => {};
  await panel._loadConfig();
  expect(panel._configData.entries[0].revision).toBe("current");
  expect(panel._busy).toBe(true);
});

test("a config reload preserves the draft for conflict review", () => {
  const panel = createPanel();
  panel._data = { entries: [] };
  panel._activeTab = "settings";
  panel._configData = { entries: [] };
  panel._renderConfig = () =>
    '<form data-form="config" data-entry-id="e"><input name="base_url" value="saved"><input name="enabled" type="checkbox"></form>';
  panel._render();
  panel.shadowRoot.querySelector('[name="base_url"]').value = "draft";
  panel.shadowRoot.querySelector('[name="enabled"]').checked = true;
  panel._configData = { entries: [] };
  panel._render();
  expect(panel.shadowRoot.querySelector('[name="base_url"]').value).toBe(
    "draft",
  );
  expect(panel.shadowRoot.querySelector('[name="enabled"]').checked).toBe(true);
});

test("settings groups, run filters and scenarios respond without polling", async () => {
  const settings = document.createElement("voice-harness-settings");
  const runs = document.createElement("voice-harness-runs");
  const playground = document.createElement("voice-harness-playground");
  runs.entries = [
    {
      entry_id: "e",
      traces: {
        records: [
          { run_id: "a", status: "ok", user_text: "Bedroom" },
          { run_id: "b", status: "failed", user_text: "Living room" },
        ],
      },
    },
  ];
  playground.scenarios = [
    {
      id: "bedroom",
      title: "Bedroom climate",
      user: "How warm is the bedroom?",
      response: "No reading",
      expected: {},
    },
  ];
  document.body.append(settings, runs, playground);
  try {
    await Promise.all([
      settings.updateComplete,
      runs.updateComplete,
      playground.updateComplete,
    ]);
    [...settings.shadowRoot.querySelectorAll("button")]
      .find((button) => button.textContent.includes("Models & routing"))
      .click();
    [...runs.shadowRoot.querySelectorAll("button[aria-pressed]")]
      .find((button) => button.textContent.includes("Failed"))
      .click();
    playground.shadowRoot
      .querySelector('section[aria-label="Scenarios"] button')
      .click();
    await Promise.all([
      settings.updateComplete,
      runs.updateComplete,
      playground.updateComplete,
    ]);
    expect(settings.getAttribute("section")).toBe("routing");
    expect(
      runs.shadowRoot.querySelectorAll(
        'button[aria-label^="Select for comparison"]',
      ),
    ).toHaveLength(1);
    expect(runs.shadowRoot.querySelector("article").textContent).toContain(
      "Living room",
    );
    expect(playground.shadowRoot.querySelector("textarea").value).toBe(
      "How warm is the bedroom?",
    );
    expect(
      playground.shadowRoot
        .querySelector('section[aria-label="Scenarios"] button')
        .getAttribute("aria-pressed"),
    ).toBe("true");
  } finally {
    settings.remove();
    runs.remove();
    playground.remove();
  }
});

test("stopping before subscription acknowledgement closes the late stream", async () => {
  const playground = document.createElement("voice-harness-playground");
  let acknowledge;
  let receive;
  let cancelled = 0;
  const subscription = new Promise((resolve) => {
    acknowledge = resolve;
  });
  playground.hass = {
    connection: {
      subscribeMessage: (callback) => {
        receive = callback;
        return subscription;
      },
    },
  };
  playground.entries = [{ entry_id: "e", title: "Gateway" }];
  playground.scenarios = [
    {
      id: "hello",
      title: "Hello",
      user: "Hello",
      response: "Hi",
      expected: {},
    },
  ];
  document.body.append(playground);
  try {
    await playground.updateComplete;
    playground.shadowRoot
      .querySelector('section[aria-label="Scenarios"] button')
      .click();
    await playground.updateComplete;
    [...playground.shadowRoot.querySelectorAll("button")]
      .find((button) => button.textContent.includes("Run & watch"))
      .click();
    await playground.updateComplete;
    [...playground.shadowRoot.querySelectorAll("button")]
      .find((button) => button.textContent.trim() === "Stop")
      .click();
    acknowledge(() => {
      cancelled++;
    });
    await subscription;
    await playground.updateComplete;
    receive({ type: "token", text: "late answer" });
    await playground.updateComplete;
    expect(cancelled).toBe(1);
    expect(
      playground.shadowRoot.querySelector('[aria-label="Live test output"]')
        .textContent,
    ).toContain("Stopped");
    expect(
      playground.shadowRoot.querySelector('[aria-label="Model response"]')
        .textContent,
    ).not.toContain("late answer");
  } finally {
    playground.remove();
  }
});

test("a lost HA connection fails the preview without automatic resubscription", async () => {
  const playground = document.createElement("voice-harness-playground");
  let disconnect;
  let options;
  let cancelled = 0;
  const removed = [];
  playground.hass = {
    connection: {
      addEventListener: (_type, listener) => {
        disconnect = listener;
      },
      removeEventListener: (_type, listener) => {
        removed.push(listener);
      },
      subscribeMessage: async (callback, _message, settings) => {
        options = settings;
        callback({ type: "token", text: "Partial answer" });
        return () => {
          cancelled++;
        };
      },
    },
  };
  playground.entries = [{ entry_id: "e", title: "Gateway" }];
  document.body.append(playground);
  try {
    await playground.updateComplete;
    const input = playground.shadowRoot.querySelector("textarea");
    input.value = "Hello";
    input.dispatchEvent(new dom.Event("input"));
    await playground.updateComplete;
    [...playground.shadowRoot.querySelectorAll("button")]
      .find((button) => button.textContent.includes("Run & watch"))
      .click();
    await playground.updateComplete;
    expect(options).toEqual({ resubscribe: false });
    disconnect();
    await playground.updateComplete;
    expect(
      playground.shadowRoot.querySelector('[role="alert"]').textContent,
    ).toContain("Connection lost");
    expect(
      playground.shadowRoot.querySelector('[aria-label="Live test output"]')
        .textContent,
    ).not.toContain("Assertions passed");
    expect(cancelled).toBe(1);
    expect(removed).toEqual([disconnect]);
  } finally {
    playground.remove();
  }
});

test("choosing another scenario clears the previous generation's token usage", async () => {
  const playground = document.createElement("voice-harness-playground");
  playground.entries = [{ entry_id: "e", title: "Gateway" }];
  playground.scenarios = [
    { id: "hello", title: "Hello", user: "Hello", response: "Hi", expected: {} },
    { id: "climate", title: "Climate", user: "How warm is it?", response: "Unknown", expected: {} },
  ];
  playground.hass = {
    connection: {
      subscribeMessage: async (receive) => {
        receive({ type: "token", text: "Hi" });
        receive({ type: "usage", usage: { output_tokens: 12 } });
        receive({ type: "complete", passed: true, violations: [] });
        return () => {};
      },
    },
  };
  document.body.append(playground);
  try {
    await playground.updateComplete;
    const scenarios = playground.shadowRoot.querySelectorAll('section[aria-label="Scenarios"] button');
    scenarios[0].click();
    await playground.updateComplete;
    [...playground.shadowRoot.querySelectorAll("button")]
      .find((button) => button.textContent.includes("Run & watch")).click();
    await playground.updateComplete;
    const monitor = playground.shadowRoot.querySelector('[aria-label="Live test output"]');
    expect(monitor.textContent).toContain("output_tokens");
    scenarios[1].click();
    await playground.updateComplete;
    expect(monitor.textContent).not.toContain("output_tokens");
    expect(monitor.textContent).not.toContain("Assertions passed");
  } finally {
    playground.remove();
  }
});

test("reference-only assertion checks do not claim a provider completed", async () => {
  const playground = document.createElement("voice-harness-playground");
  playground.hass = {
    callApi: async () => ({ spoken: "Reference answer", passed: true, violations: [] }),
  };
  document.body.append(playground);
  try {
    await playground.updateComplete;
    const input = playground.shadowRoot.querySelector("textarea");
    input.value = "Hello";
    input.dispatchEvent(new dom.Event("input"));
    await playground.updateComplete;
    [...playground.shadowRoot.querySelectorAll("button")]
      .find((button) => button.textContent.includes("Check assertions")).click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await playground.updateComplete;
    const monitor = playground.shadowRoot.querySelector('[aria-label="Live test output"]');
    expect(monitor.textContent).toContain("Assertions passed");
    expect(monitor.textContent).not.toContain("Provider completion");
    expect(monitor.textContent).toContain("Reference reply checked");
  } finally {
    playground.remove();
  }
});
