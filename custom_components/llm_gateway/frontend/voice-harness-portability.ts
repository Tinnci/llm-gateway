import { parse, stringify } from "yaml";
import { object, type EvidenceRecord } from "./voice-harness-live-model";
import type { VoiceSettings } from "./voice-harness-audio-settings";

export type TuningConfiguration = {
  gateway?: Record<string, unknown>;
  audio?: VoiceSettings;
};
const gatewayFields = [
  "routing_mode",
  "models",
  "max_tokens",
  "timeouts",
  "temperature",
  "top_p",
  "diagnostic_traces",
  "trace_include_raw_messages",
  "trace_max_runs",
  "trace_retention_hours",
];
const audioFields = [
  "wake_cue_volume",
  "follow_up_cue_volume",
  "processing_volume",
  "tts_volume_day",
  "tts_volume_night",
  "fallback_volume",
  "audio_muted",
  "night_mode",
];

export function tuningSnapshot(
  options: EvidenceRecord,
  audio: VoiceSettings,
): TuningConfiguration {
  const gateway: Record<string, unknown> = {};
  for (const key of gatewayFields.filter(
    (key) => !["models", "max_tokens", "timeouts"].includes(key),
  ))
    if (options[key] !== undefined) gateway[key] = options[key];
  for (const [key, suffix] of [
    ["models", "model"],
    ["max_tokens", "max_tokens"],
    ["timeouts", "chat_timeout"],
  ]) {
    const values = Object.fromEntries(
      ["fast", "mid", "deep"].flatMap((tier) =>
        options[tier + "_" + suffix] === undefined
          ? []
          : [[tier, options[tier + "_" + suffix]]],
      ),
    );
    if (Object.keys(values).length) gateway[key] = values;
  }
  return {
    gateway,
    audio: Object.fromEntries(
      audioFields.flatMap((key) =>
        audio[key] === undefined ? [] : [[key, audio[key]]],
      ),
    ),
  };
}

export function parseTuning(text: string): TuningConfiguration {
  const value: unknown = parse(text);
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("Configuration must be an object / 配置必须是对象");
  const input = object(value);
  if (Object.keys(input).some((key) => !["gateway", "audio"].includes(key)))
    throw new Error(
      "Import only gateway and audio tuning / 仅支持导入网关与音频调音参数",
    );
  const result: TuningConfiguration = {};
  for (const section of ["gateway", "audio"] as const) {
    if (input[section] === undefined) continue;
    if (
      !input[section] ||
      typeof input[section] !== "object" ||
      Array.isArray(input[section])
    )
      throw new Error(section + " must be an object");
    const values = object(input[section]);
    const allowed = section === "gateway" ? gatewayFields : audioFields;
    if (Object.keys(values).some((key) => !allowed.includes(key)))
      throw new Error("Unsupported tuning field / 不支持的调音字段");
    if (section === "audio") {
      for (const [key, value] of Object.entries(values)) {
        if (
          ["audio_muted", "night_mode"].includes(key)
            ? typeof value !== "boolean"
            : typeof value !== "number" ||
              !Number.isFinite(value) ||
              value < 0 ||
              value > 1
        )
          throw new Error("Invalid audio value: " + key);
      }
      result.audio = { ...values } as VoiceSettings;
    } else {
      // The config API owns range validation and concurrent-edit protection.
      result.gateway = JSON.parse(JSON.stringify(values)) as Record<
        string,
        unknown
      >;
    }
  }
  if (
    !Object.values(result).some(
      (section) => section && Object.keys(section).length,
    )
  )
    throw new Error("No tuning values found / 未找到调音参数");
  return result;
}

export function serializeTuning(
  config: TuningConfiguration,
  format: "json" | "yaml",
): string {
  return format === "json"
    ? JSON.stringify(config, null, 2) + "\n"
    : stringify(config);
}
