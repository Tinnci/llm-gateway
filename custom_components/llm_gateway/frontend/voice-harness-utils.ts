export type RouteKind = "auto" | "fast" | "mid" | "deep";
export type FirstResponsePlaybackAdapter = "local" | "ha_media_player" | "auto";
export type Tone = "ok" | "warning" | "bad" | "error" | "muted";

export function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function safeId(value: unknown): string {
  return String(value ?? "default").replace(/[^a-zA-Z0-9_-]/g, "-");
}

export function translate(
  tables: Record<string, Record<string, string>>,
  locale: string,
  key: string,
  params: Record<string, unknown> = {}
): string {
  const table = tables[locale] || tables.en || {};
  const fallback = tables.en?.[key] || key;
  return String(table[key] || fallback).replace(/\{(\w+)\}/g, (_match, name) =>
    String(params[name] ?? "")
  );
}

export function localize(value: unknown, locale: string, fallback = ""): string {
  if (!value || typeof value !== "object") {
    return String(value || fallback);
  }
  const localized = value as Record<string, unknown>;
  return String(localized[locale] || localized.en || localized["zh-Hans"] || fallback);
}

export function routeKind(value: unknown): RouteKind {
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

export function firstResponseAdapter(value: unknown): FirstResponsePlaybackAdapter {
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

export function groundingTone(value: unknown): Tone {
  const status = String(value || "");
  if (status === "repaired") {
    return "warning";
  }
  if (["no_answer", "no_evidence", "unsupported", "verifier_error"].includes(status)) {
    return "bad";
  }
  return "ok";
}

export function formatTime(value: unknown, locale: string): string {
  if (!value) {
    return "";
  }
  const date = new Date(
    value instanceof Date || typeof value === "number" || typeof value === "string"
      ? value
      : String(value)
  );
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat(locale, {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}
