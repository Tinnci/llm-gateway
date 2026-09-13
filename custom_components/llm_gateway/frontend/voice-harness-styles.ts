import { css } from "lit";

export const harnessFoundationStyles = css`
  :host {
    box-sizing: border-box;
    color: var(--primary-text-color, #202a32);
    font-family: var(
      --paper-font-body1_-_font-family,
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      sans-serif
    );
    --vh-ink: var(--primary-text-color, #202a32);
    --vh-muted: var(--secondary-text-color, #626f78);
    --vh-surface: var(--card-background-color, #fff);
    --vh-background: var(--primary-background-color, #f4f6f8);
    --vh-line: color-mix(
      in srgb,
      var(--divider-color, #cdd5dc) 65%,
      transparent
    );
    --vh-accent: var(--primary-color, #347c8c);
    --vh-soft: color-mix(in srgb, var(--vh-accent) 8%, var(--vh-surface));
    --vh-radius-s: 12px;
    --vh-radius-m: 20px;
    --vh-radius-l: 28px;
    --vh-space-xs: 6px;
    --vh-space-s: 12px;
    --vh-space-m: 20px;
    --vh-ease: cubic-bezier(0.2, 0.8, 0.2, 1);
    font-size: 14px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
  :host([hidden]),
  [hidden] {
    display: none !important;
  }
  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }
  h1,
  h2,
  h3,
  p {
    margin: 0;
  }
  h2 {
    font-size: clamp(22px, 2vw, 30px);
    font-weight: 650;
    letter-spacing: -0.035em;
    line-height: 1.2;
  }
  h3 {
    font-size: 16px;
    font-weight: 650;
    letter-spacing: -0.015em;
  }
  ha-icon {
    width: 22px;
    height: 22px;
    --mdc-icon-size: 22px;
    flex: 0 0 auto;
  }
  :focus-visible {
    outline: 3px solid var(--vh-accent);
    outline-offset: 3px;
  }
  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      animation: none !important;
      transition: none !important;
      scroll-behavior: auto !important;
    }
  }
`;

export const harnessButtonStyles = css`
  button,
  select,
  input,
  textarea {
    font: inherit;
    color: inherit;
  }
  button,
  select,
  input:not([type="checkbox"]):not([type="radio"]):not([type="range"]) {
    min-height: 44px;
  }
  button {
    min-width: 44px;
    border: 1px solid var(--vh-line);
    border-radius: var(--vh-radius-s);
    padding: 10px 16px;
    background: var(--vh-surface);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-weight: 550;
    transition:
      background 180ms,
      transform 180ms var(--vh-ease),
      box-shadow 180ms;
  }
  button:hover:not(:disabled) {
    background: var(--vh-soft);
    box-shadow: 0 2px 8px #00000008;
  }
  button:active:not(:disabled) {
    transform: scale(0.975);
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  button.primary {
    background: var(--vh-accent);
    color: var(--text-primary-color, white);
    border-color: transparent;
  }
  button.primary:hover:not(:disabled) {
    background: color-mix(in srgb, var(--vh-accent) 88%, var(--vh-ink));
  }
  button.quiet {
    background: transparent;
    border-color: transparent;
  }
  input,
  select,
  textarea {
    width: 100%;
    border: 1px solid var(--vh-line);
    border-radius: var(--vh-radius-s);
    background: var(--vh-background);
    padding: 10px 12px;
  }
  textarea {
    resize: vertical;
    line-height: 1.65;
  }
  label {
    display: grid;
    gap: 8px;
    font-weight: 550;
  }
  summary {
    cursor: pointer;
    min-height: 44px;
    padding: 12px 0;
  }
`;

export const harnessSurfaceStyles = css`
  .surface {
    background: var(--vh-surface);
    border: 1px solid var(--vh-line);
    border-radius: var(--vh-radius-m);
    padding: 24px;
    min-width: 0;
  }
  .muted,
  .meta {
    color: var(--vh-muted);
    font-size: 13px;
  }
  .eyebrow {
    color: var(--vh-muted);
    font-size: 11px;
    font-weight: 650;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .section-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
  }
  .section-head > div {
    min-width: 0;
    display: grid;
    gap: 8px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 550;
    background: var(--vh-background);
    color: var(--vh-muted);
    white-space: nowrap;
  }
  .ok {
    color: var(--success-color, #238675);
  }
  .warning {
    color: var(--warning-color, #ae782b);
  }
  .bad {
    color: var(--error-color, #c45050);
  }
  .chip.ok {
    background: color-mix(
      in srgb,
      var(--success-color, #238675) 10%,
      var(--vh-surface)
    );
  }
  .chip.warning {
    background: color-mix(
      in srgb,
      var(--warning-color, #ae782b) 10%,
      var(--vh-surface)
    );
  }
  .chip.bad {
    background: color-mix(
      in srgb,
      var(--error-color, #c45050) 10%,
      var(--vh-surface)
    );
  }
  .empty {
    padding: 48px 24px;
    text-align: center;
    color: var(--vh-muted);
  }
  .error {
    padding: 14px 18px;
    border-radius: var(--vh-radius-s);
    background: color-mix(
      in srgb,
      var(--error-color, #c45050) 10%,
      var(--vh-surface)
    );
    overflow-wrap: anywhere;
  }
  pre {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font: 12px/1.65 var(--code-font-family, ui-monospace, monospace);
  }
  @media (max-width: 600px) {
    .surface {
      padding: 18px;
    }
    .section-head {
      align-items: flex-start;
      flex-wrap: wrap;
    }
  }
`;
