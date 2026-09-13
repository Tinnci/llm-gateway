import { expect, test } from "bun:test";
import {
  parseTuning,
  serializeTuning,
  tuningSnapshot,
} from "../../custom_components/llm_gateway/frontend/voice-harness-portability";

test("tuning exports exclude secrets and unrelated runtime values", () => {
  const config = tuningSnapshot(
    {
      fast_model: "fast",
      prompt: "private",
      api_key: "secret",
      provider_profiles: [{ api_key: "hidden" }],
      fast_chat_timeout: 30,
      trace_max_runs: 20,
    },
    { tts_volume_day: 1, audio_muted: false, hidden: 2 },
  );
  const json = serializeTuning(config, "json");
  expect(json).not.toContain("secret");
  expect(json).not.toContain("private");
  expect(json).not.toContain("hidden");
  expect(config.gateway?.models).toEqual({ fast: "fast" });
  expect(config.gateway?.timeouts).toEqual({ fast: 30 });
  expect(config.audio?.audio_muted).toBe(false);
  expect(parseTuning(serializeTuning(config, "yaml"))).toEqual(config);
});

test("unsafe imported fields and invalid gains fail before any update", () => {
  expect(() => parseTuning("gateway:\n  api_key: secret")).toThrow();
  expect(() => parseTuning("audio:\n  tts_volume_day: 8")).toThrow();
  expect(() => parseTuning('audio:\n  audio_muted: "false"')).toThrow();
  expect(() => parseTuning("audio: null")).toThrow();
  expect(() => parseTuning("{}")).toThrow();
});

test("mute and night mode survive JSON and YAML round trips", () => {
  const config = tuningSnapshot(
    {},
    { audio_muted: true, night_mode: true, tts_volume_night: 0.42 },
  );
  for (const format of ["json", "yaml"] as const) {
    expect(parseTuning(serializeTuning(config, format)).audio).toEqual({
      audio_muted: true,
      night_mode: true,
      tts_volume_night: 0.42,
    });
  }
});
