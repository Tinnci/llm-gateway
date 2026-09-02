import { css, html, LitElement } from "lit";

import { harnessFoundationStyles } from "./voice-harness-styles";

type StatTone = "bad" | "muted" | "ok" | "warning";

export class VoiceHarnessStat extends LitElement {
  static properties = {
    icon: { type: String },
    label: { type: String },
    tone: { reflect: true, type: String },
    value: { type: String },
  };

  declare icon: string;
  declare label: string;
  declare tone: StatTone;
  declare value: string;

  constructor() {
    super();
    this.icon = "mdi:information-outline";
    this.label = "";
    this.tone = "muted";
    this.value = "";
  }

  render() {
    return html`
      <ha-icon icon=${this.icon}></ha-icon>
      <div><span>${this.label}</span><strong>${this.value || "-"}</strong></div>
    `;
  }

  static styles = [harnessFoundationStyles, css`
    :host { min-height: 66px; display: grid; grid-template-columns: 26px minmax(0, 1fr); gap: 8px; align-items: center; padding: 10px; border: 1px solid var(--divider-color); border-radius: 8px; background: var(--card-background-color); box-sizing: border-box; }
    :host([tone="ok"]) { border-color: color-mix(in srgb, var(--success-color) 30%, var(--divider-color)); }
    :host([tone="warning"]) { border-color: color-mix(in srgb, var(--warning-color) 38%, var(--divider-color)); }
    :host([tone="bad"]) { border-color: color-mix(in srgb, var(--error-color) 38%, var(--divider-color)); }
    ha-icon { width: 22px; height: 22px; color: var(--secondary-text-color); }
    div { min-width: 0; display: grid; gap: 2px; }
    span { color: var(--secondary-text-color); font-size: 12px; overflow: hidden; text-overflow: ellipsis; }
    strong { min-width: 0; font-size: 14px; line-height: 1.25; overflow-wrap: anywhere; }
  `];
}

if (!customElements.get("voice-harness-stat")) {
  customElements.define("voice-harness-stat", VoiceHarnessStat);
}

declare global {
  interface HTMLElementTagNameMap {
    "voice-harness-stat": VoiceHarnessStat;
  }
}
