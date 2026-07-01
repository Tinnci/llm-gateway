// custom_components/llm_gateway/frontend/voice-harness-utils.ts
function escapeHtml(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
function safeId(value) {
  return String(value ?? "default").replace(/[^a-zA-Z0-9_-]/g, "-");
}
function translate(tables, locale, key, params = {}) {
  const table = tables[locale] || tables.en || {};
  const fallback = tables.en?.[key] || key;
  return String(table[key] || fallback).replace(/\{(\w+)\}/g, (_match, name) => String(params[name] ?? ""));
}
function localize(value, locale, fallback = "") {
  if (!value || typeof value !== "object") {
    return String(value || fallback);
  }
  const localized = value;
  return String(localized[locale] || localized.en || localized["zh-Hans"] || fallback);
}
function routeKind(value) {
  const candidate = String(value || "auto");
  switch (candidate) {
    case "fast":
    case "mid":
    case "deep":
    case "auto":
      return candidate;
    default:
      return "auto";
  }
}
function firstResponseAdapter(value) {
  const candidate = String(value || "local");
  switch (candidate) {
    case "ha_media_player":
    case "auto":
    case "local":
      return candidate;
    default:
      return "local";
  }
}
function groundingTone(value) {
  const status = String(value || "");
  if (status === "repaired") {
    return "warning";
  }
  if (["no_answer", "no_evidence", "unsupported", "verifier_error"].includes(status)) {
    return "bad";
  }
  return "ok";
}
function formatTime(value, locale) {
  if (!value) {
    return "";
  }
  const date = new Date(value instanceof Date || typeof value === "number" || typeof value === "string" ? value : String(value));
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat(locale, {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(date);
}

// custom_components/llm_gateway/frontend/voice-harness-ui.ts
function attrs(values = {}) {
  const rendered = Object.entries(values).filter(([, value]) => value !== false && value !== null && value !== undefined).map(([key, value]) => value === true ? key : `${key}="${escapeHtml(value)}"`);
  return rendered.length ? ` ${rendered.join(" ")}` : "";
}
function icon(name) {
  return `<ha-icon icon="${escapeHtml(name)}"></ha-icon>`;
}
function button(options) {
  const className = options.className ? ` class="${escapeHtml(options.className)}"` : "";
  const title = options.title ? ` title="${escapeHtml(options.title)}"` : "";
  const disabled = options.disabled ? " disabled" : "";
  const dataAttrs = attrs(Object.fromEntries(Object.entries(options.data || {}).map(([key, value]) => [`data-${key}`, value])));
  return `
    <button${className} type="${escapeHtml(options.type || "button")}"${title}${disabled}${dataAttrs}>
      ${options.icon ? icon(options.icon) : ""}
      ${options.label ? `<span>${escapeHtml(options.label)}</span>` : ""}
    </button>
  `;
}
function iconButton(options) {
  return button({ ...options, className: "iconButton" });
}
function tabButton(options) {
  return button({
    className: `tab ${options.active ? "active" : ""}`.trim(),
    data: { tab: options.id },
    icon: options.icon,
    label: options.label
  });
}
function chip(content, tone = "muted", title = "") {
  return `<span class="chip ${escapeHtml(tone)}"${title ? ` title="${escapeHtml(title)}"` : ""}>${escapeHtml(content)}</span>`;
}
export {
  tabButton,
  iconButton,
  icon,
  chip,
  button,
  attrs
};
