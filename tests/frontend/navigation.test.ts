import { afterAll, describe, expect, test } from "bun:test";
import { Window } from "happy-dom";

const browserWindow = new Window({ url: "http://localhost" });
Object.assign(globalThis, {
  CSS: browserWindow.CSS,
  CSSStyleSheet: browserWindow.CSSStyleSheet,
  CustomEvent: browserWindow.CustomEvent,
  Document: browserWindow.Document,
  Event: browserWindow.Event,
  HTMLDetailsElement: browserWindow.HTMLDetailsElement,
  HTMLElement: browserWindow.HTMLElement,
  KeyboardEvent: browserWindow.KeyboardEvent,
  Node: browserWindow.Node,
  ShadowRoot: browserWindow.ShadowRoot,
  customElements: browserWindow.customElements,
  document: browserWindow.document,
  window: browserWindow,
});

const { VoiceHarnessNavigation } = await import(
  "../../custom_components/llm_gateway/frontend/voice-harness-navigation"
);
const { VoiceHarnessRunList } = await import(
  "../../custom_components/llm_gateway/frontend/voice-harness-run-list"
);
const { VoiceHarnessOverview } = await import(
  "../../custom_components/llm_gateway/frontend/voice-harness-overview"
);

afterAll(() => browserWindow.close());

describe("Voice Harness navigation", () => {
  test("renders a compact task-based view list", async () => {
    const navigation = new VoiceHarnessNavigation();
    navigation.active = "overview";
    navigation.items = [
      { id: "overview", label: "Overview", icon: "mdi:view-dashboard-outline" },
      { id: "runs", label: "Runs", icon: "mdi:play-circle-outline" },
      { id: "test", label: "Test", icon: "mdi:flask-outline" },
      { id: "settings", label: "Settings", icon: "mdi:cog-outline" },
    ];
    document.body.append(navigation);
    await navigation.updateComplete;

    const tabs = navigation.shadowRoot?.querySelectorAll("button") || [];
    expect(tabs).toHaveLength(4);
    expect(tabs[0]?.getAttribute("aria-selected")).toBe("true");
  });

  test("emits a typed selection event", async () => {
    const navigation = new VoiceHarnessNavigation();
    navigation.active = "overview";
    navigation.items = [
      { id: "overview", label: "Overview", icon: "mdi:view-dashboard-outline" },
      { id: "runs", label: "Runs", icon: "mdi:play-circle-outline" },
    ];
    document.body.append(navigation);
    await navigation.updateComplete;

    const selected: string[] = [];
    navigation.addEventListener("harness-view-select", (event) => {
      selected.push((event as CustomEvent<{ id: string }>).detail.id);
    });
    navigation.shadowRoot?.querySelectorAll("button")[1]?.click();
    expect(selected).toEqual(["runs"]);
  });
});

describe("Voice Harness run list", () => {
  test("renders summaries and emits one selected run", async () => {
    const list = new VoiceHarnessRunList();
    list.selected = "run-1";
    list.items = [
      {
        id: "run-1",
        latency: "120 ms",
        route: "Fast",
        status: "ok",
        subtitle: "turn on the light",
        title: "12:00",
      },
      {
        id: "run-2",
        latency: "900 ms",
        route: "Mid",
        status: "bad",
        subtitle: "what failed",
        title: "12:01",
      },
    ];
    document.body.append(list);
    await list.updateComplete;

    const selected: string[] = [];
    list.addEventListener("harness-run-select", (event) => {
      selected.push((event as CustomEvent<{ id: string }>).detail.id);
    });
    const rows = list.shadowRoot?.querySelectorAll("button") || [];
    expect(rows).toHaveLength(2);
    expect(rows[0]?.getAttribute("aria-selected")).toBe("true");
    rows[1]?.click();
    expect(selected).toEqual(["run-2"]);
  });
});

describe("Voice Harness overview", () => {
  test("owns summary composition and task navigation", async () => {
    const overview = new VoiceHarnessOverview();
    overview.model = {
      actions: [
        { destination: "runs", icon: "mdi:play", label: "Inspect runs" },
        { destination: "test", icon: "mdi:flask", label: "Run a test" },
      ],
      ariaLabel: "System health",
      diagnosticsLabel: "Advanced diagnostics",
      focusHint: "Inspect the affected run.",
      focusIcon: "mdi:alert",
      focusTitle: "Investigation needed",
      headline: "System health",
      memoryLabel: "Recent memory",
      metrics: [
        { icon: "mdi:lan", label: "Gateways", tone: "ok", value: "1" },
      ],
      stateLabel: "Investigation needed",
      stateTone: "warning",
      statusLine: "1 gateway",
    };
    overview.openSections = ["memory"];
    document.body.append(overview);
    await overview.updateComplete;

    expect(overview.shadowRoot?.querySelectorAll("voice-harness-stat")).toHaveLength(1);
    const disclosures = overview.shadowRoot?.querySelectorAll("details") || [];
    expect(disclosures).toHaveLength(2);
    expect(disclosures[1]?.open).toBe(true);

    const destinations: string[] = [];
    overview.addEventListener("harness-overview-navigate", (event) => {
      destinations.push(
        (event as CustomEvent<{ destination: string }>).detail.destination,
      );
    });
    overview.shadowRoot?.querySelector("button")?.click();
    expect(destinations).toEqual(["runs"]);
  });

  test("reports disclosure state without owning panel data", async () => {
    const overview = new VoiceHarnessOverview();
    overview.model = {
      actions: [],
      ariaLabel: "System health",
      diagnosticsLabel: "Advanced diagnostics",
      focusHint: "Ready",
      focusIcon: "mdi:check",
      focusTitle: "Ready",
      headline: "System health",
      memoryLabel: "Recent memory",
      metrics: [],
      stateLabel: "Ready",
      stateTone: "ok",
      statusLine: "1 gateway",
    };
    document.body.append(overview);
    await overview.updateComplete;

    const changes: Array<{ id: string; open: boolean }> = [];
    overview.addEventListener("harness-overview-disclosure-toggle", (event) => {
      changes.push((event as CustomEvent<{ id: string; open: boolean }>).detail);
    });
    const details = overview.shadowRoot?.querySelector("details");
    if (!details) throw new Error("diagnostics disclosure was not rendered");
    details.open = true;
    details.dispatchEvent(new Event("toggle"));
    expect(changes.at(-1)).toEqual({ id: "diagnostics", open: true });
  });
});
