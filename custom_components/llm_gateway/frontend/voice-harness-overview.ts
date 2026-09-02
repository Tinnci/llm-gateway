import { css, html, LitElement, nothing } from "lit";

import {
  harnessButtonStyles,
  harnessFoundationStyles,
} from "./voice-harness-styles";
import "./voice-harness-stat";

export type HarnessOverviewDestination = "runs" | "test";
export type HarnessOverviewTone = "bad" | "muted" | "ok" | "warning";

export type HarnessOverviewMetric = {
  icon: string;
  label: string;
  tone: HarnessOverviewTone;
  value: string;
};

export type HarnessOverviewModel = {
  actions: Array<{ destination: HarnessOverviewDestination; icon: string; label: string }>;
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
  };

  declare model: HarnessOverviewModel | null;
  declare openSections: string[];

  constructor() {
    super();
    this.model = null;
    this.openSections = [];
  }

  render() {
    const model = this.model;
    if (!model) return nothing;
    return html`
      <section class="surface hero" aria-label=${model.ariaLabel}>
        <header>
          <div>
            <h2>${model.headline}</h2>
            <span class="meta">${model.statusLine}</span>
          </div>
          <span class="chip ${model.stateTone}">${model.stateLabel}</span>
        </header>
        <div class="metrics">
          ${model.metrics.map(
            (metric) => html`
              <voice-harness-stat
                .icon=${metric.icon}
                .label=${metric.label}
                .tone=${metric.tone}
                .value=${metric.value}
              ></voice-harness-stat>
            `,
          )}
        </div>
        <div class="focus ${model.stateTone}">
          <ha-icon icon=${model.focusIcon}></ha-icon>
          <div>
            <strong>${model.focusTitle}</strong>
            <span>${model.focusHint}</span>
          </div>
          <div class="actions">
            ${model.actions.map(
              (action) => html`
                <button @click=${() => this.navigate(action.destination)}>
                  <ha-icon icon=${action.icon}></ha-icon>
                  <span>${action.label}</span>
                </button>
              `,
            )}
          </div>
        </div>
      </section>
      <slot name="satellite"></slot>
      ${this.disclosure("diagnostics", model.diagnosticsLabel)}
      ${this.disclosure("memory", model.memoryLabel)}
    `;
  }

  private disclosure(id: "diagnostics" | "memory", label: string) {
    return html`
      <details
        class="surface disclosure"
        .open=${this.openSections.includes(id)}
        @toggle=${(event: Event) => this.onToggle(id, event)}
      >
        <summary>${label}</summary>
        <slot name=${id}></slot>
      </details>
    `;
  }

  private navigate(destination: HarnessOverviewDestination): void {
    this.dispatchEvent(
      new CustomEvent<{ destination: HarnessOverviewDestination }>(
        "harness-overview-navigate",
        {
          bubbles: true,
          composed: true,
          detail: { destination },
        },
      ),
    );
  }

  private onToggle(id: "diagnostics" | "memory", event: Event): void {
    const details = event.currentTarget;
    if (!(details instanceof HTMLDetailsElement)) return;
    this.dispatchEvent(
      new CustomEvent<{ id: "diagnostics" | "memory"; open: boolean }>(
        "harness-overview-disclosure-toggle",
        {
          bubbles: true,
          composed: true,
          detail: { id, open: details.open },
        },
      ),
    );
  }

  static styles = [harnessFoundationStyles, harnessButtonStyles, css`
    :host { display: grid; gap: 14px; }
    .surface { background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 8px; }
    .hero { padding: 16px; }
    header { min-height: 42px; display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
    header > div { min-width: 0; }
    h2 { margin: 0 0 4px; font-size: 16px; }
    .meta { color: var(--secondary-text-color); font-size: 12px; line-height: 1.4; }
    .chip { display: inline-flex; align-items: center; min-height: 26px; padding: 0 9px; border: 1px solid var(--divider-color); border-radius: 999px; font-size: 11px; white-space: nowrap; }
    .chip.ok { color: var(--success-color); border-color: color-mix(in srgb, var(--success-color) 35%, var(--divider-color)); }
    .chip.warning { color: var(--warning-color); border-color: color-mix(in srgb, var(--warning-color) 42%, var(--divider-color)); }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
    .focus { min-height: 72px; display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; gap: 12px; align-items: center; margin-top: 12px; padding: 12px; border: 1px solid var(--divider-color); border-radius: 8px; background: var(--primary-background-color); }
    .focus.ok { border-color: color-mix(in srgb, var(--success-color) 30%, var(--divider-color)); }
    .focus.warning { border-color: color-mix(in srgb, var(--warning-color) 42%, var(--divider-color)); }
    .focus > ha-icon { width: 24px; height: 24px; color: var(--secondary-text-color); }
    .focus > div:nth-child(2) { min-width: 0; display: grid; gap: 4px; }
    .focus strong { font-size: 14px; }
    .focus span { color: var(--secondary-text-color); font-size: 12px; line-height: 1.4; }
    .actions { display: flex; gap: 8px; }
    button { display: inline-flex; align-items: center; gap: 8px; padding: 0 14px; background: var(--secondary-background-color); border: 1px solid var(--divider-color); }
    button:hover { background: color-mix(in srgb, var(--primary-color) 8%, var(--secondary-background-color)); }
    .disclosure { padding: 0; overflow: hidden; }
    summary { min-height: 48px; display: flex; align-items: center; padding: 0 16px; cursor: pointer; font-size: 14px; font-weight: 650; }
    details[open] > summary { border-bottom: 1px solid var(--divider-color); }
    ::slotted(.overview-slot) { display: block; margin: 14px; }
    slot[name="satellite"]::slotted(.overview-slot) { margin: 0; }
    @media (max-width: 900px) {
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .focus { grid-template-columns: 28px minmax(0, 1fr); }
      .actions { grid-column: 2; justify-content: flex-start; }
    }
    @media (max-width: 560px) {
      .metrics { grid-template-columns: 1fr; }
      .focus { grid-template-columns: 1fr; }
      .actions { grid-column: 1; flex-direction: column; }
      button { width: 100%; justify-content: center; }
    }
  `];
}

if (!customElements.get("voice-harness-overview")) {
  customElements.define("voice-harness-overview", VoiceHarnessOverview);
}

declare global {
  interface HTMLElementTagNameMap {
    "voice-harness-overview": VoiceHarnessOverview;
  }
}
