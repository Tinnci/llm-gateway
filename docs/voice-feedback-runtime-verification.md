# Voice feedback runtime verification

This note records the verification path for the Earcon and Live Status work.
It is intentionally operational: every feedback feature should be visible in
trace data, in the Voice Harness UI, and through a manual debugging step.

## Consensus mapping

Earcons are short, abstract, structured status sounds. The v0 pack keeps the
surface small but covers the maintained voice states: `wake`, `captured`,
`listening_start`, `listening_end`, `processing_loop`, `thinking`, `search`,
`confirmation`, `clarification`, `provider_fallback`, `deep_task`, `success`,
`failure`, and `cancel`. The manifest records the semantic state, priority,
microphone safety, quiet-hours behavior, and trace event name for each sound.

Sound product behavior is deterministic and local. The model does not decide
when to play sounds. `VoiceFeedbackPolicy` maps pipeline events to earcons,
applies quiet-hours behavior, suppresses unsafe sounds while the microphone is
hot, and records the decision in the trace.

Lock-screen and floating display state uses a platform-neutral schema. A
`display_status_event` contains `turn_id`, short state, privacy level, progress,
action buttons, source, and a Voice Harness deep link. The maintained adapters
are the Voice Harness live banner/trace JSON and the local
Phosh/kukui-display-agent path. Android, iOS, and browser surfaces should
consume the same schema later instead of adding new status models.

Observability requires one shared turn id. `voice_runs`, diagnostic traces,
earcon events, display status events, and
`/api/llm_gateway/harness/runs/{run_id}` use the same `run_id`.

## Runtime evidence

Run the full runtime verification set:

```bash
uv run pytest tests/test_conversation.py::test_converse_records_search_feedback_trace \
  tests/test_conversation.py::test_converse_records_high_risk_confirmation_feedback \
  tests/test_conversation.py::test_converse_records_plain_feedback_without_search_overplay \
  tests/test_conversation.py::test_converse_records_failure_feedback_trace -q
```

These tests use the real Home Assistant conversation entity, runtime data,
`VoiceRunRecorder`, `VoiceFeedbackPolicy`, `TraceStore`, and diagnostic trace
serialization. The upstream OpenAI-compatible HTTP endpoint is mocked so the
test remains deterministic; the feedback, trace, and HA runtime path is real.

Expected evidence:

- Search-needed turn: trace contains `captured` and `search` earcons, a
  `searching` display event, and final `done`.
- High-risk turn: trace contains `confirmation` earcon and latest display state
  remains `confirming` with `confirm`, `cancel`, and `open_panel` actions.
- Plain state/control turn: trace contains `captured` only; no `search` or
  `thinking` overplay.
- Failure turn: trace contains `failure` earcon and latest display state is
  `failed`.

## UI evidence

Render the Voice Harness panel fixture:

```bash
fixture_url="file://$(pwd)/tools/voice-harness-ui-fixture.html"
bunx playwright screenshot --browser chromium \
  --wait-for-selector voice-harness-panel \
  --wait-for-timeout 1800 \
  --full-page "$fixture_url" /tmp/voice-harness-ui-feedback-expanded.png
```

Expected visible UI sections:

- top live banner: `实时状态: Searching`
- run detail: `首反馈决策`, `关键路径`, `搜索调试`
- feedback detail: `提示音事件`, `显示状态`
- event rows: `captured`, `search`, `searching`, `done`

The fixture uses the real `voice-harness-panel.js` custom element and the same
status payload shape returned by `/api/llm_gateway/harness/status`.

## Audio evidence

Render and lint the pack:

```bash
cd tools/ha-earcon
uv run ha-earcon render packs/ha_voice_minimal_v0.yaml \
  --out ../../custom_components/llm_gateway/frontend/earcons/ha_voice_minimal_v0
uv run ha-earcon lint \
  ../../custom_components/llm_gateway/frontend/earcons/ha_voice_minimal_v0/*.wav \
  --max-duration-ms 420 \
  --target-lufs -24 \
  --lufs-tolerance 3 \
  --max-peak-dbfs -3
```

Expected result: every wav reports `OK`.

## Manual Home Assistant steps

1. Open `/voice-harness`.
2. In `Runs`, check the live status banner at the top of the LLM Gateway card.
3. Expand a run.
4. Confirm the run detail contains `Earcons` and `Display status`.
5. For a search request, confirm `search` earcon and `searching` display state.
6. For a high-risk request, confirm `confirmation` earcon, `confirm/cancel`
   action buttons, and no unsafe HA action execution.
7. For an ordinary state/control request, confirm no unnecessary `search` or
   `thinking` earcon.
8. For a failure request, confirm `failure` earcon and trace error reason.

## Adapter matrix

Adapters should consume the same `display_status_event` without changing the
schema:

- Voice Harness: live banner, run detail, trace JSON, and deep links.
- Phosh/kukui-display-agent: local status event endpoint, lock-screen/AOD text,
  short state indicator, local cue playback, and playback stop/barge-in hooks.
- Android: notification or heads-up notification with lock-screen visibility.
- iOS: Live Activity when available, notification fallback otherwise.
- Browser: optional notification permission and floating overlay page.
