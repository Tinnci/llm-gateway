import { escapeHtml, type Tone } from "./voice-harness-utils";

type AttrValue = string | number | boolean | null | undefined;

type ButtonOptions = {
  className?: string;
  data?: Record<string, AttrValue>;
  disabled?: boolean;
  icon?: string;
  label?: string;
  title?: string;
  type?: "button" | "submit";
};

type TabButtonOptions = {
  active: boolean;
  icon: string;
  id: string;
  label: string;
};

export function attrs(values: Record<string, AttrValue> = {}): string {
  const rendered = Object.entries(values)
    .filter(([, value]) => value !== false && value !== null && value !== undefined)
    .map(([key, value]) => value === true ? key : `${key}="${escapeHtml(value)}"`);
  return rendered.length ? ` ${rendered.join(" ")}` : "";
}

export function icon(name: string): string {
  return `<ha-icon icon="${escapeHtml(name)}"></ha-icon>`;
}

export function button(options: ButtonOptions): string {
  const className = options.className ? ` class="${escapeHtml(options.className)}"` : "";
  const title = options.title ? ` title="${escapeHtml(options.title)}"` : "";
  const disabled = options.disabled ? " disabled" : "";
  const dataAttrs = attrs(
    Object.fromEntries(
      Object.entries(options.data || {}).map(([key, value]) => [`data-${key}`, value])
    )
  );
  return `
    <button${className} type="${escapeHtml(options.type || "button")}"${title}${disabled}${dataAttrs}>
      ${options.icon ? icon(options.icon) : ""}
      ${options.label ? `<span>${escapeHtml(options.label)}</span>` : ""}
    </button>
  `;
}

export function iconButton(options: Omit<ButtonOptions, "className" | "label">): string {
  return button({ ...options, className: "iconButton" });
}

export function tabButton(options: TabButtonOptions): string {
  return button({
    className: `tab ${options.active ? "active" : ""}`.trim(),
    data: { tab: options.id },
    icon: options.icon,
    label: options.label,
  });
}

export function chip(content: unknown, tone: Tone = "muted", title = ""): string {
  return `<span class="chip ${escapeHtml(tone)}"${title ? ` title="${escapeHtml(title)}"` : ""}>${escapeHtml(content)}</span>`;
}
