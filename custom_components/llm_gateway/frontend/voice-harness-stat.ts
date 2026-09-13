import { css, html, LitElement, nothing, svg } from "lit";
import { sparkline } from "./voice-harness-live-model";
import { harnessFoundationStyles } from "./voice-harness-styles";

type StatTone = "bad" | "muted" | "ok" | "warning";

export class VoiceHarnessStat extends LitElement {
  static properties = {
    icon: {},
    label: {},
    tone: { reflect: true },
    value: {},
    hint: {},
    values: { attribute: false },
  };
  declare icon: string;
  declare label: string;
  declare tone: StatTone;
  declare value: string;
  declare hint: string;
  declare values: number[];
  constructor() {
    super();
    this.icon = "";
    this.label = "";
    this.tone = "muted";
    this.value = "";
    this.hint = "";
    this.values = [];
  }
  render() {
    const points = sparkline(this.values);
    return html`
      <div class="label">
        ${this.icon ? html`<ha-icon icon=${this.icon}></ha-icon>` : nothing}<span
          >${this.label}</span
        >
      </div>
      <strong>${this.value || "—"}</strong>
      <small>${this.hint}</small>
      ${points ? svg`<svg viewBox="0 0 180 42" preserveAspectRatio="none" aria-hidden="true"><polyline points=${points} fill="none" stroke="currentColor" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" stroke-linecap="round" /></svg>` : nothing}
    `;
  }
  static styles = [
    harnessFoundationStyles,
    css`
      :host {
        display: grid;
        align-content: start;
        position: relative;
        min-height: 170px;
        gap: 10px;
        padding: 22px;
        border: 1px solid var(--vh-line);
        border-radius: var(--vh-radius-m);
        background: var(--vh-surface);
        overflow: hidden;
      }
      .label {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--vh-muted);
        font-size: 13px;
      }
      ha-icon {
        width: 18px;
        height: 18px;
        --mdc-icon-size: 18px;
      }
      strong {
        font-size: clamp(26px, 3vw, 40px);
        font-weight: 570;
        letter-spacing: -0.045em;
        line-height: 1.15;
        font-variant-numeric: tabular-nums;
        z-index: 1;
        overflow-wrap: anywhere;
      }
      small {
        color: var(--vh-muted);
        font-size: 11px;
        z-index: 1;
        max-width: 70%;
      }
      svg {
        position: absolute;
        right: 16px;
        bottom: 12px;
        width: 42%;
        height: 32px;
        color: var(--vh-accent);
        opacity: 0.7;
      }
      :host([tone="bad"]) svg {
        color: var(--error-color, #c45050);
      }
      :host([tone="ok"]) svg {
        color: var(--success-color, #238675);
      }
      @media (max-width: 600px) {
        :host {
          min-height: 150px;
          padding: 18px;
        }
        strong {
          font-size: 28px;
        }
        .label {
          font-size: 12px;
        }
      }
    `,
  ];
}
if (!customElements.get("voice-harness-stat"))
  customElements.define("voice-harness-stat", VoiceHarnessStat);
declare global {
  interface HTMLElementTagNameMap {
    "voice-harness-stat": VoiceHarnessStat;
  }
}
