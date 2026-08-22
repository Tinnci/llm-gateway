import { css, html, LitElement, nothing } from "lit";

import { replayDiffSections, type ReplayPair } from "./voice-harness-replay-diff";

type Labels = Record<string, string>;

export class VoiceHarnessReplayInspector extends LitElement {
  static properties = {
    pair: { attribute: false },
    labels: { attribute: false },
  };

  declare pair: ReplayPair | null;
  declare labels: Labels;

  constructor() {
    super();
    this.pair = null;
    this.labels = {};
  }

  render() {
    if (!this.pair) return nothing;
    const sections = replayDiffSections(this.pair.source, this.pair.fork);
    const changed = sections.filter((section) => section.changed).length;
    return html`
      <section>
        <header>
          <div><span class="eyebrow">Replay / Fork</span><strong>Diff Inspector</strong></div>
          <span class=${changed ? "chip warning" : "chip ok"}>${changed} changed</span>
        </header>
        <div class="lineage">
          <span>${this.pair.sourceId}</span><b aria-hidden="true">→</b><span>${this.pair.forkId}</span>
        </div>
        <div class="sections">
          ${sections.map((item) => html`
            <details class="diff" ?open=${item.changed}>
              <summary>
                <strong>${this.labels[item.id] || item.id}</strong>
                <span class=${item.changed ? "chip warning" : "chip muted"}>
                  ${item.changed ? "changed" : "unchanged"}
                </span>
              </summary>
              <pre>${item.parts.map((part) => html`<span class=${part.added ? "added" : part.removed ? "removed" : "same"}>${part.value}</span>`)}</pre>
            </details>
          `)}
        </div>
      </section>
    `;
  }

  static styles = css`
    :host { display: block; margin: 14px 0; color: var(--primary-text-color); }
    section { overflow: hidden; border: 1px solid var(--divider-color); border-radius: 8px; background: var(--card-background-color); }
    header { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 48px; padding: 0 12px; border-bottom: 1px solid var(--divider-color); }
    header > div { display: grid; gap: 2px; }
    .eyebrow { color: var(--secondary-text-color); font-size: 10px; font-weight: 650; letter-spacing: .04em; text-transform: uppercase; }
    .chip { display: inline-flex; align-items: center; min-height: 20px; padding: 0 7px; border-radius: 999px; font-size: 10px; font-weight: 650; }
    .warning { background: color-mix(in srgb, var(--warning-color, #f9a825) 16%, transparent); color: var(--warning-color, #a66a00); }
    .ok { background: color-mix(in srgb, var(--success-color, #43a047) 15%, transparent); color: var(--success-color, #2e7d32); }
    .muted { background: color-mix(in srgb, var(--secondary-text-color) 11%, transparent); color: var(--secondary-text-color); }
    .lineage { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid var(--divider-color); color: var(--secondary-text-color); font-family: var(--code-font-family, Menlo, Consolas, monospace); font-size: 10px; }
    .lineage span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .lineage b { color: var(--primary-color); }
    .sections { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .diff { min-width: 0; border-right: 1px solid var(--divider-color); border-bottom: 1px solid var(--divider-color); }
    .diff:nth-child(2n) { border-right: 0; }
    summary { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 38px; padding: 0 10px; cursor: pointer; font-size: 11px; }
    pre { max-height: 220px; margin: 0; padding: 8px 10px; overflow: auto; border-top: 1px solid var(--divider-color); background: var(--primary-background-color); font: 10px/1.5 var(--code-font-family, Menlo, Consolas, monospace); white-space: pre-wrap; }
    pre span { display: block; margin: 0 -10px; padding: 0 10px; }
    .added { background: color-mix(in srgb, var(--success-color, #43a047) 16%, transparent); color: var(--success-color, #2e7d32); }
    .removed { background: color-mix(in srgb, var(--error-color) 13%, transparent); color: var(--error-color); text-decoration: line-through; }
    @media (max-width: 560px) { .sections { grid-template-columns: 1fr; } .diff { border-right: 0; } }
  `;
}

if (!customElements.get("voice-harness-replay-inspector")) {
  customElements.define("voice-harness-replay-inspector", VoiceHarnessReplayInspector);
}
