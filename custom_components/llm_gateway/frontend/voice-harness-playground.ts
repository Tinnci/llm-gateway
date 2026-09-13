import { css, html, LitElement, nothing } from "lit";
import {
  harnessButtonStyles,
  harnessFoundationStyles,
  harnessSurfaceStyles,
} from "./voice-harness-styles";
import { requestHarnessJson, type HomeAssistantApi } from "./voice-harness-api";
import { object, type EvidenceRecord } from "./voice-harness-live-model";

export interface HarnessLiveApi extends HomeAssistantApi {
  connection?: {
    subscribeMessage: (
      callback: (event: EvidenceRecord) => void,
      message: Record<string, unknown>,
      options?: { resubscribe: boolean },
    ) => Promise<() => Promise<unknown> | void>;
    addEventListener?: (type: "disconnected", listener: () => void) => void;
    removeEventListener?: (type: "disconnected", listener: () => void) => void;
  };
}
export type PlaygroundScenario = {
  id: string;
  title: string;
  user: string;
  response: string;
  expected: Record<string, unknown>;
};
type Draft = { user: string; response: string; expected: string };
type Stream = {
  unsubscribe?: () => Promise<unknown> | void;
  removeDisconnect?: () => void;
};

export class VoiceHarnessPlayground extends LitElement {
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
    entryId: { state: true },
  };
  declare hass: HarnessLiveApi | undefined;
  declare language: string;
  declare scenarios: PlaygroundScenario[];
  declare entries: EvidenceRecord[];
  declare private draft: Draft;
  declare private chosen: string;
  declare private result: EvidenceRecord | null;
  declare private text: string;
  declare private events: EvidenceRecord[];
  declare private usage: EvidenceRecord;
  declare private status: string;
  declare private error: string;
  declare private expanded: boolean;
  declare private route: string;
  declare private entryId: string;
  private active?: Stream;
  private last?: {
    mode: "evaluate" | "stream";
    draft: Draft;
    entryId: string;
    route: string;
  };
  constructor() {
    super();
    this.language = "en";
    this.scenarios = [];
    this.entries = [];
    this.draft = {
      user: "",
      response: "",
      expected: JSON.stringify(
        { spoken_response: { max_sentences: 2 } },
        null,
        2,
      ),
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
  private t(en: string, zh: string) {
    return this.language.startsWith("zh") ? zh : en;
  }
  private choose(scenario: PlaygroundScenario) {
    if (this.active) return;
    this.chosen = scenario.id;
    this.draft = {
      user: scenario.user,
      response: scenario.response,
      expected: JSON.stringify(scenario.expected, null, 2),
    };
    this.result = null;
    this.error = "";
    this.status = "idle";
    this.text = "";
    this.events = [];
    this.usage = {};
  }
  private edit(field: keyof Draft, event: Event) {
    this.draft = {
      ...this.draft,
      [field]: (event.target as HTMLTextAreaElement).value,
    };
  }
  render() {
    const t = this.t.bind(this);
    const working = ["connecting", "streaming", "evaluating"].includes(
      this.status,
    );
    const visible = this.expanded ? this.scenarios : this.scenarios.slice(0, 6);
    return html`
      <div class="section-head">
        <div>
          <span class="eyebrow"
            >VOICE HARNESS / ${t("PLAYGROUND", "测试")}</span
          >
          <h2>
            ${t("Try a thought. Shape a response.", "试一句话，打磨一次回应。")}
          </h2>
          <p class="muted">
            ${t("Explore a scenario, check its assertions, or watch a model compose a reply.", "从生活场景出发，检查断言，或看模型实时组织回答。")}
          </p>
        </div>
        <span class="chip">${t("Preview workspace", "演练工作台")}</span>
      </div>
      <section class="scenarios" aria-label=${t("Scenarios", "场景卡片")}>
        ${visible.map(
          (scenario, index) =>
            html`<button
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
            </button>`,
        )}
      </section>
      ${
        this.scenarios.length > 6
          ? html`<button
              class="quiet more"
              @click=${() => {
                this.expanded = !this.expanded;
              }}
            >
              ${this.expanded ? t("Show less", "收起场景") : t("All scenarios", "全部场景") + " · " + this.scenarios.length}
            </button>`
          : nothing
      }
      <div class="workbench">
        <section class="surface composer">
          <div class="section-head">
            <div>
              <span class="eyebrow">COMPOSE</span>
              <h3>${t("Your test conversation", "你的测试对话")}</h3>
            </div>
            <span class="chip">${t("Text input", "文本输入")}</span>
          </div>
          <label
            >${t("Say something", "说点什么")}<textarea
              rows="4"
              .value=${this.draft.user}
              ?disabled=${working}
              @input=${(event: Event) => this.edit("user", event)}
              placeholder=${t("What is the temperature in the bedroom?", "卧室现在温度怎么样？")}
            ></textarea>
          </label>
          <div class="route-fields">
            <label
              >${t("Gateway", "网关")}<select
                .value=${this.entryId || String(this.entries[0]?.entry_id || "")}
                ?disabled=${working}
                @change=${(event: Event) => {
                  this.entryId = (event.target as HTMLSelectElement).value;
                }}
              >
                ${this.entries.map((entry) => html`<option value=${String(entry.entry_id)}>${String(entry.title)}</option>`)}
              </select></label
            ><label
              >${t("Model route", "模型路由")}<select
                .value=${this.route}
                ?disabled=${working}
                @change=${(event: Event) => {
                  this.route = (event.target as HTMLSelectElement).value;
                }}
              >
                ${["auto", "fast", "mid", "deep"].map((route) => html`<option value=${route}>${route === "auto" ? t("Automatic", "自动") : route[0].toUpperCase() + route.slice(1)}</option>`)}
              </select></label
            >
          </div>
          <details class="draft-details" open>
            <summary>
              ${t("Assertions & reference reply", "断言与参考回答")}
            </summary>
            <label
              >${t("Reference reply (assertion check only)", "参考回答（用于断言检查）")}<textarea
                rows="3"
                .value=${this.draft.response}
                ?disabled=${working}
                @input=${(event: Event) => this.edit("response", event)}
              ></textarea></label
            ><label
              >${t("Expected behavior · JSON", "预期行为 · JSON")}<textarea
                class="code"
                rows="5"
                .value=${this.draft.expected}
                ?disabled=${working}
                @input=${(event: Event) => this.edit("expected", event)}
              ></textarea>
            </label>
          </details>
          <div class="actions">
            <button
              class="primary"
              ?disabled=${working || !this.draft.user.trim() || !this.entries.length}
              @click=${() => this.run("stream")}
            >
              ${t("Run & watch", "运行并观察")} ↗</button
            ><button
              ?disabled=${working || !this.draft.user.trim()}
              @click=${() => this.run("evaluate")}
            >
              ${t("Check assertions", "检查断言")}
            </button>
          </div>
          <p class="muted boundary">
            ${t("Model preview makes a real provider request. Tool calls are shown as proposals; device state is never changed. Text scenarios do not measure microphone or network reliability.", "模型演练会真实请求服务商；工具调用显示为提案，设备状态不变。文本场景不代表麦克风或弱网实测。")}
          </p>
        </section>
        <section
          class="surface monitor"
          aria-label=${t("Live test output", "实时测试输出")}
        >
          <div class="section-head">
            <div>
              <span class="eyebrow">LIVE OUTPUT</span>
              <h3>${t("As it happens", "看见回应发生")}</h3>
            </div>
            <span
              class=${"chip " + (this.status === "error" ? "bad" : this.status === "complete" ? "ok" : "muted")}
              >${{ idle: t("Ready", "就绪"), connecting: t("Connecting", "连接中"), streaming: t("Streaming", "生成中"), evaluating: t("Checking", "检查中"), complete: t("Complete", "已完成"), cancelled: t("Stopped", "已停止"), error: t("Failed", "失败") }[this.status as "idle"] || this.status}</span
            >
          </div>
          ${this.error ? html`<p class="error" role="alert">${this.error}</p>` : nothing}
          ${
            this.status === "idle" && !this.text
              ? html`<div class="waiting">
                  <div class="waiting-glyph">
                    <ha-icon icon="mdi:creation-outline"></ha-icon>
                  </div>
                  <h3>
                    ${t("Space for a new idea", "给一句新想法，留个位置")}
                  </h3>
                  <p>
                    ${t("Choose a scenario or write your own. The response and tool proposals appear here.", "选择场景，或写下你的问题。回答与工具提案会在这里展开。")}
                  </p>
                </div>`
              : html`<div
                  class="stream-text"
                  aria-label=${t("Model response", "模型回答")}
                >
                  ${this.text}${working ? html`<span class="caret" aria-hidden="true"></span>` : nothing}
                </div>`
          }
          <div class="event-track">
            ${this.events.map(
              (event) =>
                html`<article class="stream-event">
                  <span class="event-marker"></span>
                  <div>
                    <strong
                      >${event.type === "route" ? String(event.route).toUpperCase() + " · " + String(event.model) : t("Tool proposal", "工具提案") + " · " + String(event.name || "…")}</strong
                    >${event.type === "tool" ? html`<code>${String(event.arguments || "")}</code><small>${t("Not dispatched", "尚未派发")}</small>` : nothing}
                  </div>
                </article>`,
            )}
          </div>
          ${Object.keys(this.usage).length ? html`<div class="tokens">${Object.entries(this.usage).map(([key, value]) => html`<span>${key}: <strong>${String(value)}</strong></span>`)}</div>` : nothing}
          ${this.result ? html`<div class=${"assertions " + (this.result.passed ? "ok" : "bad")} role="status"><strong>${this.result.passed ? "✓ " + t("Assertions passed", "断言通过") : "× " + t("Assertions failed", "断言未通过")}</strong>${Array.isArray(this.result.violations) ? this.result.violations.map((violation) => html`<p>${String(violation)}</p>`) : nothing}</div>` : nothing}
          <div class="monitor-actions">
            ${working ? html`<button @click=${() => this.stop()}>${t("Stop", "停止")}</button>` : this.last ? html`<button @click=${() => this.replayLast()}>↻ ${t("Replay test", "重放本轮测试")}</button>` : nothing}<span
              role="status"
              class="muted"
              >${this.status === "complete" ? this.last?.mode === "evaluate" ? t("Reference reply checked", "已检查参考回答") : t("Provider completion and assertions recorded", "已记录生成结束与断言结果") : ""}</span
            >
          </div>
        </section>
      </div>
      <details class="surface policies">
        <summary>${t("Prompt & policy reference", "提示词与策略参考")}</summary>
        <slot name="policies"></slot>
      </details>
    `;
  }
  private async run(mode: "evaluate" | "stream", replay = false) {
    let expected: unknown;
    try {
      expected = JSON.parse(this.draft.expected);
      if (!expected || typeof expected !== "object" || Array.isArray(expected))
        throw new Error();
    } catch {
      this.error = this.t(
        "Expected behavior must be a JSON object.",
        "预期行为必须是 JSON 对象。",
      );
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
    const stream: Stream = {};
    this.active = stream;
    this.status = mode === "stream" ? "connecting" : "evaluating";
    try {
      if (mode === "evaluate") {
        const result = await requestHarnessJson<EvidenceRecord>(
          this.hass,
          "POST",
          "llm_gateway/harness/evaluate",
          {
            entry_id: entryId,
            user: snapshot.user,
            response: snapshot.response,
            expected,
          },
        );
        if (this.active !== stream) return;
        this.result = result;
        this.text = String(result.spoken || "");
        this.status = "complete";
        this.active = undefined;
        return;
      }
      if (!this.hass?.connection)
        throw new Error(
          this.t(
            "Connect through Home Assistant to stream a model response.",
            "请通过 Home Assistant 连接模型流式演练。",
          ),
        );
      const connection = this.hass.connection;
      const disconnected = () => {
        if (this.active !== stream) return;
        this.error = this.t(
          "Connection lost. Replay when Home Assistant reconnects.",
          "连接已断开，Home Assistant 恢复后可重放测试。",
        );
        this.status = "error";
        this.active = undefined;
        this.release(stream);
      };
      connection.addEventListener?.("disconnected", disconnected);
      stream.removeDisconnect = () =>
        connection.removeEventListener?.("disconnected", disconnected);
      const unsubscribe = await connection.subscribeMessage(
        (event) => {
          if (this.active !== stream) return;
          if (event.type === "token") {
            this.status = "streaming";
            this.text += String(event.text || "");
          }
          if (event.type === "route") this.events = [...this.events, event];
          if (event.type === "tool") {
            const prior = this.events.findIndex(
              (item) => item.type === "tool" && item.index === event.index,
            );
            this.events =
              prior < 0
                ? [...this.events, { ...event }]
                : this.events.map((item, index) =>
                    index === prior ? { ...event } : item,
                  );
          }
          if (event.type === "usage") this.usage = object(event.usage);
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
        },
        {
          type: "llm_gateway/harness/stream",
          entry_id: entryId,
          user: snapshot.user,
          route: this.route,
          expected,
        },
        { resubscribe: false },
      );
      stream.unsubscribe = unsubscribe;
      if (this.active !== stream) this.release(stream);
    } catch (error) {
      if (this.active !== stream) return;
      this.error = error instanceof Error ? error.message : String(error);
      this.status = "error";
      this.active = undefined;
      this.release(stream);
    }
  }
  private stop() {
    const current = this.active;
    this.active = undefined;
    if (current) this.release(current);
    this.status = "cancelled";
  }
  private release(stream: Stream) {
    stream.removeDisconnect?.();
    stream.removeDisconnect = undefined;
    const unsubscribe = stream.unsubscribe;
    stream.unsubscribe = undefined;
    // A disconnected transport may reject its final unsubscribe request.
    if (unsubscribe)
      void Promise.resolve()
        .then(unsubscribe)
        .catch(() => {});
  }
  private replayLast() {
    if (!this.last) return;
    this.draft = { ...this.last.draft };
    this.entryId = this.last.entryId;
    this.route = this.last.route;
    void this.run(this.last.mode, true);
  }
  disconnectedCallback() {
    if (this.active) this.stop();
    super.disconnectedCallback();
  }
  static styles = [
    harnessFoundationStyles,
    harnessButtonStyles,
    harnessSurfaceStyles,
    css`
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
    `,
  ];
}
if (!customElements.get("voice-harness-playground"))
  customElements.define("voice-harness-playground", VoiceHarnessPlayground);
declare global {
  interface HTMLElementTagNameMap {
    "voice-harness-playground": VoiceHarnessPlayground;
  }
}
