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
