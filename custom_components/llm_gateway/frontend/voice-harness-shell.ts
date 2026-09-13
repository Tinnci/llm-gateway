import { html, nothing, render } from "lit";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import {
  harnessFoundationStyles,
  harnessButtonStyles,
} from "./voice-harness-styles";
import type { EvidenceRecord } from "./voice-harness-live-model";
import type {
  HarnessLiveApi,
  PlaygroundScenario,
} from "./voice-harness-playground";
import type { TuningConfiguration } from "./voice-harness-portability";
import "./voice-harness-navigation";
import "./voice-harness-overview";
import "./voice-harness-runs";
import "./voice-harness-playground";
import "./voice-harness-settings";
import "./voice-harness-audio-settings";

export type HarnessShellModel = {
  active: string;
  visited: Set<string>;
  language: string;
  title: string;
  statusLine: string;
  error: string;
  busy: boolean;
  loaded: boolean;
  hass: HarnessLiveApi;
  entries: EvidenceRecord[];
  satellite: EvidenceRecord;
  configuration: EvidenceRecord;
  updatedAt: string;
  navigation: Array<{ id: string; label: string; icon: string }>;
  scenarios: PlaygroundScenario[];
  diagnostics: string;
  memory: string;
  config: string;
  pipeline: string;
  policies: string;
  earcons: string;
  refresh: () => void;
  select: (id: string) => void;
  loadDetail: (entryId: string, runId: string) => Promise<EvidenceRecord>;
  replay: (entryId: string, runId: string) => Promise<EvidenceRecord | null>;
  applyTuning: (
    entryId: string,
    config: TuningConfiguration,
  ) => Promise<string>;
};

export function renderHarnessShell(
  root: ShadowRoot,
  model: HarnessShellModel,
  legacyStyles: string,
) {
  const zh = model.language.startsWith("zh");
  render(
    html`
      <style>
        ${harnessFoundationStyles.cssText}${legacyStyles}${harnessButtonStyles.cssText}${shellStyles}
      </style>
      <main class="shell">
        <header class="topbar">
          <div class="brand">
            <span class="brand-icon" aria-hidden="true"
              ><i></i><i></i><i></i><i></i><i></i
            ></span>
            <div>
              <h1>Voice Harness</h1>
              <span class="subline"
                >${zh ? "让交互，回归自然。" : "A more natural connection."}</span
              >
            </div>
          </div>
          <voice-harness-navigation
            .active=${model.active}
            .items=${model.navigation}
            @harness-view-select=${(event: CustomEvent<{ id: string }>) => model.select(event.detail.id)}
          ></voice-harness-navigation>
          <div class="refresh">
            <span class="subline" title=${model.statusLine}
              >${model.busy ? (zh ? "同步中…" : "Syncing…") : model.updatedAt ? new Date(model.updatedAt).toLocaleTimeString(model.language, { hour: "2-digit", minute: "2-digit" }) : "—"}</span
            ><button
              class="quiet"
              ?disabled=${model.busy}
              aria-label=${zh ? "刷新观测" : "Refresh observations"}
              @click=${model.refresh}
            >
              <ha-icon icon="mdi:refresh"></ha-icon>
            </button>
          </div>
        </header>
        ${model.error ? html`<div class="banner error" role="alert">${model.error}</div>` : nothing}
        <div
          class="content"
          role="region"
          aria-label=${model.navigation.find((view) => view.id === model.active)?.label || model.active}
        >
          ${!model.loaded ? html`<div class="loading" role="status">${zh ? "正在连接你的语音空间…" : "Connecting to your voice space…"}</div>` : nothing}
          ${
          model.visited.has("overview") && model.loaded
            ? html` <voice-harness-overview
                ?hidden=${model.active !== "overview"}
                .entries=${model.entries}
                .satellite=${model.satellite}
                .language=${model.language}
                @harness-overview-navigate=${(event: CustomEvent<{ destination: string }>) => model.select(event.detail.destination)}
              >
                <div slot="diagnostics">${unsafeHTML(model.diagnostics)}</div>
                <div slot="memory">${unsafeHTML(model.memory)}</div>
              </voice-harness-overview>`
            : nothing
        }
          ${model.visited.has("runs") && model.loaded ? html`<voice-harness-runs ?hidden=${model.active !== "runs"} .entries=${model.entries} .language=${model.language} .loadDetail=${model.loadDetail} .replay=${model.replay}></voice-harness-runs>` : nothing}
          ${model.visited.has("test") && model.loaded ? html`<voice-harness-playground ?hidden=${model.active !== "test"} .hass=${model.hass} .entries=${model.entries} .language=${model.language} .scenarios=${model.scenarios}><div slot="policies">${unsafeHTML(model.policies)}</div></voice-harness-playground>` : nothing}
          ${
          model.visited.has("settings") && model.loaded
            ? html`<voice-harness-settings
                ?hidden=${model.active !== "settings"}
                .hass=${model.hass}
                .entries=${model.entries}
                .language=${model.language}
                .configuration=${model.configuration}
                .applyTuning=${model.applyTuning}
              >
                <div slot="audio">
                  <voice-harness-audio-settings
                    .hass=${model.hass}
                    .language=${model.language}
                    .active=${model.active === "settings"}
                  ></voice-harness-audio-settings>
                  <details class="surface sound-library">
                    <summary>${zh ? "提示音素材库" : "Sound library"}</summary>
                    ${unsafeHTML(model.earcons)}
                  </details>
                </div>
                <div slot="configuration">${unsafeHTML(model.config)}</div>
                <div slot="pipeline">${unsafeHTML(model.pipeline)}</div>
              </voice-harness-settings>`
            : nothing
        }
        </div>
        <footer class="shell-footer">
          <span>Voice Harness</span
          ><span
            >${zh ? "观测 · 理解 · 回应" : "Observe · Understand · Respond"}</span
          ><span>${zh ? "键盘快捷键 1–4" : "Keyboard shortcuts 1–4"}</span>
        </footer>
      </main>
    `,
    root,
  );
}

const shellStyles = `
  :host { display:block; height:100%; overflow:auto; color-scheme:light dark; background:var(--vh-background); }
  .shell { max-width:1500px; margin:0 auto; padding:28px 42px 16px; box-sizing:border-box; font-family:inherit; min-height:100%; }
  .topbar { display:grid; grid-template-columns:1fr minmax(350px,480px) 1fr; align-items:center; gap:24px; margin:0 0 44px; padding:0 0 24px; border-bottom:1px solid var(--vh-line); }
  .brand {display:flex; align-items:center; gap:14px; min-width:0;}
  .brand-icon {display:flex; justify-content:center; align-items:center; gap:3px; width:44px; height:44px; border-radius:14px; background:var(--vh-accent); color:var(--text-primary-color,white); flex-shrink:0;}
  .brand-icon i {width:3px; height:12px; border-radius:3px; background:currentColor;}
  .brand-icon i:nth-child(2), .brand-icon i:nth-child(4) {height:20px;} .brand-icon i:nth-child(3) {height:28px;}
  .topbar h1 {font-size:20px; font-weight:630; letter-spacing:-.035em; line-height:1.3; margin:0; white-space:nowrap;}
  .subline {font-size:11px; color:var(--vh-muted); margin-top:5px; display:block;}
  .refresh {display:flex; gap:10px; justify-content:flex-end; align-items:center;}
  .refresh .subline {margin:0; font-variant-numeric:tabular-nums;}
  .content {view-transition-name:harness-content; min-width:0;}
  .loading {min-height:400px; display:grid; place-items:center; color:var(--vh-muted);}
  .shell-footer {display:flex; gap:24px; justify-content:space-between; margin-top:38px; padding:18px 0; color:var(--vh-muted); font-size:10px; letter-spacing:.06em; border-top:1px solid var(--vh-line);}
  .shell-footer > span:first-child {font-weight:650;}
  .surface {background:var(--vh-surface); border:1px solid var(--vh-line); border-radius:20px; box-shadow:none; padding:24px;}
  h2 {font-size:18px; letter-spacing:-.02em;} h3 {font-size:15px;}
  .meta, .settingsNote, .settingsDescription {font-size:12px; line-height:1.7; color:var(--vh-muted);}
  .sectionHead {margin-bottom:20px; gap:14px;}
  .settingsForm .sectionHead h2 {font-size:18px;}
  .settingsGrid {display:grid; grid-template-columns:1fr; gap:18px;}
  .settingsForm {padding:24px; min-width:0;}
  .settingsForm .configCard {border:1px solid var(--vh-line); border-radius:16px; margin-top:16px; overflow:visible;}
  .configCard > summary {min-height:56px; font-size:14px; padding:16px 20px;}
  .configCard fieldset {padding:18px 20px; border-color:var(--vh-line); margin:0; display:grid; gap:16px;}
  .configCard fieldset:last-child {border-bottom:0;}
  .configCard legend {font-size:12px; color:var(--vh-muted);}
  .settingsForm label {font-size:13px; line-height:1.6; gap:8px;}
  .settingsForm input:not([type=checkbox]), .settingsForm textarea, .settingsForm select {border-radius:10px; border:1px solid var(--vh-line); padding:12px; background:var(--vh-background);}
  .checkRow {min-height:44px; align-items:center;}
  .settingsTriples {gap:16px;}
  .modelPicker .pickerToggle {min-height:48px; border-radius:10px; border-color:var(--vh-line); background:var(--vh-background);}
  .pickerRow, .pickerPick, .pickerProbe {min-height:44px;}
  .pickerMenu {z-index:10; border-radius:14px;}
  .modelsToolbar {gap:10px;}
  button, select, summary {min-height:44px;}
  .sound-library {margin-top:20px; padding-top:0; padding-bottom:0;}
  .sound-library > summary {padding:18px 0; font-size:14px;}
  .earconGrid {grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px;}
  .earconGrid .surface {padding:18px; margin-bottom:18px;}
  voice-harness-settings[section=audio] [data-settings-section],
  voice-harness-settings[section=routing] [data-settings-section]:not([data-settings-section=routing]),
  voice-harness-settings[section=pipeline] [data-settings-section]:not([data-settings-section=pipeline]),
  voice-harness-settings[section=system] [data-settings-section]:not([data-settings-section=system]) {display:none;}
  .satelliteLayout {display:grid; grid-template-columns:1fr; gap:18px;}
  .satelliteLayout .surface {grid-column:auto;}
  .satelliteSummary {gap:12px;}
  [slot=policies] {padding-bottom:20px;}
  @media (max-width:1150px) {.shell {padding:24px;} .topbar {grid-template-columns:1fr auto; gap:20px; margin-bottom:30px;} .topbar voice-harness-navigation {grid-column:1 / -1; grid-row:2;} .topbar .refresh {grid-column:2; grid-row:1;} }
  @media (max-width:600px) {.shell {padding:18px 16px 12px;} .topbar {margin-bottom:28px; padding-bottom:16px; gap:18px;} .topbar h1 {font-size:18px;} .brand {gap:10px;} .brand-icon {width:40px; height:40px;} .refresh .subline {display:none;} .shell-footer {font-size:9px; gap:12px; flex-wrap:wrap; margin-top:28px;} .shell-footer > span:last-child {display:none;} .surface, .settingsForm {padding:18px;} .configCard > summary {padding:14px;} .configCard fieldset {padding:14px;} .settingsTriples, .settingsTriples.two {grid-template-columns:1fr;} .earconGrid {grid-template-columns:1fr;} .modelsToolbar {flex-wrap:wrap;} .sectionHead {flex-wrap:wrap;} }
  @media (prefers-reduced-motion:reduce) {.content {view-transition-name:none;} }
`;
