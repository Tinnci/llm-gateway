import { css, html, LitElement, nothing } from "lit";
import {
  harnessButtonStyles,
  harnessFoundationStyles,
  harnessSurfaceStyles,
} from "./voice-harness-styles";
import {
  livePipeline,
  object,
  observedMetrics,
  records,
  type EvidenceRecord,
} from "./voice-harness-live-model";
import "./voice-harness-stat";

export type HarnessOverviewDestination = "runs" | "test" | "settings";
export type HarnessOverviewTone = "bad" | "muted" | "ok" | "warning";
export type HarnessOverviewMetric = {
  icon: string;
  label: string;
  tone: HarnessOverviewTone;
  value: string;
  values?: number[];
  hint?: string;
};
export type HarnessOverviewModel = {
  actions: Array<{
    destination: HarnessOverviewDestination;
    icon: string;
    label: string;
  }>;
  ariaLabel: string;
  diagnosticsLabel: string;
  focusHint: string;
  focusIcon: string;
  focusTitle: string;
  headline: string;
  memoryLabel: string;
  metrics: HarnessOverviewMetric[];
  stateLabel: string;
  stateTone: "ok" | "warning";
  statusLine: string;
};

export class VoiceHarnessOverview extends LitElement {
  static properties = {
    model: { attribute: false },
    openSections: { attribute: false },
    entries: { attribute: false },
    satellite: { attribute: false },
    language: {},
    updatedAt: {},
  };
  declare model: HarnessOverviewModel | null;
  declare openSections: string[];
  declare entries: EvidenceRecord[];
  declare satellite: EvidenceRecord;
  declare language: string;
  declare updatedAt: string;
  constructor() {
    super();
    this.model = null;
    this.openSections = [];
    this.entries = [];
    this.satellite = {};
    this.language = "en";
    this.updatedAt = "";
  }
  private text(en: string, zh: string) {
    return this.language.startsWith("zh") ? zh : en;
  }
  render() {
    const t = this.text.bind(this);
    const runs = this.entries.flatMap((entry) =>
      records(object(entry.traces).records),
    );
    const metrics = observedMetrics(runs);
    const states = object(this.satellite.states);
    const snapshot = object(this.satellite.diagnostic_snapshot);
    const display = object(object(this.entries[0]?.feedback).latest_display);
    const live = livePipeline(states, display);
    const checks = records(snapshot.checks);
    const firstIssue = object(snapshot.first_failing_check);
    const issue = firstIssue.id
      ? firstIssue
      : checks.find((check) =>
          ["error", "warning"].includes(String(check.status)),
        );
    const loaded = this.entries.some((entry) => entry.state === "loaded");
    const format = (value: number | null, suffix: string) =>
      value === null
        ? "—"
        : new Intl.NumberFormat(this.language, {
            maximumFractionDigits: suffix === "ms" ? 0 : 1,
          }).format(value) + suffix;
    const latestWake = records(snapshot.event_stream)
      .filter((event) => /wake/.test(String(event.type)))
      .at(-1);
    const wakeValue =
      latestWake?.timestamp || object(snapshot.wake).last_detected_at;
    const asr = object(snapshot.asr);
    const tts = object(snapshot.tts);
    const summaryHint =
      t("Latest ", "最近 ") +
      metrics.count +
      t(" completed live runs", " 次已结束实机运行");
    const model = this.model;
    return html`
      <div class="section-head intro">
        <div>
          <span class="eyebrow">VOICE HARNESS / ${t("OVERVIEW", "概览")}</span>
          <h2>
            ${t("A little closer to effortless.", "让每一句，都自然发生。")}
          </h2>
          <p class="muted">
            ${t("A clear view of your voice, from the first word to the last reply.", "从唤醒到回应，安静而清楚地看见语音的每一步。")}
          </p>
        </div>
        <span class="chip ${issue ? "warning" : loaded ? "ok" : "muted"}"
          ><span class="dot"></span
          >${issue ? t("Needs attention", "需要留意") : loaded ? t("Gateway ready", "网关已就绪") : t("Awaiting observations", "等待观测")}</span
        >
      </div>
      <div class="bento">
        <section
          class="surface pipeline"
          aria-label=${t("Observed voice pipeline", "语音链路观测")}
        >
          <div class="section-head">
            <div>
              <span class="eyebrow">LIVE PIPELINE</span>
              <h3>${t("One continuous conversation", "一段连贯的对话")}</h3>
            </div>
            <span class="chip"
              >${live.active ? t("Active", "交互中") : live.phase === "standby" ? t("Standing by", "待机") : live.phase === "paused" ? t("Capture paused", "收音已暂停") : t("No live evidence", "暂无实时观测")}</span
            >
          </div>
          <div
            class="pulse-scene"
            data-active=${String(live.active)}
            aria-hidden="true"
          >
            <div class="orb">
              <ha-icon icon="mdi:microphone-outline"></ha-icon>
            </div>
            <div class="wave">
              ${Array.from({ length: 15 }, (_, i) => html`<i style=${"--i:" + i + ";--h:" + (8 + (7 - Math.abs(7 - i)) * 5) + "px"}></i>`)}
            </div>
          </div>
          <div class="pipeline-nodes">
            ${[
            ["mdi:microphone-outline", t("Wake", "唤醒")],
            ["mdi:waveform", "ASR"],
            ["mdi:creation-outline", "LLM"],
            ["mdi:volume-high", "TTS"],
            ["mdi:play-circle-outline", t("Playback", "播放")],
            ["mdi:reply-outline", t("Follow-up", "追问")],
          ].map(
            ([icon, label]) =>
              html`<span><ha-icon icon=${icon}></ha-icon>${label}</span>`,
          )}
          </div>
          <p class="pipeline-note">
            ${live.active ? String(display.title || display.state || "") : live.phase === "paused" ? t("Capture is paused. Resume it in acoustic settings when you are ready.", "收音已暂停，可在声学设置中恢复。") : live.connected ? t("Ready when you are. Animation follows fresh capture and response evidence.", "随时等你开口。动效随最新收音与回应状态出现。") : t("Waiting for current satellite observations.", "等待卫星的最新观测。")}
          </p>
        </section>
        <section class="surface focus">
          <div class="section-head">
            <span class="eyebrow">${t("YOUR NEXT STEP", "值得留意")}</span
            ><ha-icon
              icon=${issue ? "mdi:alert-circle-outline" : "mdi:check-decagram-outline"}
            ></ha-icon>
          </div>
          <h3>
            ${issue ? t("A detail needs a closer look", "有一处细节值得看看") : t("Make room for a better response", "为更好的回应，留一点空间")}
          </h3>
          <p class="muted">
            ${issue ? t("Open system observations for the source, dependencies and recovery guidance.", "展开系统观测，可查看来源、依赖和恢复建议。") : t("Explore a recent conversation, or try a scenario without changing your home.", "展开最近的对话，或用场景演练打磨下一次回应。")}
          </p>
          <div class="focus-actions">
            ${(
            model?.actions || [
              {
                destination: "runs",
                icon: "mdi:arrow-top-right",
                label: t("Explore runs", "查看运行记录"),
              },
              {
                destination: "test",
                icon: "mdi:flask-outline",
                label: t("Try a scenario", "开始场景演练"),
              },
            ]
          ).map(
            (action) =>
              html`<button
                @click=${() => this.navigate(action.destination as HarnessOverviewDestination)}
              >
                <span>${action.label}</span
                ><ha-icon icon=${action.icon}></ha-icon>
              </button>`,
          )}
          </div>
        </section>
        <div class="metrics">
          <voice-harness-stat
            .label=${t("Median response", "响应中位数")}
            .value=${format(metrics.medianMs, "ms")}
            .values=${metrics.latencies}
            .hint=${summaryHint}
            icon="mdi:timer-outline"
          ></voice-harness-stat>
          <voice-harness-stat
            .label=${t("Answered", "回答完成率")}
            .value=${format(metrics.successRate, "%")}
            .values=${metrics.outcomes}
            .hint=${t("Conversation outcome", "按对话结果统计")}
            tone="ok"
            icon="mdi:check-circle-outline"
          ></voice-harness-stat>
          <voice-harness-stat
            .label=${t("Error rate", "错误率")}
            .value=${format(metrics.errorRate, "%")}
            .values=${metrics.errors}
            .hint=${summaryHint}
            .tone=${metrics.errorRate ? "bad" : "muted"}
            icon="mdi:pulse"
          ></voice-harness-stat>
          <voice-harness-stat
            .label=${t("Last wake", "最近唤醒")}
            .value=${typeof wakeValue === "string" && Number.isFinite(Date.parse(wakeValue)) ? new Date(wakeValue).toLocaleTimeString(this.language, { hour: "2-digit", minute: "2-digit" }) : "—"}
            .hint=${t("Satellite timestamp", "卫星唤醒时间戳")}
            icon="mdi:microphone-outline"
          ></voice-harness-stat>
        </div>
        <section class="surface services">
          <div class="section-head">
            <div>
              <span class="eyebrow">CONNECTED SYSTEM</span>
              <h3>${t("Working together", "彼此协同")}</h3>
            </div>
            <button class="quiet" @click=${() => this.navigate("settings")}>
              ${t("Settings", "设置")} ↗
            </button>
          </div>
          <div class="service-grid">
            ${this.service("LLM Gateway", t("Routing & response", "路由与回答"), loaded ? "ok" : "muted", loaded ? t("Loaded", "已加载") : t("Unknown", "未知"), "mdi:creation-outline")}
            ${this.service("Wyoming ASR", t("Speech recognition", "语音识别"), asr.connected === true || asr.status === "ok" ? "ok" : "muted", String(asr.status || object(states.asr_metrics).state || t("No observation", "暂无观测")), "mdi:waveform")}
            ${this.service("Edge TTS", t("Speech synthesis", "语音合成"), tts.status === "ok" ? "ok" : "muted", String(tts.status || t("Measured per reply", "按次记录合成")), "mdi:volume-high")}
            ${this.service("Kukui · Phosh", t("Capture & playback", "收音与播放"), live.connected ? "ok" : "muted", live.connected ? t("Observed online", "观测在线") : t("Unknown", "未知"), "mdi:tablet-dashboard")}
          </div>
        </section>
      </div>
      ${this.disclosure("diagnostics", model?.diagnosticsLabel || t("System observations", "系统观测详情"))}
      ${this.disclosure("memory", model?.memoryLabel || t("Conversation memory", "对话记忆"))}
    `;
  }
  private service(
    name: string,
    hint: string,
    tone: string,
    status: string,
    icon: string,
  ) {
    return html`<article class="service">
      <ha-icon icon=${icon}></ha-icon>
      <div><strong>${name}</strong><small>${hint}</small></div>
      <span class=${"chip " + tone}>${status}</span>
    </article>`;
  }
  private disclosure(id: "diagnostics" | "memory", label: string) {
    return html`<details
      class="surface disclosure"
      .open=${this.openSections.includes(id)}
      @toggle=${(event: Event) => {
        const open = (event.currentTarget as HTMLDetailsElement).open;
        this.dispatchEvent(
          new CustomEvent("harness-overview-disclosure-toggle", {
            bubbles: true,
            composed: true,
            detail: { id, open },
          }),
        );
      }}
    >
      <summary>${label}</summary>
      <slot name=${id}></slot>
    </details>`;
  }
  private navigate(destination: HarnessOverviewDestination) {
    this.dispatchEvent(
      new CustomEvent("harness-overview-navigate", {
        bubbles: true,
        composed: true,
        detail: { destination },
      }),
    );
  }
  static styles = [
    harnessFoundationStyles,
    harnessButtonStyles,
    harnessSurfaceStyles,
    css`
      :host {
        display: grid;
        gap: 18px;
      }
      .intro {
        margin-bottom: 6px;
      }
      .dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: currentColor;
      }
      .bento {
        display: grid;
        grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
        gap: 18px;
      }
      .pipeline {
        padding: 26px 30px 22px;
        background:
          radial-gradient(
            ellipse at 45% 55%,
            color-mix(in srgb, var(--vh-accent) 9%, transparent),
            transparent 65%
          ),
          var(--vh-surface);
      }
      .pulse-scene {
        height: 126px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 30px;
      }
      .orb {
        width: 72px;
        height: 72px;
        border-radius: 50%;
        display: grid;
        place-items: center;
        background: var(--vh-soft);
        box-shadow: 0 0 0 14px
          color-mix(in srgb, var(--vh-accent) 3%, transparent);
        color: var(--vh-accent);
      }
      .orb ha-icon {
        --mdc-icon-size: 28px;
        width: 28px;
        height: 28px;
      }
      .wave {
        height: 56px;
        display: flex;
        align-items: center;
        gap: 5px;
        color: var(--vh-accent);
        opacity: 0.45;
      }
      .wave i {
        width: 3px;
        height: var(--h);
        border-radius: 4px;
        background: currentColor;
      }
      [data-active="true"] .orb {
        animation: breathe 2.6s ease-in-out infinite;
      }
      [data-active="true"] .wave i {
        animation: sound 900ms ease-in-out infinite alternate;
        animation-delay: calc(var(--i) * -80ms);
      }
      .pipeline-nodes {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
      }
      .pipeline-nodes span {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        font-size: 12px;
        color: var(--vh-muted);
      }
      .pipeline-nodes ha-icon {
        --mdc-icon-size: 16px;
        width: 16px;
        height: 16px;
      }
      .pipeline-note {
        margin-top: 20px;
        font-size: 12px;
        color: var(--vh-muted);
      }
      .focus {
        display: flex;
        flex-direction: column;
        gap: 14px;
        background: linear-gradient(
          135deg,
          color-mix(in srgb, #d2ae79 9%, var(--vh-surface)),
          var(--vh-surface)
        );
      }
      .focus .section-head {
        margin-bottom: 4px;
        color: var(--vh-accent);
      }
      .focus h3 {
        font-size: 22px;
        line-height: 1.4;
        letter-spacing: -0.025em;
      }
      .focus-actions {
        display: grid;
        gap: 6px;
        margin-top: auto;
        padding-top: 6px;
      }
      .focus-actions button {
        justify-content: space-between;
        background: transparent;
      }
      .metrics {
        grid-column: 1 / -1;
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 18px;
      }
      .services {
        grid-column: 1 / -1;
      }
      .service-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 16px;
      }
      .service {
        display: flex;
        flex-wrap: wrap;
        align-content: start;
        gap: 12px;
        padding: 12px 18px;
        border-left: 1px solid var(--vh-line);
      }
      .service:first-child {
        border-left: 0;
        padding-left: 0;
      }
      .service > ha-icon {
        color: var(--vh-accent);
        margin-top: 2px;
      }
      .service > div {
        display: grid;
        gap: 3px;
        min-width: 0;
      }
      .service strong {
        font-size: 14px;
      }
      .service small {
        color: var(--vh-muted);
        font-size: 12px;
      }
      .service .chip {
        max-width: 100%;
        white-space: normal;
        overflow-wrap: anywhere;
      }
      .disclosure {
        padding: 0 24px;
      }
      .disclosure summary {
        padding: 18px 0;
        font-weight: 550;
      }
      ::slotted(*) {
        display: block;
        padding-bottom: 20px;
      }
      @keyframes breathe {
        50% {
          transform: scale(1.05);
          opacity: 0.8;
        }
      }
      @keyframes sound {
        to {
          transform: scaleY(0.3);
        }
      }
      @media (max-width: 1000px) {
        .bento {
          grid-template-columns: 1fr;
        }
        .focus {
          display: none;
        }
        .service-grid {
          grid-template-columns: 1fr 1fr;
        }
        .service:nth-child(3) {
          border: 0;
          padding-left: 0;
        }
      }
      @media (max-width: 600px) {
        .metrics {
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }
        .bento {
          gap: 12px;
        }
        .pipeline {
          padding: 22px 18px;
        }
        .pipeline-nodes span {
          flex-direction: column;
          gap: 6px;
          font-size: 11px;
        }
        .pulse-scene {
          height: 110px;
        }
        .service {
          padding: 8px 0;
          border: 0;
        }
        .service-grid {
          gap: 18px;
        }
        .intro > .chip {
          margin-top: 0;
        }
      }
    `,
  ];
}
if (!customElements.get("voice-harness-overview"))
  customElements.define("voice-harness-overview", VoiceHarnessOverview);
declare global {
  interface HTMLElementTagNameMap {
    "voice-harness-overview": VoiceHarnessOverview;
  }
}
