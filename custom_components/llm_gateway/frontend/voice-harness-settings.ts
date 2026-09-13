import { css, html, LitElement, nothing } from "lit";
import {
  harnessFoundationStyles,
  harnessButtonStyles,
  harnessSurfaceStyles,
} from "./voice-harness-styles";
import {
  type TuningConfiguration,
  parseTuning,
  serializeTuning,
  tuningSnapshot,
} from "./voice-harness-portability";
import {
  object,
  records,
  type EvidenceRecord,
} from "./voice-harness-live-model";
import { requestHarnessJson, type HomeAssistantApi } from "./voice-harness-api";
import {
  voiceSettingsRequest,
  type VoiceSettings,
} from "./voice-harness-audio-settings";

type Section = "audio" | "routing" | "pipeline" | "system";
export class VoiceHarnessSettings extends LitElement {
  static properties = {
    hass: { attribute: false },
    language: {},
    section: { reflect: true },
    entries: { attribute: false },
    configuration: { attribute: false },
    applyTuning: { attribute: false },
    pending: { state: true },
    message: { state: true },
    error: { state: true },
    busy: { state: true },
    entryId: { state: true },
    probeResult: { state: true },
    probing: { state: true },
  };
  declare hass: HomeAssistantApi | undefined;
  declare language: string;
  declare section: Section;
  declare entries: EvidenceRecord[];
  declare configuration: EvidenceRecord;
  declare applyTuning?: (
    entryId: string,
    config: TuningConfiguration,
  ) => Promise<string>;
  declare private pending: TuningConfiguration | null;
  declare private message: string;
  declare private error: string;
  declare private busy: boolean;
  declare private entryId: string;
  declare private probeResult: Record<string, string>;
  declare private probing: string;
  constructor() {
    super();
    this.language = "en";
    this.section = "audio";
    this.entries = [];
    this.configuration = {};
    this.pending = null;
    this.message = "";
    this.error = "";
    this.busy = false;
    this.entryId = "";
    this.probeResult = {};
    this.probing = "";
  }
  private t(en: string, zh: string) {
    return this.language.startsWith("zh") ? zh : en;
  }
  render() {
    const t = this.t.bind(this);
    const groups: Array<{
      id: Section;
      icon: string;
      title: string;
      hint: string;
    }> = [
      {
        id: "audio",
        icon: "mdi:tune-variant",
        title: t("Acoustic tuning", "声学调音"),
        hint: t("Scenes, cues & speech", "场景、提示音与播报"),
      },
      {
        id: "routing",
        icon: "mdi:source-branch",
        title: t("Models & routing", "大模型路由策略"),
        hint: t("Providers, models & API", "服务商、模型与 API"),
      },
      {
        id: "pipeline",
        icon: "mdi:waveform",
        title: t("ASR / TTS & Wyoming", "ASR / TTS 与 Wyoming"),
        hint: t("From capture to playback", "从收音到播放"),
      },
      {
        id: "system",
        icon: "mdi:database-outline",
        title: t("System & storage", "系统与存储策略"),
        hint: t("Retention & configuration", "保留周期与配置迁移"),
      },
    ];
    return html`
      <div class="section-head">
        <div>
          <span class="eyebrow">VOICE HARNESS / ${t("SETTINGS", "设置")}</span>
          <h2>${t("Make it feel like home.", "让声音，更懂你的生活。")}</h2>
          <p class="muted">
            ${t("Thoughtful defaults. A little room to make them yours.", "从恰好的默认值出发，把细节调到适合自己。")}
          </p>
        </div>
      </div>
      <div class="layout">
        <nav class="groups" aria-label=${t("Settings groups", "设置分组")}>
          ${groups.map(
        (group) =>
          html`<button
            aria-current=${this.section === group.id ? "page" : "false"}
            @click=${() => {
              this.section = group.id;
            }}
          >
            <ha-icon icon=${group.icon}></ha-icon
            ><span
              ><strong>${group.title}</strong><small>${group.hint}</small></span
            ><span class="arrow">›</span>
          </button>`,
      )}
        </nav>
        <div class="content">
          <div ?hidden=${this.section !== "audio"}>
            <slot name="audio"></slot>
          </div>
          <div ?hidden=${this.section === "audio"}>
            <slot name="configuration"></slot>
          </div>
          <section
            class="surface probes"
            ?hidden=${this.section !== "pipeline"}
          >
            <div class="section-head">
              <div>
                <span class="eyebrow">LIVE CHECK</span>
                <h3>${t("Listen to the connection", "看见链路是否畅通")}</h3>
                <p class="muted">
                  ${t("Probe from Home Assistant and measure the response.", "通过 Home Assistant 发起探测，记录本次响应。")}
                </p>
              </div>
            </div>
            <div class="probe-grid">
              ${[
            ["wyoming", "Wyoming"],
            ["tts", "Edge TTS"],
            ["satellite", "Kukui"],
          ].map(
            ([key, label]) =>
              html`<article>
                <strong>${label}</strong>
                <p class="muted" role="status">
                  ${this.probeResult[key] || t("Not measured", "尚未测量")}
                </p>
                <button
                  ?disabled=${Boolean(this.probing)}
                  @click=${() => this.probe(key)}
                >
                  ${this.probing === key ? t("Measuring…", "测量中…") : t("Probe now", "立即探测")}
                </button>
              </article>`,
          )}
            </div>
          </section>
          <div ?hidden=${this.section !== "pipeline"}>
            <slot name="pipeline"></slot>
          </div>
          <section
            class="surface portability"
            ?hidden=${this.section !== "system"}
          >
            <div class="section-head">
              <div>
                <span class="eyebrow">TAKE YOUR SETTINGS WITH YOU</span>
                <h3>
                  ${t("Your tuning, wherever you need it", "把合适的调音，带到下一处")}
                </h3>
                <p class="muted">
                  ${t("JSON or YAML. Saved tuning values only; API keys stay in Home Assistant.", "支持 JSON 与 YAML。导出已保存的调音参数，API 密钥留在 Home Assistant。")}
                </p>
              </div>
            </div>
            ${
              this.entries.length > 1
                ? html`<label
                    >${t("Gateway", "网关")}<select
                      .value=${this.selectedEntry()}
                      @change=${(event: Event) => {
                        this.entryId = (
                          event.target as HTMLSelectElement
                        ).value;
                        this.pending = null;
                      }}
                    >
                      ${this.entries.map((entry) => html`<option value=${String(entry.entry_id)}>${String(entry.title)}</option>`)}
                    </select></label
                  >`
                : nothing
            }
            <div class="portability-actions">
              <button
                ?disabled=${this.busy || !this.entries.length}
                @click=${() => this.export("json")}
              >
                ↓ ${t("Export JSON", "导出 JSON")}</button
              ><button
                ?disabled=${this.busy || !this.entries.length}
                @click=${() => this.export("yaml")}
              >
                ↓ ${t("Export YAML", "导出 YAML")}</button
              ><label class="import-button"
                ><span>↑ ${t("Import tuning", "导入调音配置")}</span
                ><input
                  type="file"
                  accept=".json,.yaml,.yml,application/json,application/yaml"
                  ?disabled=${this.busy}
                  @change=${(event: Event) => this.import((event.target as HTMLInputElement).files?.[0])}
              /></label>
            </div>
            ${
              this.pending
                ? html`<div class="import-preview">
                    <h3>${t("Review imported values", "检查待导入参数")}</h3>
                    <pre>${JSON.stringify(this.pending, null, 2)}</pre>
                    <button
                      class="primary"
                      ?disabled=${this.busy}
                      @click=${() => this.apply()}
                    >
                      ${this.busy ? t("Applying…", "应用中…") : t("Apply these values", "应用这些参数")}</button
                    ><button
                      class="quiet"
                      ?disabled=${this.busy}
                      @click=${() => {
                        this.pending = null;
                      }}
                    >
                      ${t("Cancel", "取消")}
                    </button>
                  </div>`
                : nothing
            }
            ${this.error ? html`<p class="error" role="alert">${this.error}</p>` : nothing}${this.message ? html`<p class="message" role="status">${this.message}</p>` : nothing}
          </section>
        </div>
      </div>
    `;
  }
  private selectedEntry() {
    return this.entryId || String(this.entries[0]?.entry_id || "");
  }
  private async export(format: "json" | "yaml") {
    this.busy = true;
    this.error = "";
    this.message = "";
    try {
      const config = records(this.configuration.entries).find(
        (entry) => entry.entry_id === this.selectedEntry(),
      );
      if (!config)
        throw new Error(
          this.t(
            "Load the gateway settings before exporting.",
            "请先加载网关设置再导出。",
          ),
        );
      let audio: VoiceSettings = {};
      try {
        audio =
          (await voiceSettingsRequest(this.hass || {}, "read")).config || {};
      } catch {
        this.message = this.t(
          "Satellite unavailable; exported gateway tuning only.",
          "卫星暂不可达，本次仅导出网关调音参数。",
        );
      }
      const data = tuningSnapshot(object(config.options), audio);
      const url = URL.createObjectURL(
        new Blob([serializeTuning(data, format)], {
          type: format === "json" ? "application/json" : "application/yaml",
        }),
      );
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "voice-harness-tuning." + format;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      this.message ||= this.t(
        "Saved tuning exported.",
        "已导出保存的调音配置。",
      );
    } catch (error) {
      this.error = error instanceof Error ? error.message : String(error);
    } finally {
      this.busy = false;
    }
  }
  private async import(file?: File) {
    if (!file) return;
    this.error = "";
    this.message = "";
    this.pending = null;
    try {
      this.pending = parseTuning(await file.text());
    } catch (error) {
      this.error = error instanceof Error ? error.message : String(error);
    }
  }
  private async apply() {
    if (!this.pending || !this.applyTuning) return;
    this.busy = true;
    this.error = "";
    this.message = "";
    try {
      this.message = await this.applyTuning(this.selectedEntry(), this.pending);
      this.pending = null;
    } catch (error) {
      this.error = error instanceof Error ? error.message : String(error);
    } finally {
      this.busy = false;
    }
  }
  private async probe(kind: string) {
    this.probing = kind;
    const started = performance.now();
    try {
      let detail = "";
      if (kind === "satellite") {
        await voiceSettingsRequest(this.hass || {}, "read");
        detail = this.t("Agent replied", "代理已响应");
      } else if (kind === "wyoming") {
        const result = await requestHarnessJson<{
          results: Array<{
            name: string;
            connected: boolean;
            latency_ms?: number;
            error?: string;
          }>;
        }>(this.hass, "POST", "llm_gateway/harness/probe-wyoming", {});
        if (!result.results.length)
          throw new Error(
            this.t(
              "No Wyoming integration configured",
              "尚未配置 Wyoming 集成",
            ),
          );
        detail = result.results
          .map(
            (probe) =>
              probe.name +
              ": " +
              (probe.connected
                ? this.t("TCP reachable", "TCP 可达") +
                  " · " +
                  probe.latency_ms +
                  " ms"
                : probe.error),
          )
          .join(" · ");
        this.probeResult = { ...this.probeResult, [kind]: detail };
        return;
      } else {
        const candidates = this.entries.flatMap((entry) =>
          records(object(object(entry.first_response_audio).candidates).tts),
        );
        const entity = candidates.find(
          (candidate) => candidate.usable,
        )?.entity_id;
        if (!entity)
          throw new Error(
            this.t("No available TTS engine", "暂无可用 TTS 引擎"),
          );
        const result = await requestHarnessJson<{ path: string }>(
          this.hass,
          "POST",
          "tts_get_url",
          {
            engine_id: entity,
            message: this.t(
              "The voice connection is ready.",
              "语音链路已准备好。",
            ),
            cache: false,
          },
        );
        if (!result.path?.startsWith("/api/tts_proxy/"))
          throw new Error("TTS did not return a local audio path");
        const response = await fetch(result.path);
        if (!response.ok)
          throw new Error("TTS synthesis returned HTTP " + response.status);
        const bytes = (await response.arrayBuffer()).byteLength;
        if (!bytes) throw new Error("TTS returned no audio");
        detail =
          this.t("Audio synthesized, not played", "已生成音频，未播放") +
          " · " +
          Math.round(bytes / 1024) +
          " KB";
      }
      this.probeResult = {
        ...this.probeResult,
        [kind]:
          detail +
          " · " +
          Math.round(performance.now() - started) +
          " ms " +
          this.t("round trip", "往返"),
      };
    } catch (error) {
      this.probeResult = {
        ...this.probeResult,
        [kind]:
          this.t("Probe failed: ", "探测失败：") +
          (error instanceof Error ? error.message : String(error)),
      };
    } finally {
      this.probing = "";
    }
  }
  static styles = [
    harnessFoundationStyles,
    harnessButtonStyles,
    harnessSurfaceStyles,
    css`
      :host {
        display: block;
      }
      .layout {
        display: grid;
        grid-template-columns: 242px minmax(0, 1fr);
        align-items: start;
        gap: 26px;
      }
      .groups {
        display: grid;
        gap: 8px;
        position: sticky;
        top: 20px;
      }
      .groups button {
        justify-content: flex-start;
        gap: 12px;
        border: 0;
        background: transparent;
        text-align: left;
        padding: 16px 14px;
        border-radius: 16px;
        color: var(--vh-muted);
      }
      .groups [aria-current="page"] {
        color: var(--vh-accent);
        background: var(--vh-soft);
      }
      .groups button > span:not(.arrow) {
        display: grid;
        gap: 4px;
        flex: 1;
      }
      .groups strong {
        font-size: 13px;
        font-weight: 580;
      }
      .groups small {
        font-size: 11px;
        font-weight: 400;
        color: var(--vh-muted);
      }
      .arrow {
        font-size: 20px;
        opacity: 0.6;
      }
      .content {
        display: grid;
        gap: 20px;
        min-width: 0;
      }
      .portability {
        display: grid;
        gap: 18px;
      }
      .portability-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }
      .import-button {
        position: relative;
        min-height: 44px;
        padding: 10px 16px;
        border: 1px solid var(--vh-line);
        border-radius: 12px;
        font-weight: 550;
        font-size: 14px;
        cursor: pointer;
        overflow: hidden;
      }
      .import-button input {
        position: absolute;
        inset: 0;
        opacity: 0;
        cursor: pointer;
        width: 100%;
      }
      .import-button:focus-within {
        outline: 3px solid var(--vh-accent);
        outline-offset: 3px;
      }
      .import-preview {
        padding: 18px;
        background: var(--vh-background);
        border-radius: 16px;
      }
      pre {
        max-height: 320px;
        overflow: auto;
        margin: 14px 0;
      }
      .message {
        font-size: 13px;
        color: var(--success-color);
      }
      .probe-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 16px;
      }
      .probe-grid article {
        display: grid;
        gap: 14px;
        align-content: start;
        min-width: 0;
      }
      .probe-grid p {
        font-size: 12px;
        overflow-wrap: anywhere;
      }
      .probe-grid button {
        margin-top: auto;
      }
      @media (max-width: 1100px) {
        .layout {
          grid-template-columns: 210px minmax(0, 1fr);
          gap: 18px;
        }
        .probe-grid {
          grid-template-columns: 1fr;
        }
      }
      @media (max-width: 850px) {
        .layout {
          grid-template-columns: 1fr;
        }
        .groups {
          grid-template-columns: 1fr 1fr;
          position: static;
          gap: 8px;
        }
        .groups button {
          background: var(--vh-surface);
          padding: 14px;
        }
        .arrow {
          display: none;
        }
      }
      @media (max-width: 600px) {
        .groups button {
          gap: 8px;
          padding: 12px;
        }
        .groups strong {
          font-size: 12px;
        }
        .groups small {
          font-size: 10px;
        }
        .groups ha-icon {
          width: 18px;
          height: 18px;
          --mdc-icon-size: 18px;
        }
        .portability-actions > * {
          flex: 1;
          white-space: nowrap;
        }
      }
    `,
  ];
}
if (!customElements.get("voice-harness-settings"))
  customElements.define("voice-harness-settings", VoiceHarnessSettings);
declare global {
  interface HTMLElementTagNameMap {
    "voice-harness-settings": VoiceHarnessSettings;
  }
}
