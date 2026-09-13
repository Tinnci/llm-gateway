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
    if (event.key === "ArrowLeft")
      next = (next - 1 + this.items.length) % this.items.length;
    if (event.key === "ArrowRight") next = (next + 1) % this.items.length;
    const item = this.items[next];
    if (!item) return;
    this.select(item.id);
    const button = this.renderRoot.querySelector<HTMLButtonElement>(
      `button[data-id="${CSS.escape(item.id)}"]`,
    );
    button?.focus();
  }

  static styles = [
    harnessFoundationStyles,
    harnessButtonStyles,
    css`
      :host {
        display: block;
        margin: 0;
      }
      nav {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 4px;
        padding: 5px;
        border: 1px solid var(--vh-line);
        border-radius: 16px;
        background: var(--vh-surface);
      }
      button {
        min-width: 0;
        min-height: 46px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 0 10px;
        background: transparent;
        white-space: nowrap;
      }
      button:hover {
        background: color-mix(in srgb, var(--primary-color) 8%, transparent);
      }
      button[aria-selected="true"] {
        background: var(--vh-soft);
        color: var(--vh-accent);
      }
      ha-icon {
        width: 20px;
        height: 20px;
        flex: 0 0 auto;
      }
      span {
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      @media (max-width: 560px) {
        button {
          padding: 8px 4px;
          flex-direction: column;
          gap: 4px;
          font-size: 11px;
          min-height: 60px;
        }
        ha-icon {
          width: 18px;
          height: 18px;
          --mdc-icon-size: 18px;
        }
      }
    `,
  ];
}

if (!customElements.get("voice-harness-navigation")) {
  customElements.define("voice-harness-navigation", VoiceHarnessNavigation);
}

declare global {
  interface HTMLElementTagNameMap {
    "voice-harness-navigation": VoiceHarnessNavigation;
  }
}
