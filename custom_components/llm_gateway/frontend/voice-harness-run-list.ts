import { css, html, LitElement } from "lit";

import {
  harnessButtonStyles,
  harnessFoundationStyles,
} from "./voice-harness-styles";

export type HarnessRunListItem = {
  id: string;
  latency: string;
  route: string;
  status: "bad" | "ok" | "warning";
  subtitle: string;
  title: string;
};

export class VoiceHarnessRunList extends LitElement {
  static properties = {
    items: { attribute: false },
    selected: { type: String },
  };

  declare items: HarnessRunListItem[];
  declare selected: string;

  constructor() {
    super();
    this.items = [];
    this.selected = "";
  }

  render() {
    return html`
      <div role="listbox" aria-label="Voice Harness runs">
        ${this.items.map(
          (item) => html`
            <button
              aria-selected=${String(item.id === this.selected)}
              data-id=${item.id}
              role="option"
              tabindex=${item.id === this.selected ? "0" : "-1"}
              @click=${() => this.select(item.id)}
              @keydown=${this.onKeydown}
            >
              <span class="status ${item.status}" aria-hidden="true"></span>
              <span class="identity">
                <strong>${item.title}</strong>
                <small>${item.subtitle}</small>
              </span>
              <span class="facts"><small>${item.route}</small><small>${item.latency}</small></span>
            </button>
          `,
        )}
      </div>
    `;
  }

  private select(id: string): void {
    this.dispatchEvent(
      new CustomEvent<{ id: string }>("harness-run-select", {
        bubbles: true,
        composed: true,
        detail: { id },
      }),
    );
  }

  private onKeydown(event: KeyboardEvent): void {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const current = this.items.findIndex((item) => item.id === this.selected);
    let next = current < 0 ? 0 : current;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = this.items.length - 1;
    if (event.key === "ArrowUp") next = (next - 1 + this.items.length) % this.items.length;
    if (event.key === "ArrowDown") next = (next + 1) % this.items.length;
    const item = this.items[next];
    if (!item) return;
    this.select(item.id);
    this.renderRoot.querySelector<HTMLButtonElement>(
      `button[data-id="${CSS.escape(item.id)}"]`,
    )?.focus();
  }

  static styles = [harnessFoundationStyles, harnessButtonStyles, css`
    :host { display: block; min-width: 0; }
    div { display: grid; gap: var(--vh-space-xs); }
    button { width: 100%; min-height: 64px; display: grid; grid-template-columns: 8px minmax(0, 1fr) auto; gap: var(--vh-space-s); align-items: center; padding: var(--vh-space-s); background: transparent; text-align: left; }
    button:hover { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
    button[aria-selected="true"] { background: color-mix(in srgb, var(--primary-color) 13%, var(--card-background-color)); }
    .status { width: 7px; height: 7px; border-radius: 50%; background: var(--secondary-text-color); }
    .status.ok { background: var(--success-color); }
    .status.warning { background: var(--warning-color); }
    .status.bad { background: var(--error-color); }
    .identity, .facts { min-width: 0; display: grid; gap: 3px; }
    strong, small { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    strong { font-size: 12px; }
    small { color: var(--secondary-text-color); font-size: 10px; }
    .facts { justify-items: end; }
  `];
}

if (!customElements.get("voice-harness-run-list")) {
  customElements.define("voice-harness-run-list", VoiceHarnessRunList);
}

declare global {
  interface HTMLElementTagNameMap {
    "voice-harness-run-list": VoiceHarnessRunList;
  }
}
