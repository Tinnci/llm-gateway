import { LitElement, css, html } from "lit";
import type { PropertyValues } from "lit";

export type VoiceSettings = Record<string, number | boolean>;
export interface VoiceSettingsHass {
  language?: string;
  callApi?: (method: "GET" | "POST", path: string, data?: unknown) => Promise<unknown>;
}
interface AgentResponse {
  ok: boolean;
  error?: string;
  config?: VoiceSettings;
  apply?: { applied: boolean };
  status?: string;
}

export async function voiceSettingsRequest(
  hass: VoiceSettingsHass, action: "read" | "update" | "preview", data: unknown = {},
): Promise<AgentResponse> {
  if (!hass.callApi) throw new Error("Home Assistant is unavailable");
  const service = action === "preview" ? "kukui_voice_audio_preview" : `kukui_voice_config_${action}`;
  const response = await hass.callApi("POST", `services/rest_command/${service}?return_response`, data) as {
    service_response?: { status?: number; content?: AgentResponse };
  };
  const result = response.service_response;
  if (!result?.content?.ok || result.status !== 200) {
    throw new Error(result?.content?.error || "The satellite did not apply this request");
  }
  return result.content;
}

export class VoiceSettingsSaver {
  pending: VoiceSettings = {};
  saved: VoiceSettings = {};
  error = "";
  saving = false;
  inflight: VoiceSettings = {};
  applied = false;
  private timer?: ReturnType<typeof setTimeout>;
  private flight?: Promise<void>;

  constructor(
    private save: (patch: VoiceSettings) => Promise<AgentResponse>,
    private changed: () => void,
  ) {}

  edit(field: string, value: number | boolean): void {
    this.pending = { ...this.pending, [field]: value };
    this.error = "";
    this.applied = false;
    clearTimeout(this.timer);
    this.timer = setTimeout(() => void this.flush().catch(() => {}), 400);
    this.changed();
  }

  flush(): Promise<void> {
    clearTimeout(this.timer);
    if (this.flight) return this.flight;
    const run = async () => {
      while (Object.keys(this.pending).length) {
        const patch = this.pending;
        this.inflight = patch;
        this.pending = {};
        this.saving = true;
        this.changed();
        try {
          const response = await this.save(patch);
          if (!response.ok || !response.apply?.applied || !response.config) {
            throw new Error(response.error || "Settings were saved but could not be applied");
          }
          this.saved = response.config;
          this.applied = true;
          this.error = "";
        } catch (error) {
          this.pending = { ...patch, ...this.pending };
          this.error = error instanceof Error ? error.message : String(error);
          this.applied = false;
          throw error;
        } finally {
          this.saving = false;
          this.inflight = {};
          this.changed();
        }
      }
    };
    this.flight = run().finally(() => { this.flight = undefined; });
    return this.flight;
  }
}

const groups = [
  { title: ["Wake and follow-up", "唤醒与追问"], fields: [
    ["wake_cue_volume", "Wake cue", "唤醒提示音"],
    ["follow_up_cue_volume", "Follow-up cue", "追问提示音"],
  ] },
  { title: ["Spoken replies", "语音播报"], fields: [
    ["tts_volume_day", "Day", "白天音量"],
    ["tts_volume_night", "Night", "夜间音量"],
  ] },
  { title: ["Feedback", "状态反馈"], fields: [
    ["processing_volume", "Thinking", "处理中提示"],
    ["fallback_volume", "Local feedback", "完成与错误提示"],
  ] },
] as const;

export class VoiceHarnessAudioSettings extends LitElement {
  static properties = { hass: { attribute: false }, language: { type: String } };
  declare hass?: VoiceSettingsHass;
  declare language?: string;
  private loaded = false;
  private loading = false;
  private loadError = "";
  private previewing = "";
  private previewMessage = "";
  readonly saver = new VoiceSettingsSaver(
    (patch) => voiceSettingsRequest(this.hass!, "update", { config: patch }),
    () => this.requestUpdate(),
  );

  setConfig(): void { /* Lovelace supplies hass after card configuration. */ }
  getCardSize(): number { return 6; }

  protected updated(changes: PropertyValues): void {
    if (changes.has("hass") && this.hass && !this.loaded && !this.loading) void this.load();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    // A panel refresh or navigation must not discard the user's last slider edit.
    void this.saver.flush().catch(() => {});
  }

  private async load(): Promise<void> {
    this.loading = true;
    try {
      const response = await voiceSettingsRequest(this.hass!, "read");
      this.saver.saved = response.config || {};
      this.saver.applied = Boolean(response.apply?.applied);
      this.loaded = true;
      this.loadError = "";
    } catch (error) {
      this.loadError = error instanceof Error ? error.message : String(error);
    } finally {
      this.loading = false;
      this.requestUpdate();
    }
  }

  private text(en: string, zh: string): string {
    return (this.language || this.hass?.language || "en").startsWith("zh") ? zh : en;
  }

  private async preview(field: string): Promise<void> {
    this.previewing = field;
    this.previewMessage = "";
    this.requestUpdate();
    try {
      await this.saver.flush();
      const response = await voiceSettingsRequest(this.hass!, "preview", { field });
      this.previewMessage = response.status === "muted"
        ? this.text("Output is muted", "平板当前已静音")
        : this.text("Test sound played on the tablet", "已在平板播放试听音");
    } catch (error) {
      this.previewMessage = error instanceof Error ? error.message : String(error);
    } finally {
      this.previewing = "";
      this.requestUpdate();
    }
  }

  render() {
    const values = { ...this.saver.saved, ...this.saver.inflight, ...this.saver.pending };
    const status = this.saver.saving
      ? this.text("Applying…", "正在应用…")
      : Object.keys(this.saver.pending).length ? this.text("Saving…", "正在保存…")
      : this.saver.applied ? this.text("Saved and applied", "已保存并应用")
      : this.text("Changes save automatically", "修改后自动保存");
    return html`
      <section aria-label=${this.text("Tablet audio", "平板声音")}>
        <header><div><h2>${this.text("Tablet audio", "平板声音")}</h2>
          <p role="status">${status}</p></div>
          <div class="toggles">${([['audio_muted', 'Mute', '静音'], ['night_mode', 'Night', '夜间']] as const).map(([field, en, zh]) => html`
            <button class=${values[field] ? "selected" : ""} ?disabled=${!this.loaded}
              aria-pressed=${Boolean(values[field])} @click=${() => this.saver.edit(field, !values[field])}>${this.text(en, zh)}</button>`)}
          </div></header>
        ${this.loadError ? html`<p role="alert">${this.loadError}</p><button @click=${() => this.load()}>${this.text("Retry", "重试")}</button>` : ""}
        ${groups.map((group) => html`<fieldset><legend>${this.text(group.title[0], group.title[1])}</legend>
          ${group.fields.map(([field, en, zh]) => html`<div class="volume-row">
            <label for=${field}>${this.text(en, zh)}<output>${Math.round(Number(values[field] ?? 0) * 100)}%</output></label>
            <input id=${field} type="range" min=${["tts_volume_day", "tts_volume_night", "fallback_volume"].includes(field) ? "0.2" : "0.05"} max="1" step="0.01" .value=${String(values[field] ?? 1)}
              ?disabled=${!this.loaded} @input=${(event: Event) => this.saver.edit(field, Number((event.target as HTMLInputElement).value))}>
            <button class="preview" ?disabled=${!this.loaded || Boolean(this.previewing)}
              aria-label=${`${this.text("Preview on tablet", "在平板试听")} · ${this.text(en, zh)}`}
              @click=${() => this.preview(field)}>▶ <span>${this.text("Preview", "试听")}</span></button>
          </div>`)}
        </fieldset>`)}
        ${this.saver.error ? html`<p role="alert">${this.saver.error}</p><button @click=${() => void this.saver.flush().catch(() => {})}>${this.text("Retry", "重试")}</button>` : ""}
        <p class="preview-status" role="status">${this.previewMessage || this.text("Preview plays through the tablet speaker.", "试听声音从平板扬声器播放。")}</p>
      </section>`;
  }

  static styles = css`
    :host { display: block; color: var(--primary-text-color, #e7edf4); }
    section { background: var(--card-background-color, #17222e); border-radius: 18px; padding: 22px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    h2 { font-size: 20px; margin: 0 0 7px; }
    p { color: var(--secondary-text-color, #a2b5c5); font-size: 13px; margin: 0; }
    fieldset { border: 0; border-top: 1px solid var(--divider-color, #344555); padding: 16px 0 8px; margin: 20px 0 0; }
    legend { padding-right: 10px; font-size: 13px; font-weight: 600; color: var(--secondary-text-color, #a2b5c5); }
    .volume-row { display: grid; grid-template-columns: minmax(110px, 1fr) minmax(90px, 1.3fr) auto; gap: 12px; align-items: center; margin: 10px 0; }
    label { display: flex; flex-direction: column; gap: 5px; font-size: 14px; }
    output { font-size: 12px; color: var(--secondary-text-color, #a2b5c5); font-variant-numeric: tabular-nums; }
    input { width: 100%; min-width: 0; accent-color: var(--primary-color, #6cdbd0); }
    button { border: 1px solid var(--divider-color, #405564); background: transparent; color: inherit; border-radius: 20px; min-height: 40px; padding: 7px 13px; cursor: pointer; }
    button:focus-visible, input:focus-visible { outline: 2px solid var(--primary-color, #6cdbd0); outline-offset: 3px; }
    button:disabled { opacity: .45; cursor: default; }
    .toggles { display: flex; gap: 8px; }
    .selected { background: var(--primary-color, #6cdbd0); color: var(--text-primary-color, #10252a); }
    [role=alert] { color: var(--error-color, #ff9b88); margin: 12px 0; }
    .preview-status { margin-top: 12px; min-height: 18px; }
    @media(max-width: 430px) { section { padding: 16px; } .volume-row { grid-template-columns: 95px 1fr 42px; gap: 8px; } .preview span { display: none; } .preview { padding: 7px; } }
  `;
}

if (!customElements.get("voice-harness-audio-settings")) {
  customElements.define("voice-harness-audio-settings", VoiceHarnessAudioSettings);
}
