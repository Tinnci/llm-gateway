import { css, html, LitElement } from "lit";

import {
  harnessButtonStyles,
  harnessFoundationStyles,
} from "./voice-harness-styles";

export type HarnessNavigationItem = {
  icon: string;
  id: string;
  label: string;
};

export type HarnessViewSelectDetail = {
  id: string;
};

export class VoiceHarnessNavigation extends LitElement {
  static properties = {
    active: { type: String },
    items: { attribute: false },
  };

  declare active: string;
  declare items: HarnessNavigationItem[];

  constructor() {
    super();
    this.active = "";
    this.items = [];
  }

  render() {
    return html`
      <nav aria-label="Voice Harness views" role="tablist">
        ${this.items.map(
          (item) => html`
            <button
              aria-selected=${String(item.id === this.active)}
              data-id=${item.id}
              role="tab"
              tabindex=${item.id === this.active ? "0" : "-1"}
              @click=${() => this.select(item.id)}
              @keydown=${this.onKeydown}
            >
              <ha-icon icon=${item.icon}></ha-icon>
              <span>${item.label}</span>
            </button>
          `,
        )}
      </nav>
    `;
  }

  private select(id: string): void {
    this.dispatchEvent(
      new CustomEvent<HarnessViewSelectDetail>("harness-view-select", {
        bubbles: true,
        composed: true,
        detail: { id },
      }),
    );
  }

  private onKeydown(event: KeyboardEvent): void {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      return;
    }
    event.preventDefault();
    const current = this.items.findIndex((item) => item.id === this.active);
    let next = current < 0 ? 0 : current;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = this.items.length - 1;
    if (event.key === "ArrowLeft") next = (next - 1 + this.items.length) % this.items.length;
    if (event.key === "ArrowRight") next = (next + 1) % this.items.length;
    const item = this.items[next];
    if (!item) return;
    this.select(item.id);
    const button = this.renderRoot.querySelector<HTMLButtonElement>(
      `button[data-id="${CSS.escape(item.id)}"]`,
    );
    button?.focus();
  }

  static styles = [harnessFoundationStyles, harnessButtonStyles, css`
    :host { display: block; margin: 14px 0 18px; }
    nav { display: flex; gap: var(--vh-space-xs); padding: var(--vh-space-xs); overflow-x: auto; border: 1px solid var(--divider-color); border-radius: var(--vh-radius-m); background: var(--card-background-color); }
    button { min-width: 0; flex: 1 0 132px; display: inline-flex; align-items: center; justify-content: center; gap: var(--vh-space-s); padding: 0 var(--vh-space-m); background: transparent; white-space: nowrap; }
    button:hover { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
    button[aria-selected="true"] { background: color-mix(in srgb, var(--primary-color) 14%, var(--card-background-color)); color: var(--primary-color); }
    ha-icon { width: 20px; height: 20px; flex: 0 0 auto; }
    span { min-width: 0; overflow: hidden; text-overflow: ellipsis; }
    @media (max-width: 560px) { button { flex-basis: 112px; justify-content: flex-start; } }
  `];
}

if (!customElements.get("voice-harness-navigation")) {
  customElements.define("voice-harness-navigation", VoiceHarnessNavigation);
}

declare global {
  interface HTMLElementTagNameMap {
    "voice-harness-navigation": VoiceHarnessNavigation;
  }
}
