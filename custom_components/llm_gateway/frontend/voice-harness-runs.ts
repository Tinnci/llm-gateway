import { css, html, LitElement, nothing } from "lit";
import type { PropertyValues } from "lit";
import { repeat } from "lit/directives/repeat.js";
import {
  object,
  records,
  idOf,
  speechOf,
  pipelineStages,
  pcmWave,
  pcmSampleRates,
  measurement,
  supportsActionReplay,
  type EvidenceRecord,
} from "./voice-harness-live-model";
import { runOutcome, runTone } from "./voice-harness-model";
import {
  harnessFoundationStyles,
  harnessButtonStyles,
  harnessSurfaceStyles,
} from "./voice-harness-styles";
import "./voice-harness-replay-inspector";

type RunItem = { entryId: string; record: EvidenceRecord };
type Filter = "all" | "answered" | "warning" | "failed" | "slow";
const stageNames = {
  wake: ["Wake", "唤醒"],
  asr: ["Recognition", "识别"],
  llm: ["Gateway", "网关"],
  tts: ["Synthesis", "合成"],
  playback: ["Playback", "播放"],
  follow_up: ["Follow-up", "追问"],
};

export class VoiceHarnessRuns extends LitElement {
  static properties = {
    entries: { attribute: false },
    language: {},
    loadDetail: { attribute: false },
    replay: { attribute: false },
    filter: { state: true },
    query: { state: true },
    selected: { state: true },
    selection: { state: true },
    detailTab: { state: true },
    error: { state: true },
    loading: { state: true },
    audioUrl: { state: true },
    compareOpen: { state: true },
  };
  declare entries: EvidenceRecord[];
  declare language: string;
  declare loadDetail?: (
    entryId: string,
    runId: string,
  ) => Promise<EvidenceRecord>;
  declare replay?: (
    entryId: string,
    runId: string,
  ) => Promise<EvidenceRecord | null>;
  declare private filter: Filter;
  declare private query: string;
  declare private selected: RunItem | null;
  declare private selection: RunItem[];
  private details = new Map<string, EvidenceRecord>();
  declare private detailTab: string;
  declare private error: string;
  declare private loading: boolean;
  declare private audioUrl: string;
  private audioName = "";
  declare private compareOpen: boolean;
  private audioRate = 16000;
  private audioChannels = 1;
  private opener?: HTMLElement;
  constructor() {
    super();
    this.entries = [];
    this.language = "en";
    this.filter = "all";
    this.query = "";
    this.selected = null;
    this.selection = [];
    this.detailTab = "conversation";
    this.error = "";
    this.loading = false;
    this.audioUrl = "";
    this.compareOpen = false;
  }
  private text(en: string, zh: string) {
    return this.language.startsWith("zh") ? zh : en;
  }
  private get items(): RunItem[] {
    return this.entries.flatMap((entry) =>
      records(object(entry.traces).records).map((record) => ({
        entryId: String(entry.entry_id),
        record,
      })),
    );
  }
  private key(item: RunItem) {
    return item.entryId + ":" + idOf(item.record);
  }
  private current(item: RunItem) {
    return this.details.get(this.key(item)) || item.record;
  }
  private label(record: EvidenceRecord) {
    const status = runOutcome(record);
    return {
      answered: this.text("Answered", "已回答"),
      failed: this.text("Failed", "失败"),
      clarification: this.text("Clarification", "待澄清"),
      cancelled: this.text("Cancelled", "已取消"),
      running: this.text("In progress", "进行中"),
      unknown: this.text("Unknown", "未知"),
    }[status];
  }
  private filtered(item: RunItem) {
    const record = item.record;
    const outcome = runOutcome(record);
    const query = this.query.trim().toLocaleLowerCase();
    return (
      (!query ||
        [
          record.user_text,
          speechOf(record),
          object(record.route).model,
          idOf(record),
        ]
          .join(" ")
          .toLocaleLowerCase()
          .includes(query)) &&
      (this.filter === "all" ||
        this.filter === outcome ||
        (this.filter === "warning" &&
          ["clarification", "cancelled", "unknown", "running"].includes(
            outcome,
          )) ||
        (this.filter === "slow" &&
          (measurement(record.latency_ms) ?? -1) > 3000))
    );
  }
  private time(value: unknown) {
    const date = new Date(String(value));
    return Number.isFinite(date.getTime())
      ? date.toLocaleString(this.language, {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "—";
  }
  render() {
    const t = this.text.bind(this);
    const items = this.items.filter((item) => this.filtered(item));
    const selected = this.selected ? this.current(this.selected) : null;
    return html`
      <div class="section-head">
        <div>
          <span class="eyebrow">VOICE HARNESS / ${t("RUNS", "运行记录")}</span>
          <h2>
            ${t("Every conversation has a story.", "每一段对话，都有迹可循。")}
          </h2>
          <p class="muted">
            ${t("Follow the timing, the answer and the evidence behind it.", "沿着时间线，看见回应，也看见回应背后的证据。")}
          </p>
        </div>
        <span class="chip"
          >${this.items.length} ${t("retained runs", "条保留记录")}</span
        >
      </div>
      <section class="surface run-surface">
        <div class="toolbar">
          <div class="filters" aria-label=${t("Filter runs", "筛选运行记录")}>
            ${(
              [
                ["all", t("All", "全部")],
                ["answered", t("Answered", "已回答")],
                ["warning", t("Attention", "留意")],
                ["failed", t("Failed", "失败")],
                ["slow", ">3s"],
              ] as const
            ).map(
              ([id, label]) =>
                html`<button
                  class="filter"
                  aria-pressed=${String(this.filter === id)}
                  @click=${() => {
                this.filter = id;
              }}
                >
                  ${label}
                </button>`,
            )}
          </div>
          <label class="search"
            ><span class="sr-only"
              >${t("Search runs", "搜索对话、模型或 ID")}</span
            ><input
              type="search"
              .value=${this.query}
              @input=${(event: Event) => {
                this.query = (event.target as HTMLInputElement).value;
              }}
              placeholder=${t("Search conversations, models…", "搜索对话、模型…")}
          /></label>
        </div>
        ${
          this.selection.length
            ? html`<div class="compare-bar">
                <span
                  >${this.selection.length}/2 ${t("selected", "条已选")}</span
                ><button
                  class="primary"
                  ?disabled=${this.selection.length !== 2}
                  @click=${() => this.openComparison()}
                >
                  ${t("Compare replies", "对比模型回答")}</button
                ><button
                  class="quiet"
                  @click=${() => {
                    this.selection = [];
                  }}
                >
                  ${t("Clear", "清除")}
                </button>
              </div>`
            : nothing
        }
        <div class="list-head" aria-hidden="true">
          <span>${t("Conversation", "对话")}</span
          ><span>${t("Route / duration", "路由 / 耗时")}</span
          ><span>${t("Outcome", "结果")}</span
          ><span>${t("Compare", "对比")}</span>
        </div>
        <div class="run-list">
          ${repeat(
            items,
            (item) => this.key(item),
            (item) => html`
              <article class="run-row">
                <button
                  class="run-open"
                  @click=${(event: Event) => this.open(item, event.currentTarget as HTMLElement)}
                >
                  <span class=${"status-dot " + runTone(item.record)}></span
                  ><span class="identity"
                    ><strong
                      >${String(item.record.user_text || idOf(item.record))}</strong
                    ><small
                      >${this.time(item.record.created_at)}${object(item.record.lineage).mode === "dry_run" ? " · " + t("Dry-run replay", "模拟重放") : ""}</small
                    ><span class="excerpt"
                      >${speechOf(item.record) || t("No answer retained", "未保留回答")}</span
                    ></span
                  >
                  <span class="run-facts"
                    ><strong
                      >${String(object(item.record.route).kind || item.record.route || "—")}</strong
                    ><small
                      >${measurement(item.record.latency_ms) === null ? "—" : Number(item.record.latency_ms).toLocaleString(this.language) + " ms"}</small
                    ></span
                  >
                  <span class=${"chip " + runTone(item.record)}
                    >${this.label(item.record)}</span
                  >
                </button>
                <button
                  class="compare-pick quiet"
                  aria-label=${t("Select for comparison: ", "选择对比：") + String(item.record.user_text || idOf(item.record))}
                  aria-pressed=${String(this.selection.some((value) => this.key(value) === this.key(item)))}
                  @click=${() => this.toggleCompare(item)}
                >
                  <ha-icon icon="mdi:compare-horizontal"></ha-icon
                  ><span class="mobile-compare">${t("Compare", "对比")}</span>
                </button>
              </article>
            `,
          )}
        </div>
        ${
          !items.length
            ? html`<div class="empty">
                <ha-icon icon="mdi:message-outline"></ha-icon>
                <h3>${t("A quiet moment", "这里暂时很安静")}</h3>
                <p>
                  ${this.query || this.filter !== "all" ? t("No runs match these filters.", "没有符合当前筛选的记录。") : t("Retained voice runs appear here. Enable diagnostic traces in Settings to capture the next conversation.", "保留的语音运行会出现在这里。可在设置中开启诊断记录，观察下一段对话。")}
                </p>
              </div>`
            : nothing
        }
      </section>
      <dialog
        aria-labelledby="inspector-title"
        @cancel=${() => this.close()}
        @click=${(event: MouseEvent) => {
          if (event.target === event.currentTarget) {
            const bounds = (
              event.currentTarget as HTMLElement
            ).getBoundingClientRect();
            if (event.clientX < bounds.left || event.clientX > bounds.right)
              this.close();
          }
        }}
      >
        <header class="drawer-header">
          <div>
            <span class="eyebrow"
              >${this.compareOpen ? "REPLAY DIFF" : "TRACE INSPECTOR"}</span
            >
            <h3 id="inspector-title">
              ${this.compareOpen ? t("Two perspectives, side by side", "两次回应，一目了然") : t("Inside the conversation", "走进这段对话")}
            </h3>
          </div>
          <button
            class="quiet"
            aria-label=${t("Close inspector", "关闭检查抽屉")}
            @click=${() => this.close()}
          >
            ✕
          </button>
        </header>
        <div class="drawer-body">
          ${this.error ? html`<p class="error" role="alert">${this.error}</p>` : nothing}
          ${this.loading ? html`<p role="status" class="muted">${t("Loading observed evidence…", "正在读取观测证据…")}</p>` : nothing}
          ${this.compareOpen ? this.comparison() : selected ? this.detail(selected) : nothing}
        </div>
      </dialog>
    `;
  }
  private detail(record: EvidenceRecord) {
    const t = this.text.bind(this);
    const usage = object(record.usage);
    return html`
      <div class="detail-summary">
        <span class=${"chip " + runTone(record)}>${this.label(record)}</span
        ><span class="muted">${this.time(record.created_at)}</span
        ><span class="chip">${String(object(record.route).model || "—")}</span>
      </div>
      <h2 class="question">
        ${String(record.user_text || object(record.input).text || "—")}
      </h2>
      ${this.waterfall(record)}
      <nav
        class="detail-tabs"
        aria-label=${t("Run detail sections", "运行详情分组")}
      >
        ${[
          ["conversation", t("Conversation", "对话")],
          ["evidence", t("Evidence", "证据")],
          ["audio", t("Audio", "音频")],
          ["json", "JSON"],
        ].map(
          ([id, label]) =>
            html`<button
              aria-pressed=${String(this.detailTab === id)}
              @click=${() => {
              this.detailTab = id;
            }}
            >
              ${label}
            </button>`,
        )}
      </nav>
      <section
        ?hidden=${this.detailTab !== "conversation"}
        class="conversation"
      >
        <div class="bubble user">
          <small>${t("You", "你")}</small>
          <p>${String(record.user_text || "—")}</p>
        </div>
        <div class="bubble assistant">
          <small>${t("Assistant", "助手")}</small>
          <p>${speechOf(record) || t("No answer retained", "未保留回答")}</p>
        </div>
        <div class="usage">
          ${[
            [
              t("Input tokens", "输入 Token"),
              usage.input_tokens ?? usage.prompt_tokens,
            ],
            [
              t("Output tokens", "输出 Token"),
              usage.output_tokens ?? usage.completion_tokens,
            ],
            [t("Cached tokens", "缓存 Token"), usage.cached_input_tokens],
          ].map(
            ([label, value]) =>
              html`<div>
                <small>${label}</small
                ><strong
                  >${measurement(value) === null ? "—" : Number(value).toLocaleString(this.language)}</strong
                >
              </div>`,
          )}
        </div>
        <button
          class="primary"
          ?disabled=${this.loading || !this.replay || !supportsActionReplay(record)}
          @click=${() => this.replaySelected()}
        >
          ↻ ${t("Replay action proposal", "重放动作提案")}
        </button>
        <p class="muted replay-note">
          ${supportsActionReplay(record) ? t("Replay evaluates the recorded local action. Device actions remain proposals.", "重放评估已记录的本地动作，设备动作保留为提案。") : t("This record has no replayable local action. Use the Test panel to preview a new model response.", "此记录没有可重放的本地动作，可在测试面板演练模型回答。")}
        </p>
      </section>
      <section ?hidden=${this.detailTab !== "evidence"} class="evidence">
        <p class="muted">
          ${t("Dispatch, acceptance and physical confirmation remain separate facts.", "派发、接收和物理确认，是彼此独立的事实。")}
        </p>
        ${
          this.detailTab === "evidence"
            ? html`
                ${[...records(record.actions), ...records(record.proposed_actions)].map((action) => html`<article class="surface"><strong>${String(action.entity_id || action.domain || action.service || "Action")}</strong>${this.jsonTree(action, "Actuation evidence")}</article>`)}
                ${this.jsonTree(record.outcome_verdict || record.harness_loop || object(record.route).outcome_verdict || {}, t("Outcome", "对话结果"))}
                ${this.jsonTree(record.tools || [], t("Tool calls", "工具调用"))}
                ${this.jsonTree(record.errors || [], t("Errors", "错误"))}
                ${this.jsonTree(record.event_stream || record.timeline || [], t("Observed events", "观测事件"))}
              `
            : nothing
        }
      </section>
      <section ?hidden=${this.detailTab !== "audio"} class="audio-preview">
        <h3>${t("Listen in context", "在语境中试听")}</h3>
        <p class="muted">
          ${t("This trace does not retain microphone recordings. Load a local WAV or 16-bit PCM sample to audition; it stays in this browser.", "此记录不保存麦克风录音。可载入本地 WAV 或 16 位 PCM 样本试听，文件仅留在浏览器。")}
        </p>
        <div class="audio-format">
          <label
            >${t("PCM sample rate", "PCM 采样率")}<select
              @change=${(event: Event) => {
                this.audioRate = Number(
                  (event.target as HTMLSelectElement).value,
                );
                this.clearAudio();
              }}
            >
              ${pcmSampleRates.map((rate) => html`<option .selected=${rate === this.audioRate} value=${rate}>${rate} Hz</option>`)}
            </select></label
          ><label
            >${t("Channels", "声道")}<select
              @change=${(event: Event) => {
                this.audioChannels = Number(
                  (event.target as HTMLSelectElement).value,
                );
                this.clearAudio();
              }}
            >
              <option value="1">${t("Mono", "单声道")}</option>
              <option value="2">${t("Stereo", "双声道")}</option>
            </select></label
          >
        </div>
        <label
          >${t("Local audio sample", "本地音频样本")}<input
            type="file"
            accept=".wav,.pcm,audio/wav"
            @change=${(event: Event) => this.loadAudio((event.target as HTMLInputElement).files?.[0])}
        /></label>
        ${this.audioUrl ? html`<span class="muted">${this.audioName}</span><audio controls preload="metadata" src=${this.audioUrl}></audio>` : nothing}
      </section>
      <section ?hidden=${this.detailTab !== "json"}>
        ${this.detailTab === "json" ? this.jsonTree(record, t("Complete run", "完整运行记录")) : nothing}
      </section>
    `;
  }
  private waterfall(record: EvidenceRecord) {
    const t = this.text.bind(this);
    const stages = pipelineStages(record);
    const starts = stages.flatMap((stage) =>
      stage.startMs === null ? [] : [stage.startMs],
    );
    const origin = Math.min(0, ...starts);
    const end = Math.max(
      1,
      ...stages.map(
        (stage) => (stage.startMs ?? origin) + (stage.durationMs ?? 0),
      ),
    );
    const span = end - origin;
    return html`<section
      class="waterfall"
      aria-label=${t("Observed pipeline timing", "观测链路时序")}
    >
      <div class="timing-head">
        <span>${t("Pipeline timing", "链路时序")}</span
        ><small
          >${t("Missing spans stay unmeasured", "缺失阶段保留为未测量")}</small
        >
      </div>
      ${stages.map(
        (stage) =>
          html`<details
            class="stage"
            style=${"--stage-color:var(--stage-" + stage.id + ")"}
          >
            <summary>
              <span
                >${stageNames[stage.id][this.language.startsWith("zh") ? 1 : 0]}</span
              ><span class="track"
                >${stage.events.length ? html`<i class=${stage.startMs === null ? "unaligned" : stage.durationMs === null ? "point" : ""} style=${"left:" + (stage.startMs === null ? 0 : Math.max(0, ((stage.startMs - origin) / span) * 100)) + "%;width:" + (stage.durationMs === null || stage.startMs === null ? 2 : Math.max(1, Math.min(100, (stage.durationMs / span) * 100))) + "%"}></i>` : html`<em>—</em>`}</span
              ><small
                >${stage.durationMs === null ? t("Unmeasured", "未测量") : Math.round(stage.durationMs) + " ms"}</small
              >
            </summary>
            <div class="stage-detail">
              <span class="chip">${stage.status}</span
              >${stage.startMs === null && stage.events.length ? html`<p class="muted">${t("No shared time offset was recorded.", "未记录统一时间偏移。")}</p>` : nothing}${stage.events.length ? stage.events.map((event) => this.jsonTree(event, String(event.type || event.stage || event.event_type || "Event"))) : html`<p class="muted">${t("No stage evidence retained", "未保留该阶段证据")}</p>`}
            </div>
          </details>`,
      )}
    </section>`;
  }
  private jsonTree(value: unknown, label: string, depth = 0): unknown {
    if (value && typeof value === "object") {
      const entries = Object.entries(value);
      return html`<details class="json-tree" ?open=${depth === 0}>
        <summary>
          <strong>${label}</strong
          ><span class="muted"
            >${Array.isArray(value) ? "[" + entries.length + "]" : "{" + entries.length + "}"}</span
          >
        </summary>
        ${depth >= 6 ? html`<pre>${JSON.stringify(value, null, 2)}</pre>` : html`<div class="json-children">${entries.map(([key, child]) => this.jsonTree(child, key, depth + 1))}</div>`}
      </details>`;
    }
    return html`<div class="json-value">
      <span>${label}</span
      ><code>${typeof value === "string" ? value : JSON.stringify(value)}</code>
    </div>`;
  }
  private toggleCompare(item: RunItem) {
    const found = this.selection.some(
      (value) => this.key(value) === this.key(item),
    );
    this.selection = found
      ? this.selection.filter((value) => this.key(value) !== this.key(item))
      : [...this.selection.slice(-1), item];
  }
  private async fetchDetail(item: RunItem) {
    const detail = this.details.get(this.key(item));
    if (detail || !this.loadDetail) return detail || item.record;
    const loaded = await this.loadDetail(item.entryId, idOf(item.record));
    this.details.set(this.key(item), loaded);
    this.requestUpdate();
    return loaded;
  }
  private async open(item: RunItem, opener?: HTMLElement) {
    this.opener = opener;
    this.selected = item;
    this.compareOpen = false;
    this.detailTab = "conversation";
    this.error = "";
    this.clearAudio();
    await this.updateComplete;
    this.showDialog();
    this.loading = true;
    try {
      await this.fetchDetail(item);
    } catch (error) {
      this.error = String(error instanceof Error ? error.message : error);
    } finally {
      this.loading = false;
    }
  }
  private showDialog() {
    const dialog = this.renderRoot.querySelector("dialog");
    if (dialog && !dialog.open) dialog.showModal();
  }
  private close() {
    this.renderRoot.querySelector("dialog")?.close();
    this.clearAudio();
    this.selected = null;
    this.compareOpen = false;
    this.opener?.focus();
  }
  private async openComparison() {
    if (this.selection.length !== 2) return;
    this.opener =
      this.renderRoot.querySelector<HTMLElement>(".compare-bar .primary") ||
      undefined;
    this.error = "";
    this.compareOpen = true;
    this.loading = true;
    await this.updateComplete;
    this.showDialog();
    try {
      await Promise.all(this.selection.map((item) => this.fetchDetail(item)));
    } catch (error) {
      this.error = String(error instanceof Error ? error.message : error);
    } finally {
      this.loading = false;
    }
  }
  private comparison() {
    if (this.selection.length !== 2) return nothing;
    const [left, right] = this.selection;
    return html`<voice-harness-replay-inspector
      .language=${this.language}
      .pair=${{ source: this.current(left), fork: this.current(right), sourceId: idOf(left.record), forkId: idOf(right.record) }}
      .labels=${{ route: this.text("Model & route", "模型与路由"), actions: this.text("Proposed actions", "动作提案"), speech: this.text("Reply", "回答"), events: this.text("Events", "事件") }}
    ></voice-harness-replay-inspector>`;
  }
  private async replaySelected() {
    if (!this.selected || !this.replay) return;
    this.loading = true;
    this.error = "";
    try {
      const source = this.selected;
      const record = await this.replay(source.entryId, idOf(source.record));
      if (record) {
        const fork = { entryId: source.entryId, record };
        this.details.set(this.key(fork), record);
        this.selection = [source, fork];
        this.compareOpen = true;
      }
    } catch (error) {
      this.error = String(error instanceof Error ? error.message : error);
    } finally {
      this.loading = false;
    }
  }
  private clearAudio() {
    this.renderRoot.querySelector("audio")?.pause();
    if (this.audioUrl) URL.revokeObjectURL(this.audioUrl);
    this.audioUrl = "";
  }
  private async loadAudio(file?: File) {
    if (!file) return;
    this.error = "";
    this.clearAudio();
    try {
      const bytes = await file.arrayBuffer();
      const blob = file.name.toLowerCase().endsWith(".pcm")
        ? new Blob(
            [
              pcmWave(
                new Uint8Array(bytes),
                this.audioRate,
                this.audioChannels,
              ),
            ],
            { type: "audio/wav" },
          )
        : new Blob([bytes], { type: "audio/wav" });
      this.audioName = file.name;
      this.audioUrl = URL.createObjectURL(blob);
    } catch (error) {
      this.error = String(error instanceof Error ? error.message : error);
    }
  }
  protected updated(changes: PropertyValues) {
    if (changes.has("detailTab") && this.detailTab !== "audio")
      this.renderRoot.querySelector("audio")?.pause();
  }
  disconnectedCallback() {
    this.clearAudio();
    super.disconnectedCallback();
  }
  static styles = [
    harnessFoundationStyles,
    harnessButtonStyles,
    harnessSurfaceStyles,
    css`
      :host {
        display: block;
        --stage-wake: #c19b55;
        --stage-asr: #4c9c98;
        --stage-llm: #788fca;
        --stage-tts: #a487bb;
        --stage-playback: #659975;
        --stage-follow_up: #c58d73;
      }
      .run-surface {
        padding: 8px 22px;
      }
      .toolbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 14px 0;
      }
      .filters {
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
      }
      .filter {
        border: 0;
        background: transparent;
        padding: 10px 14px;
        border-radius: 999px;
        color: var(--vh-muted);
      }
      [aria-pressed="true"] {
        background: var(--vh-soft);
        color: var(--vh-accent);
      }
      .search {
        max-width: 320px;
        width: 30%;
      }
      .search input {
        background: transparent;
      }
      .list-head {
        padding: 14px 8px;
        border-bottom: 1px solid var(--vh-line);
        display: grid;
        grid-template-columns: minmax(0, 1fr) 140px 100px 65px;
        color: var(--vh-muted);
        font-size: 12px;
      }
      .run-row {
        display: flex;
        align-items: center;
        gap: 10px;
        border-bottom: 1px solid var(--vh-line);
      }
      .run-row:last-child {
        border-bottom: 0;
      }
      .run-open {
        flex: 1;
        display: grid;
        grid-template-columns: 8px minmax(0, 1fr) 140px 100px;
        gap: 14px;
        text-align: left;
        background: transparent;
        border: 0;
        border-radius: 14px;
        padding: 22px 8px;
      }
      .identity {
        min-width: 0;
        display: grid;
        gap: 5px;
      }
      .identity strong {
        font-size: 15px;
        font-weight: 570;
        white-space: nowrap;
        text-overflow: ellipsis;
        overflow: hidden;
      }
      .identity small,
      .run-facts small {
        font-size: 11px;
        color: var(--vh-muted);
        font-weight: 400;
      }
      .excerpt {
        font-size: 13px;
        color: var(--vh-muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-weight: 400;
      }
      .run-facts {
        display: grid;
        gap: 6px;
        font-variant-numeric: tabular-nums;
      }
      .run-facts strong {
        font-size: 13px;
        text-transform: capitalize;
        font-weight: 550;
      }
      .run-open .chip {
        justify-self: start;
      }
      .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: currentColor;
      }
      .compare-pick {
        width: 56px;
        flex-shrink: 0;
      }
      .mobile-compare {
        display: none;
      }
      .compare-bar {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 0;
      }
      .compare-bar > span {
        margin-right: auto;
        color: var(--vh-muted);
      }
      dialog {
        position: fixed;
        inset: 0 0 0 auto;
        width: min(860px, 94vw);
        max-width: 100vw;
        height: 100%;
        max-height: 100%;
        margin: 0;
        border: 0;
        border-left: 1px solid var(--vh-line);
        background: var(--vh-background);
        color: var(--vh-ink);
        padding: 0;
        box-shadow: -24px 0 80px #00000015;
      }
      dialog[open] {
        animation: drawer-in 280ms var(--vh-ease);
      }
      dialog::backdrop {
        background: #14253266;
        backdrop-filter: blur(3px);
      }
      .drawer-header {
        position: sticky;
        top: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 22px 30px;
        background: var(--vh-surface);
        border-bottom: 1px solid var(--vh-line);
        z-index: 2;
      }
      .drawer-header > div {
        display: grid;
        gap: 6px;
      }
      .drawer-body {
        padding: 24px 30px 48px;
      }
      .detail-summary {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
      }
      .question {
        margin: 22px 0;
        font-size: 25px;
        line-height: 1.5;
        overflow-wrap: anywhere;
      }
      .waterfall {
        padding: 18px 20px;
        border-radius: var(--vh-radius-m);
        background: var(--vh-surface);
        border: 1px solid var(--vh-line);
      }
      .timing-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        margin-bottom: 10px;
      }
      .timing-head small {
        font-size: 10px;
        color: var(--vh-muted);
      }
      .stage summary {
        display: grid;
        grid-template-columns: 68px minmax(0, 1fr) 76px;
        align-items: center;
        gap: 12px;
        font-size: 12px;
      }
      .stage summary::marker {
        content: "";
      }
      .stage summary > small {
        text-align: right;
        color: var(--vh-muted);
        font-size: 11px;
      }
      .track {
        height: 18px;
        position: relative;
        border-radius: 5px;
        background: var(--vh-background);
        overflow: hidden;
      }
      .track i {
        position: absolute;
        top: 3px;
        height: 12px;
        min-width: 3px;
        border-radius: 3px;
        background: var(--stage-color);
      }
      .track i.point {
        width: 3px !important;
      }
      .track i.unaligned {
        background: repeating-linear-gradient(
          45deg,
          var(--stage-color) 0px 2px,
          transparent 2px 4px
        );
        width: 100% !important;
        opacity: 0.55;
      }
      .track em {
        padding-left: 8px;
        color: var(--vh-muted);
        font-style: normal;
      }
      .stage-detail {
        padding: 8px 0 16px;
      }
      .detail-tabs {
        display: flex;
        gap: 6px;
        margin: 22px 0;
        padding: 4px;
        border-radius: 14px;
        background: var(--vh-surface);
      }
      .detail-tabs button {
        flex: 1;
        border: 0;
        background: transparent;
      }
      .detail-tabs [aria-pressed="true"] {
        background: var(--vh-soft);
      }
      .conversation {
        display: grid;
        gap: 16px;
      }
      .bubble {
        padding: 18px 20px;
        border-radius: 20px;
        max-width: 90%;
      }
      .bubble p {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        font-size: 15px;
        line-height: 1.75;
      }
      .bubble small {
        display: block;
        margin-bottom: 8px;
        color: var(--vh-muted);
      }
      .bubble.user {
        justify-self: end;
        background: var(--vh-soft);
        border-bottom-right-radius: 5px;
      }
      .bubble.assistant {
        justify-self: start;
        background: var(--vh-surface);
        border-bottom-left-radius: 5px;
      }
      .usage {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin: 12px 0;
      }
      .usage > div {
        padding: 16px;
        border-radius: 14px;
        border: 1px solid var(--vh-line);
        display: grid;
        gap: 6px;
      }
      .usage small {
        color: var(--vh-muted);
        font-size: 11px;
      }
      .usage strong {
        font-size: 24px;
        font-weight: 550;
        font-variant-numeric: tabular-nums;
      }
      .replay-note {
        margin-top: -4px;
      }
      .evidence,
      .audio-preview {
        display: grid;
        gap: 16px;
      }
      .json-tree {
        border-bottom: 1px solid var(--vh-line);
        min-width: 0;
      }
      .json-tree summary {
        display: flex;
        gap: 12px;
        align-items: center;
        font-size: 12px;
      }
      .json-tree summary::before {
        content: "›";
        font-size: 18px;
      }
      .json-tree[open] > summary::before {
        transform: rotate(90deg);
      }
      .json-children {
        padding-left: 14px;
        border-left: 1px solid var(--vh-line);
      }
      .json-value {
        display: grid;
        grid-template-columns: minmax(80px, 0.35fr) minmax(0, 1fr);
        gap: 10px;
        font-size: 11px;
        padding: 8px 0;
        overflow-wrap: anywhere;
      }
      .json-value > span {
        color: var(--vh-muted);
      }
      .audio-format {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      audio {
        width: 100%;
        margin-top: 12px;
      }
      .empty h3 {
        margin: 12px 0;
      }
      .empty p {
        max-width: 480px;
        margin: auto;
        line-height: 1.7;
      }
      .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip-path: inset(50%);
      }
      @keyframes drawer-in {
        from {
          transform: translateX(60px);
          opacity: 0;
        }
      }
      @media (max-width: 900px) {
        .toolbar {
          flex-wrap: wrap;
        }
        .search {
          width: 100%;
          max-width: none;
        }
        .run-open {
          grid-template-columns: 6px minmax(0, 1fr) 76px;
        }
        .run-facts {
          display: none;
        }
        .list-head {
          grid-template-columns: 1fr 80px 56px;
        }
        .list-head > span:nth-child(2) {
          display: none;
        }
      }
      @media (max-width: 600px) {
        .run-surface {
          padding: 6px 12px;
        }
        .run-row {
          flex-wrap: wrap;
          gap: 0;
          padding: 10px 0;
        }
        .run-open {
          padding: 10px 0;
          width: 100%;
          flex-basis: 100%;
          gap: 8px;
        }
        .identity strong {
          white-space: normal;
          font-size: 14px;
        }
        .compare-pick {
          width: auto;
          min-height: 44px;
          margin-left: auto;
          font-size: 12px;
        }
        .mobile-compare {
          display: inline;
        }
        .list-head {
          display: none;
        }
        .run-open .chip {
          font-size: 10px;
          padding: 5px 8px;
        }
        .filters {
          gap: 0;
          flex-wrap: nowrap;
          width: 100%;
          justify-content: space-between;
        }
        .filter {
          padding: 10px;
          font-size: 12px;
        }
        dialog {
          width: 100%;
        }
        .drawer-header,
        .drawer-body {
          padding: 18px;
        }
        .waterfall {
          padding: 14px;
        }
        .stage summary {
          grid-template-columns: 46px minmax(0, 1fr) 60px;
          gap: 8px;
        }
        .timing-head {
          align-items: flex-start;
          flex-direction: column;
        }
        .bubble {
          max-width: 95%;
        }
        .usage {
          gap: 8px;
        }
        .usage > div {
          padding: 12px;
        }
        .json-value {
          grid-template-columns: 1fr;
          gap: 3px;
        }
      }
    `,
  ];
}
if (!customElements.get("voice-harness-runs"))
  customElements.define("voice-harness-runs", VoiceHarnessRuns);
declare global {
  interface HTMLElementTagNameMap {
    "voice-harness-runs": VoiceHarnessRuns;
  }
}
