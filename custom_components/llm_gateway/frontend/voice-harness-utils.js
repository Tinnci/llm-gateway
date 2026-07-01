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
export {
  translate,
  safeId,
  routeKind,
  localize,
  groundingTone,
  formatTime,
  firstResponseAdapter,
  escapeHtml
};
