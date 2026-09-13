import { css, html, LitElement, nothing } from "lit";
import { harnessButtonStyles, harnessFoundationStyles, harnessSurfaceStyles } from "./voice-harness-styles";
import {
  conversationFacts, latestConversation, livePipeline, object, observedMetrics, records,
  type EvidenceRecord,
} from "./voice-harness-live-model";
import "./voice-harness-stat";

export class VoiceHarnessOverview extends LitElement {
  static properties = {
    entries: { attribute: false }, satellite: { attribute: false }, language: {},
  };
  declare entries: EvidenceRecord[];
  declare satellite: EvidenceRecord;
  declare language: string;
  constructor() {
    super();
    this.entries = [];
    this.satellite = {};
    this.language = "en";
  }
  private text(en: string, zh: string) {
    return this.language.startsWith("zh") ? zh : en;
  }
  render() {
    const t = this.text.bind(this);
    const runs = this.entries.flatMap((entry) => records(object(entry.traces).records));
    const active = this.entries.flatMap((entry) => records(entry.voice_runs).filter((run) => run.status === "running"));
    const latest = latestConversation([...active, ...runs]);
    const facts = latest ? conversationFacts(latest) : null;
    const live = livePipeline(object(this.satellite.states), object(object(this.entries[0]?.feedback).latest_display));
    const stateLabel = live.phase === "paused" ? t("Do not disturb", "免打扰中")
      : live.active ? t("Conversation in progress", "正在对话")
      : live.phase === "standby" ? t("Standing by", "语音待机")
      : live.phase === "offline" ? t("Voice connection interrupted", "语音连接中断")
      : t("Capture state unknown", "收音状态未知");
    const evidence = facts?.evidence || "unknown";
    const evidenceLabel = {
      observed: t("State read from observations", "已有观测依据"),
      policy_saved: t("Comfort target saved", "舒适目标已保存"),
      policy_requested: t("Comfort target submitted", "舒适目标已提交"),
      policy_suppressed: t("Target saved · away policy takes priority", "目标已保存 · 离家策略优先"),
      sent: t("Request sent · confirmation missing", "请求已发送 · 设备确认暂缺"),
      accepted: t("Request accepted · device unconfirmed", "请求已受理 · 设备确认暂缺"),
      confirmed: t("Device reported the requested state", "设备已回报请求的状态"),
      not_confirmed: t("Device did not confirm the request", "设备尚未确认这次请求"),
      unconfirmed: t("Device response unconfirmed", "尚无设备响应的确认"),
      reply: t("Reply generated", "已生成回复"),
      failed: t("This request did not complete", "这次请求未完成"),
      partial: t("Only part of the request was sent", "请求仅部分发出"),
      clarification: t("One detail to clarify", "还需要补充一点信息"),
      cancelled: t("Conversation stopped", "本次对话已停止"),
      running: t("Processing your request", "正在处理这句话"),
      unknown: t("Awaiting evidence", "等待结果依据"),
    }[evidence];
    const guidance = !latest ? t("Your next conversation will appear here.", "下一次对话会记录在这里。")
      : evidence === "clarification" ? t("Answer the question above to continue.", "回答上面的澄清问题即可继续。")
      : evidence === "policy_saved" ? t("The room will follow its comfort policy. Current temperature still comes from its sensors.", "接下来由房间按舒适策略调节，当前室温仍以传感器观测为准。")
      : evidence === "policy_requested" ? t("The request was sent. The updated room target has not been observed yet.", "请求已提交，暂未读到更新后的房间目标。")
      : evidence === "policy_suppressed" ? t("Your target is saved. The room currently follows its away policy.", "你的目标已保留，房间目前按离家策略运行。")
      : ["failed", "partial"].includes(evidence) ? t("The reply explains what is missing. Details are available in the record.", "可从回复了解未完成的原因，在记录中查看详情。")
      : ["sent", "accepted", "unconfirmed", "not_confirmed"].includes(evidence) ? t("The device response remains unconfirmed. The record has the available evidence.", "设备响应仍待确认，可在记录中查看已有反馈。")
      : evidence === "running" ? t("Waiting for the reply.", "正在等待回复。")
      : evidence === "unknown" ? t("There is not enough evidence to judge this request yet.", "目前还没有足够依据判断这次请求的结果。")
      : t("Nothing else is needed for this conversation.", "这次对话无需补充。");
    const timestamp = String(latest?.created_at || latest?.started_at || "");
    const userText = String(latest?.user_text || object(latest?.input).text || "");
    return html`
      <div class="section-head intro">
        <div><span class="eyebrow">${t("VOICE & SPACE", "语音与空间")}</span>
          <h2>${t("Your last conversation", "最近的对话")}</h2>
          <p class="muted">${t("What was understood, what happened, and what needs you.", "听懂了什么，实际发生了什么，是否需要你。")}</p>
        </div>
        <span class="chip" role="status"><span class="dot" data-active=${String(live.active)}></span>${stateLabel}</span>
      </div>
      <div class="conversation-grid">
        <section class="surface conversation" aria-label=${t("Understood intent", "理解的意图")}>
          <div class="section-head"><span class="eyebrow">${t("YOU SAID", "刚才那句话")}</span>
            ${Number.isFinite(Date.parse(timestamp)) ? html`<time datetime=${timestamp}>${new Date(timestamp).toLocaleString(this.language, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</time>` : nothing}
          </div>
          <h3 class="utterance">${userText || t("No conversation recorded yet.", "还没有对话记录。")}</h3>
          ${facts?.intent && facts.intent !== userText ? html`<p class="resolved"><span>${t("Understood as", "理解为")}</span>${facts.intent}</p>` : nothing}
          <div class="reply"><span class="eyebrow">${t("THE REPLY", "系统的回应")}</span>
            <p>${facts?.reply || (latest ? t("The reply has not been recorded yet.", "暂未记录到回复。") : t("Speak as you normally would.", "像平常一样开口就好。"))}</p>
          </div>
          <button class="quiet" @click=${() => this.navigate("runs")}>${t("Conversation records", "查看对话记录")} <ha-icon icon="mdi:arrow-top-right"></ha-icon></button>
        </section>
        <section class="surface reality" aria-label=${t("Result and next step", "结果与下一步")}>
          <span class="eyebrow">${t("WHAT HAPPENED", "实际结果")}</span>
          <div class="evidence" data-tone=${evidence === "failed" ? "bad" : ["observed", "confirmed", "policy_saved"].includes(evidence) ? "ok" : "muted"}>
            <ha-icon icon=${evidence === "confirmed" ? "mdi:check-circle-outline" : evidence === "observed" ? "mdi:thermometer" : evidence === "failed" ? "mdi:alert-circle-outline" : "mdi:message-processing-outline"}></ha-icon>
            <h3>${latest ? evidenceLabel : t("No result yet", "暂无结果")}</h3>
          </div>
          ${facts?.sources.length ? html`<p class="source">${t("Source at the time of the reply: ", "回复时的来源：")}${facts.sources.join(" · ")}</p>` : nothing}
          ${evidence === "reply" ? html`<p class="source">${t("This record contains a text reply. Speaker playback is recorded separately.", "这里记录了文字回复，扬声器播放需要独立的播放记录。")}</p>` : nothing}
          <div class="next-step"><span class="eyebrow">${t("DOES THIS NEED YOU?", "需要你做什么")}</span><p>${guidance}</p></div>
          ${live.phase === "paused" || live.phase === "offline" ? html`<button class="quiet" @click=${() => this.navigate("settings")}>${t("Voice settings", "语音设置")} <ha-icon icon="mdi:arrow-top-right"></ha-icon></button>` : nothing}
        </section>
      </div>
      <details class="surface diagnostics">
        <summary>${t("System details", "系统详情")}<span>${t("Measurements, connections and diagnostics", "测量、连接与诊断")}</span></summary>
        ${this.diagnostics(runs)}
        <slot name="diagnostics"></slot>
        <details class="memory"><summary>${t("Conversation memory", "对话记忆")}</summary><slot name="memory"></slot></details>
      </details>
    `;
  }
  private diagnostics(runs: EvidenceRecord[]) {
    const t = this.text.bind(this);
    const metrics = observedMetrics(runs);
    const snapshot = object(this.satellite.diagnostic_snapshot);
    const wake = records(snapshot.event_stream).filter((event) => /wake/.test(String(event.type))).at(-1);
    const wakeTime = wake?.timestamp || object(snapshot.wake).last_detected_at;
    const format = (value: number | null, suffix: string) => value === null ? "—" : new Intl.NumberFormat(this.language, { maximumFractionDigits: suffix === "ms" ? 0 : 1 }).format(value) + suffix;
    const loaded = this.entries.some((entry) => entry.state === "loaded");
    return html`
      <div class="metrics">
        <voice-harness-stat .label=${t("Median response", "响应中位数")} .value=${format(metrics.medianMs, "ms")} .values=${metrics.latencies} .hint=${t("Retained live conversations", "已保留的实际对话")} icon="mdi:timer-outline"></voice-harness-stat>
        <voice-harness-stat .label=${t("Replies completed", "回答完成率")} .value=${format(metrics.successRate, "%")} .values=${metrics.outcomes} .hint=${t("Reply outcome only", "仅描述回答结果")} icon="mdi:check-circle-outline"></voice-harness-stat>
        <voice-harness-stat .label=${t("Error rate", "错误率")} .value=${format(metrics.errorRate, "%")} .values=${metrics.errors} .hint=${String(metrics.count) + t(" completed conversations", " 次已结束对话")} icon="mdi:pulse"></voice-harness-stat>
        <voice-harness-stat .label=${t("Last wake", "最近唤醒")} .value=${typeof wakeTime === "string" && Number.isFinite(Date.parse(wakeTime)) ? new Date(wakeTime).toLocaleTimeString(this.language, { hour: "2-digit", minute: "2-digit" }) : "—"} .hint=${t("Satellite timestamp", "卫星时间戳")} icon="mdi:microphone-outline"></voice-harness-stat>
      </div>
      <p class="system-state">${loaded ? t("Gateway loaded", "网关已加载") : t("Gateway state unknown", "网关状态未知")} · ${t("Connection checks and missing measurements follow below.", "连接检查与缺失测量见下方。")}</p>
    `;
  }
  private navigate(destination: "runs" | "settings") {
    this.dispatchEvent(new CustomEvent("harness-overview-navigate", { bubbles: true, composed: true, detail: { destination } }));
  }
  static styles = [harnessFoundationStyles, harnessButtonStyles, harnessSurfaceStyles, css`
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
if (!customElements.get("voice-harness-overview")) customElements.define("voice-harness-overview", VoiceHarnessOverview);
declare global { interface HTMLElementTagNameMap { "voice-harness-overview": VoiceHarnessOverview; } }
