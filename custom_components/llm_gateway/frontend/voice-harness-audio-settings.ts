import { LitElement, css, html } from "lit";
import type { PropertyValues } from "lit";

export type VoiceSettings = Record<string, number | boolean>;
export interface VoiceSettingsHass {
  language?: string;
  callApi?: (method: "GET" | "POST", path: string, data?: unknown) => Promise<unknown>;
}
interface VoiceRuntime {
  phase: string;
  capture: "paused" | "listening" | "closed" | "wake_word" | "unknown";
  pause_remaining_seconds?: number;
  tts_profile: "day" | "night" | null;
  tts_volume: number | null;
}
interface AgentResponse {
  ok: boolean;
  error?: string;
  config?: VoiceSettings;
  apply?: { applied: boolean };
  runtime?: VoiceRuntime;
  status?: string;
}

export async function voiceSettingsRequest(
  hass: VoiceSettingsHass, action: "read" | "update" | "preview" | "pause" | "resume", data: unknown = {},
): Promise<AgentResponse> {
  if (!hass.callApi) throw new Error("Home Assistant is unavailable");
  const service = action === "preview" ? "kukui_voice_audio_preview"
    : action === "pause" || action === "resume" ? `kukui_voice_${action}` : `kukui_voice_config_${action}`;
  const response = await hass.callApi("POST", `services/rest_command/${service}?return_response`, data) as {
    service_response?: { status?: number; content?: AgentResponse };
  };
  const result = response.service_response;
  if (result?.content?.ok !== true || result.status !== 200) {
    throw new Error(result?.content?.error || "The satellite did not apply this request");
  }
  if (action === "preview" && !["played", "muted"].includes(result.content.status || "")) {
    throw new Error("Test sound playback was not confirmed");
  }
  if (action === "read" || action === "update") {
    const config = result.content.config;
    if (!config || typeof config !== "object" || Array.isArray(config)) {
      throw new Error("The satellite did not return its settings");
    }
    // The agent also returns routing strings; this card edits numeric and boolean settings.
    return { ...result.content, config: Object.fromEntries(Object.entries(config).filter(
      ([, value]) => typeof value === "boolean" || (typeof value === "number" && Number.isFinite(value)),
    )) };
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

  edit(field: string, value: number | boolean): void { this.editPatch({ [field]: value }); }

  editPatch(patch: VoiceSettings): void {
    this.pending = { ...this.pending, ...patch };
    this.error = "";
    this.applied = false;
    clearTimeout(this.timer);
    this.timer = setTimeout(() => void this.flush().catch(() => {}), 400);
    this.changed();
  }

  flush(reapply = false): Promise<void> {
    clearTimeout(this.timer);
    if (this.flight) return this.flight;
    const run = async () => {
      while (Object.keys(this.pending).length || reapply) {
        reapply = false;
        const patch = this.pending;
        this.inflight = patch;
        this.pending = {};
        this.saving = true;
        this.changed();
        try {
          const response = await this.save({ ...patch });
          if (!response.ok || !response.apply?.applied || !response.config) {
            throw new Error(response.error || "Settings were saved but could not be applied");
          }
          this.saved = { ...response.config };
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
    ["wake_cue_volume", "Wake cue", "唤醒提示音", 0.05, 0.7, 1],
    ["follow_up_cue_volume", "Follow-up cue", "追问提示音", 0.05, 0.7, 1],
  ] },
  { title: ["Spoken replies", "语音播报"], fields: [
    ["tts_volume_day", "Daytime speech", "日间播报", 0.2, 0.7, 1],
    ["tts_volume_night", "Nighttime speech", "夜间播报", 0.2, 0.5, 0.75],
  ] },
  { title: ["Gentle feedback", "轻声反馈"], fields: [
    ["processing_volume", "Thinking", "思考等待音", 0.05, 0.45, 0.65],
    ["fallback_volume", "Completion and errors", "完成与错误提示", 0.2, 0.6, 1],
  ] },
] as const;

export const audioScenes = [
  { id: "daily", name: ["Everyday", "日常"], hint: ["Clear and present", "清晰、自然"], values: {
    wake_cue_volume: 1, follow_up_cue_volume: 1, processing_volume: 0.58,
    tts_volume_day: 1, tts_volume_night: 0.72, fallback_volume: 1, night_mode: false,
  } },
  { id: "focus", name: ["Focus", "专注"], hint: ["Less interruption", "减少打扰"], values: {
    wake_cue_volume: 0.7, follow_up_cue_volume: 0.75, processing_volume: 0.25,
    tts_volume_day: 0.85, tts_volume_night: 0.6, fallback_volume: 0.7, night_mode: false,
  } },
  { id: "night", name: ["Quiet night", "夜间"], hint: ["Softer cues and speech", "提示与播报更柔和"], values: {
    wake_cue_volume: 0.55, follow_up_cue_volume: 0.6, processing_volume: 0.2,
    tts_volume_day: 1, tts_volume_night: 0.72, fallback_volume: 0.55, night_mode: true,
  } },
] as const;

export class VoiceHarnessAudioSettings extends LitElement {
  static properties = { hass: { attribute: false }, language: { type: String }, active: { type: Boolean } };
  declare hass?: VoiceSettingsHass;
  declare language?: string;
  declare active: boolean;
  constructor() { super(); this.active = true; }
  private loaded = false;
  private loadError = "";
  private previewing = "";
  private previewMessage = "";
  private controllingCapture = false;
  private runtime?: VoiceRuntime;
  private readFlight?: Promise<void>;
  private poll?: ReturnType<typeof setInterval>;
  private onVisibility = () => { if (document.visibilityState !== "hidden") void this.refresh(); };
  readonly saver = new VoiceSettingsSaver(
    async (patch) => {
      const response = await voiceSettingsRequest(this.hass!, "update", { config: patch });
      this.runtime = response.runtime;
      this.loadError = "";
      this.loaded = true;
      return response;
    },
    () => this.requestUpdate(),
  );

  setConfig(): void { /* Lovelace supplies hass after card configuration. */ }
  getCardSize(): number { return 10; }

  connectedCallback(): void {
    super.connectedCallback();
    document.addEventListener("visibilitychange", this.onVisibility);
    this.poll = setInterval(() => void this.refresh(), 2000);
    void this.refresh();
  }

  protected updated(changes: PropertyValues): void {
    if ((changes.has("hass") || changes.has("active")) && this.hass && this.active) void this.refresh();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    clearInterval(this.poll);
    document.removeEventListener("visibilitychange", this.onVisibility);
    // Navigation must not discard the user's last slider edit.
    void this.saver.flush().catch(() => {});
  }

  refresh(): Promise<void> {
    if (this.readFlight) return this.readFlight;
    if (!this.active || !this.hass?.callApi || this.saver.saving || document.visibilityState === "hidden") return Promise.resolve();
    const savedBeforeRead = this.saver.saved;
    this.readFlight = (async () => {
      try {
        const response = await voiceSettingsRequest(this.hass!, "read");
        // A response requested before a write cannot replace the newer saved snapshot.
        if (this.saver.saving || this.saver.saved !== savedBeforeRead) return;
        this.saver.saved = { ...response.config };
        this.saver.applied = response.apply?.applied === true;
        this.runtime = response.runtime;
        this.loaded = true;
        this.loadError = "";
      } catch (error) {
        if (this.saver.saved === savedBeforeRead) this.loadError = String(error);
      } finally {
        this.readFlight = undefined;
        this.requestUpdate();
      }
    })();
    return this.readFlight;
  }

  private text(en: string, zh: string): string {
    return (this.language || this.hass?.language || "en").startsWith("zh") ? zh : en;
  }

  private async preview(field: string): Promise<void> {
    this.previewing = field;
    this.previewMessage = this.text("Requesting a test sound on the tablet…", "正在请求平板试听…");
    this.requestUpdate();
    try {
      await this.saver.flush(!this.saver.applied);
      const response = await voiceSettingsRequest(this.hass!, "preview", { field });
      this.previewMessage = response.status === "muted"
        ? this.text("Speaker muted. Your volume settings are kept.", "扬声器已静音，音量设置已保留。")
        : this.text("Tablet test playback completed", "平板试听播放完成");
    } catch (error) {
      this.previewMessage = `${this.text("Test sound not completed", "试听未完成")} · ${error instanceof Error ? error.message : String(error)}`;
    } finally {
      this.previewing = "";
      this.requestUpdate();
    }
  }

  private async toggleCapture(): Promise<void> {
    this.controllingCapture = true;
    this.requestUpdate();
    try {
      await voiceSettingsRequest(this.hass!, this.runtime?.capture === "paused" ? "resume" : "pause",
        { seconds: 1800, reason: "audio_settings" });
      await this.refresh();
    } catch (error) {
      this.previewMessage = `${this.text("Wake control not confirmed", "唤醒控制未确认")} · ${String(error)}`;
    } finally {
      this.controllingCapture = false;
      this.requestUpdate();
    }
  }

  private captureLabel(): string {
    switch (this.runtime?.capture) {
      case "listening": return this.text("Listening to you", "正在聆听你");
      case "closed": return this.text("Recording ended", "本轮收音已结束");
      case "wake_word": return this.text("Ready for the wake word", "等待唤醒词");
      case "paused": return this.text("Wake word paused", "唤醒已暂停");
      default: return this.text("Capture state unavailable", "收音状态未知");
    }
  }

  render() {
    const values = { ...this.saver.saved, ...this.saver.inflight, ...this.saver.pending };
    const pending = Object.keys(this.saver.pending).length > 0;
    const scene = audioScenes.find((item) => Object.entries(item.values).every(([key, value]) => values[key] === value));
    const busy = ["listening", "stt", "thinking", "speaking"].includes(this.runtime?.phase || "");
    const status = this.loadError ? this.text("Tablet connection interrupted", "平板连接中断")
      : !this.loaded ? this.text("Connecting to the tablet…", "正在连接平板…")
      : this.saver.error ? this.text("Application not confirmed", "应用未确认")
      : this.saver.saving ? this.text("Applying…", "正在应用…")
      : pending ? this.text("Saving…", "正在保存…")
      : this.saver.applied ? this.text("Synced with the tablet", "已同步到平板")
      : this.text("Saved · application pending", "已保存 · 等待应用");
    return html`
      <section aria-label=${this.text("Tablet audio", "平板声音")}>
        <header><div><span class="eyebrow">${this.text("VOICE & SOUND", "语音与声音")}</span>
          <h2>${this.text("Tablet audio", "平板声音")}</h2><p role="status">${status}</p></div>
          <span class="profile">${this.runtime?.tts_profile === "night" ? this.text("Night speech", "夜间播报") : this.runtime?.tts_profile === "day" ? this.text("Day speech", "日间播报") : "—"}
            <strong>${!this.loadError && this.runtime?.tts_volume != null ? `${Math.round(this.runtime.tts_volume * 100)}%` : "—"}</strong></span></header>
        <div class="toggles">${([['audio_muted', 'Speaker mute', '扬声器静音'], ['night_mode', 'Use night volume', '使用夜间音量']] as const).map(([field, en, zh]) => html`
          <button aria-pressed=${values[field] === true} ?disabled=${!this.loaded || typeof values[field] !== "boolean"}
            @click=${() => this.saver.edit(field, !values[field])}>${this.text(en, zh)}</button>`)}</div>
        <div class="capture"><span class=${this.runtime?.capture === "listening" && !this.loadError ? "listening" : ""}>${this.loadError ? this.text("Capture state unavailable", "收音状态未知") : this.captureLabel()}</span>
          <button ?disabled=${!this.loaded || !!this.loadError || this.controllingCapture || !this.runtime}
            @click=${() => this.toggleCapture()}>${this.controllingCapture ? this.text("Updating…", "正在处理…") : this.runtime?.capture === "paused" ? this.text("Resume wake word", "恢复唤醒") : this.text("Pause for 30 min", "免打扰 30 分钟")}</button></div>
        <p class="explanation">${this.text("Mute keeps the microphone available. Do not disturb pauses wake and capture.", "静音保留麦克风；免打扰暂停唤醒与收音。")}</p>
        <div class="section-label"><h3>${this.text("Sound for your moment", "适合此刻的声音")}</h3><span>${scene ? this.text(scene.name[0], scene.name[1]) : this.text("Custom", "自定义")}</span></div>
        <div class="scenes">${audioScenes.map((item) => html`<button aria-pressed=${scene?.id === item.id}
          ?disabled=${!this.loaded} @click=${() => this.saver.editPatch(item.values)}>
          <strong>${this.text(item.name[0], item.name[1])}</strong><span>${this.text(item.hint[0], item.hint[1])}</span></button>`)}</div>
        <div class="groups">${groups.map((group) => html`<fieldset><legend>${this.text(group.title[0], group.title[1])}</legend>
          ${group.fields.map(([field, en, zh, min, low, high]) => {
            const value = typeof values[field] === "number" ? values[field] as number : undefined;
            const active = this.previewing === field;
            return html`<div class="volume-row" aria-busy=${active}>
              <label for=${field}>${this.text(en, zh)}<output for=${field}>${value == null ? "—" : `${Math.round(value * 100)}%`}</output></label>
              <div class="slider-row"><div class="range">
                <span class="recommended" aria-hidden="true" style=${`left:${(low - min) / (1 - min) * 100}%;width:${(high - low) / (1 - min) * 100}%`}></span>
                <input id=${field} type="range" min=${min} max="1" step="0.01" .value=${String(value ?? min)}
                  aria-valuetext=${value == null ? "—" : `${Math.round(value * 100)}%`}
                  ?disabled=${!this.loaded || value == null}
                  @input=${(event: Event) => this.saver.edit(field, Number((event.target as HTMLInputElement).value))}>
              </div><button class="preview" ?disabled=${!this.loaded || value == null || Boolean(this.previewing) || busy || !!this.loadError}
                aria-label=${`${this.text("Play test sound on tablet", "在平板试听")} · ${this.text(en, zh)}`}
                @click=${() => this.preview(field)}>
                ${active ? html`<span class="wave" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>` : html`<span aria-hidden="true">▶</span>`}
                <span>${active ? this.text("Testing…", "试听中…") : this.text("Test", "试听")}</span>
              </button></div>
              <p class="range-note">${this.text("Everyday range", "日常建议")} ${Math.round(low * 100)}–${Math.round(high * 100)}%</p>
            </div>`;
          })}</fieldset>`)}</div>
        <div class="headroom"><span class="peak-line" aria-hidden="true"></span><p>${this.text("Earcon master peak", "提示音母带峰值")} <strong>−1.0 dBFS</strong><br>
          ${this.text("100% is unity gain. Night speech is automatic from 22:00 to 07:00 on the tablet.", "100% 为原始增益。平板时间 22:00–07:00 自动使用夜间播报音量。")}</p></div>
        ${this.loadError ? html`<div class="error" role="alert">${this.text("Cannot refresh tablet settings. Your edits are kept.", "暂时无法读取平板设置，修改仍会保留。")}
          <button @click=${() => this.refresh()}>${this.text("Reconnect", "重新连接")}</button></div>` : ""}
        ${this.saver.error || (this.loaded && !this.saver.applied && !pending && !this.saver.saving) ? html`<div class="error" role="alert">${this.saver.error ? this.text("Changes are unconfirmed and kept for retry.", "修改尚未确认，已保留供重试。") : this.text("Saved settings need another application attempt.", "已保存的设置需要重新应用。")}
          <button @click=${() => void this.saver.flush(true).catch(() => {})}>${this.text("Retry", "重试")}</button></div>` : ""}
        <p class="preview-status" role="status">${this.previewMessage || (busy ? this.text("A conversation is active. Test sounds are available after the reply.", "正在对话，回复结束后可以试听。") : this.text("Test sounds play through the tablet speaker.", "试听声音从平板扬声器播放。"))}</p>
      </section>`;
  }

  static styles = css`
    :host { display: block; container-type: inline-size; color: var(--primary-text-color, #213b3b); --accent: var(--primary-color, #257a70); --surface: var(--card-background-color, #fff); --muted: var(--secondary-text-color, #637773); }
    * { box-sizing: border-box; }
    section { background: linear-gradient(145deg, color-mix(in srgb, var(--accent) 7%, var(--surface)), var(--surface) 45%); border: 1px solid var(--divider-color, #dfe7e3); border-radius: 26px; padding: 26px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
    .eyebrow { color: var(--muted); font-size: 11px; letter-spacing: .14em; }
    h2 { font-size: 27px; font-weight: 550; margin: 7px 0 8px; letter-spacing: -.03em; }
    h3 { font-size: 14px; font-weight: 550; margin: 0; }
    p { color: var(--muted); font-size: 12px; line-height: 1.6; margin: 0; }
    .profile { color: var(--muted); font-size: 11px; text-align: right; white-space: nowrap; }
    .profile strong { display: block; color: var(--primary-text-color, #213b3b); font-size: 30px; font-weight: 450; font-variant-numeric: tabular-nums; }
    button { font: inherit; font-size: 13px; border: 1px solid var(--divider-color, #d6e2de); background: transparent; color: inherit; border-radius: 14px; min-height: 44px; min-width: 44px; padding: 10px 14px; cursor: pointer; transition: background .18s, transform .18s; touch-action: manipulation; }
    button:hover:enabled { background: color-mix(in srgb, var(--accent) 9%, transparent); }
    button:active:enabled { transform: scale(.98); }
    button:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
    button:disabled { opacity: .45; cursor: default; }
    button[aria-pressed=true] { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 12%, transparent); }
    .toggles { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 24px; }
    .capture { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 12px; font-size: 12px; color: var(--muted); }
    .capture > span::before { content: ''; display: inline-block; width: 6px; height: 6px; margin-right: 8px; background: currentColor; border-radius: 50%; }
    .capture .listening { color: var(--accent); }
    .capture .listening::before { animation: listen 1.2s ease-in-out infinite alternate; }
    .capture button { font-size: 12px; padding: 8px 10px; border-color: transparent; flex-shrink: 0; }
    .explanation { margin-top: 3px; font-size: 11px; }
    .section-label { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 26px 0 12px; }
    .section-label > span { font-size: 12px; color: var(--muted); }
    .scenes { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .scenes button { text-align: left; padding: 14px; }
    .scenes strong { display: block; font-size: 14px; font-weight: 550; }
    .scenes span { display: block; margin-top: 6px; font-size: 11px; color: var(--muted); line-height: 1.4; }
    .groups { display: grid; gap: 20px; margin-top: 28px; }
    fieldset { min-width: 0; margin: 0; padding: 14px 16px 2px; border: 1px solid var(--divider-color, #dfe7e3); border-radius: 18px; }
    legend { padding: 0 7px; font-size: 13px; font-weight: 550; color: var(--muted); }
    .volume-row { margin: 2px 0 16px; }
    label { display: flex; justify-content: space-between; gap: 12px; align-items: center; font-size: 14px; }
    output { font-size: 15px; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .slider-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 14px; align-items: center; margin-top: 3px; }
    .range { position: relative; height: 44px; }
    .recommended { position: absolute; height: 3px; bottom: 1px; border-radius: 2px; background: color-mix(in srgb, var(--accent) 35%, transparent); pointer-events: none; }
    input { display: block; width: 100%; min-width: 0; height: 44px; margin: 0; accent-color: var(--accent); cursor: pointer; }
    .preview { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-width: 82px; padding: 8px 11px; font-size: 12px; }
    .range-note { font-size: 10px; margin-top: 3px; }
    .headroom { display: flex; gap: 12px; align-items: center; margin-top: 22px; }
    .headroom p { font-size: 11px; }
    .headroom strong { font-weight: 500; white-space: nowrap; }
    .peak-line { width: 5px; height: 32px; flex-shrink: 0; border-radius: 3px; border-top: 2px solid var(--accent); background: color-mix(in srgb, var(--accent) 15%, transparent); }
    .error { display: flex; gap: 12px; align-items: center; justify-content: space-between; color: var(--error-color, #b84030); margin-top: 16px; font-size: 13px; }
    .preview-status { margin-top: 18px; min-height: 20px; }
    .wave { display: inline-flex; align-items: center; gap: 2px; height: 18px; }
    .wave i { display: block; background: currentColor; width: 2px; height: 12px; border-radius: 2px; animation: wave .6s ease-in-out infinite alternate; }
    .wave i:nth-child(2n) { animation-delay: -.25s; height: 18px; }
    .wave i:nth-child(3) { animation-delay: -.4s; }
    @keyframes wave { from { transform: scaleY(.3); } to { transform: scaleY(1); } }
    @keyframes listen { from { opacity: .4; } to { opacity: 1; } }
    @container (min-width: 700px) { .groups { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; } .preview > span:last-child { display: none; } .preview { min-width: 44px; } }
    @container (max-width: 430px) { section { padding: 20px 16px; border-radius: 20px; } h2 { font-size: 25px; } .scenes { gap: 7px; } .scenes button { padding: 12px 10px; } }
    @media (prefers-reduced-motion: reduce) { *, *::before { animation: none !important; transition: none !important; } }
  `;
}

if (!customElements.get("voice-harness-audio-settings")) {
  customElements.define("voice-harness-audio-settings", VoiceHarnessAudioSettings);
}
