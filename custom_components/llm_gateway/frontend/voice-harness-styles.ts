import { css } from "lit";

export const harnessFoundationStyles = css`
  :host {
    box-sizing: border-box;
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, inherit);
    --vh-radius-s: 7px;
    --vh-radius-m: 10px;
    --vh-space-xs: 4px;
    --vh-space-s: 8px;
    --vh-space-m: 12px;
  }

  *,
  *::before,
  *::after {
    box-sizing: inherit;
  }
`;

export const harnessButtonStyles = css`
  button {
    min-height: 40px;
    border: 0;
    border-radius: var(--vh-radius-s);
    color: inherit;
    font: inherit;
    cursor: pointer;
  }

  button:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: -2px;
  }
`;
