import { expect, test } from "bun:test";

import { replayDiffSections } from "../../custom_components/llm_gateway/frontend/voice-harness-replay-diff";

test("compares route, actions, speech, and event trajectory", () => {
  const sections = replayDiffSections(
    {
      route: { kind: "fast", model: "a" },
      proposed_actions: [{ service: "light.turn_off" }],
      final_speech_text: "已关闭",
      timeline: [{ stage: "route", status: "ok", t_ms: 10 }],
    },
    {
      route: { kind: "mid", model: "b" },
      proposed_actions: [{ service: "light.turn_on" }],
      final_speech_text: "已打开",
      timeline: [{ stage: "route", status: "ok", t_ms: 12 }],
    },
  );

  expect(sections.map((section) => section.id)).toEqual([
    "route",
    "actions",
    "speech",
    "events",
  ]);
  expect(sections.every((section) => section.changed)).toBe(true);
  expect(sections[0].parts.some((part) => part.added)).toBe(true);
  expect(sections[0].parts.some((part) => part.removed)).toBe(true);
});

test("partial records produce stable unchanged sections", () => {
  const sections = replayDiffSections({}, {});
  expect(sections.every((section) => !section.changed)).toBe(true);
});
