import { afterAll, expect, test } from "bun:test";
import { Window } from "happy-dom";

const dom = new Window();
for (const key of ["window", "document", "customElements", "HTMLElement", "Document", "CSSStyleSheet", "ShadowRoot", "Node"] as const) {
  Object.assign(globalThis, { [key]: key === "window" ? dom : dom[key] });
}
const { VoiceSettingsSaver, voiceSettingsRequest, VoiceHarnessAudioSettings } = await import("../../custom_components/llm_gateway/frontend/voice-harness-audio-settings");
afterAll(() => dom.close());

test("the mounted Lit card renders and updates its language", async () => {
  const card = new VoiceHarnessAudioSettings();
  card.hass = { language: "zh-Hans", callApi: async () => ({ service_response: {
    status: 200, content: { ok: true, config: { wake_cue_volume: 1 }, apply: { applied: true } },
  } }) };
  document.body.append(card);
  try {
    await card.updateComplete;
    expect(card.shadowRoot?.textContent).toContain("平板声音");
    card.language = "en";
    await card.updateComplete;
    expect(card.shadowRoot?.textContent).toContain("Tablet audio");
  } finally {
    card.remove();
  }
});

test("an edit during save survives the older response and is applied next", async () => {
  const calls: Record<string, number | boolean>[] = [];
  let release!: () => void;
  const wait = new Promise<void>((resolve) => { release = resolve; });
  const saver = new VoiceSettingsSaver(async (patch) => {
    calls.push(patch);
    if (calls.length === 1) await wait;
    return { ok: true, config: patch, apply: { applied: true } };
  }, () => {});
  saver.edit("wake_cue_volume", 0.6);
  const saved = saver.flush();
  expect(saver.inflight.wake_cue_volume).toBe(0.6);
  saver.edit("wake_cue_volume", 0.9);
  release();
  await saved;
  expect(calls).toEqual([{ wake_cue_volume: 0.6 }, { wake_cue_volume: 0.9 }]);
  expect(saver.saved.wake_cue_volume).toBe(0.9);
  expect(saver.pending).toEqual({});
});

test("failed application retains the draft for retry", async () => {
  let applied = false;
  const saver = new VoiceSettingsSaver(async (patch) => ({ ok: true, config: patch, apply: { applied } }), () => {});
  saver.edit("audio_muted", true);
  await expect(saver.flush()).rejects.toThrow("could not be applied");
  expect(saver.pending.audio_muted).toBe(true);
  expect(saver.applied).toBe(false);
  applied = true;
  await saver.flush();
  expect(saver.applied).toBe(true);
});

test("HA service dispatch without an agent response is not confirmation", async () => {
  await expect(voiceSettingsRequest({ callApi: async () => ({}) }, "preview", { field: "wake_cue_volume" })).rejects.toThrow("did not apply");
  const requests: unknown[] = [];
  await voiceSettingsRequest({ callApi: async (...args) => {
    requests.push(args);
    return { service_response: { status: 200, content: { ok: true, status: "played" } } };
  } }, "preview", { field: "wake_cue_volume" });
  expect(requests[0]).toEqual(["POST", "services/rest_command/kukui_voice_audio_preview?return_response", { field: "wake_cue_volume" }]);
});

test("a preview response must contain player completion or intentional mute", async () => {
  await expect(voiceSettingsRequest({ callApi: async () => ({ service_response: {
    status: 200, content: { ok: true, status: "sent" },
  } }) }, "preview", { field: "wake_cue_volume" })).rejects.toThrow("not confirmed");
});

test("a scene saves one partial patch after the 400 ms quiet period", async () => {
  const calls: unknown[] = [];
  const saver = new VoiceSettingsSaver(async (patch) => {
    calls.push(patch);
    return { ok: true, config: patch, apply: { applied: true } };
  }, () => {});
  saver.editPatch({ wake_cue_volume: 0.7, follow_up_cue_volume: 0.75 });
  await Bun.sleep(200);
  saver.edit("wake_cue_volume", 0.8);
  await Bun.sleep(250);
  expect(calls).toEqual([]);
  await Bun.sleep(180);
  expect(calls).toEqual([{ wake_cue_volume: 0.8, follow_up_cue_volume: 0.75 }]);
});

test("saved snapshots do not retain mutable response references", async () => {
  const config = { wake_cue_volume: 0.7 };
  const saver = new VoiceSettingsSaver(async () => ({ ok: true, config, apply: { applied: true } }), () => {});
  saver.edit("wake_cue_volume", 0.7);
  await saver.flush();
  config.wake_cue_volume = 0.2;
  expect(saver.saved.wake_cue_volume).toBe(0.7);
});

const envelope = (config: Record<string, number | boolean>, applied = true) => ({ service_response: {
  status: 200, content: { ok: true, config, apply: { applied }, runtime: { capture: "wake_word", phase: "idle", tts_profile: "day", tts_volume: 1 } },
} });

test("refresh merges an external mute while preserving an unsaved slider edit", async () => {
  const card = new VoiceHarnessAudioSettings();
  card.hass = { callApi: async () => envelope({ wake_cue_volume: 1, audio_muted: true }) };
  card.saver.edit("wake_cue_volume", 0.6);
  await card.refresh();
  expect(card.saver.saved.audio_muted).toBe(true);
  expect(card.saver.pending.wake_cue_volume).toBe(0.6);
  await card.saver.flush();
});

test("a read started before a save cannot rewind the applied slider", async () => {
  let finishRead!: (response: unknown) => void;
  const read = new Promise((resolve) => { finishRead = resolve; });
  const card = new VoiceHarnessAudioSettings();
  card.hass = { callApi: async (_method, path) => path.includes("_read") ? read : envelope({ wake_cue_volume: 0.8 }) };
  const refreshing = card.refresh();
  card.saver.edit("wake_cue_volume", 0.8);
  await card.saver.flush();
  finishRead(envelope({ wake_cue_volume: 1 }));
  await refreshing;
  expect(card.saver.saved.wake_cue_volume).toBe(0.8);
});

test("scene selection preserves mute and sends every scene value together", async () => {
  let config = { wake_cue_volume: 1, follow_up_cue_volume: 1, tts_volume_day: 1, tts_volume_night: 0.72,
    processing_volume: 0.58, fallback_volume: 1, audio_muted: true, night_mode: false };
  const patches: unknown[] = [];
  const card = new VoiceHarnessAudioSettings();
  card.hass = { language: "en", callApi: async (_method, path, data) => {
    if (path.includes("_update")) {
      const patch = (data as { config: typeof config }).config;
      patches.push(patch);
      config = { ...config, ...patch };
    }
    return envelope(config);
  } };
  document.body.append(card);
  try {
    await card.refresh();
    await card.updateComplete;
    const button = [...card.shadowRoot!.querySelectorAll("button")].find((item) => item.textContent?.includes("Focus"));
    expect(button).toBeDefined();
    button!.click();
    await card.saver.flush();
    expect(patches).toHaveLength(1);
    expect(config.processing_volume).toBe(0.25);
    expect(config.audio_muted).toBe(true);
  } finally { card.remove(); }
});
