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

## 2026-07-17 Kukui text-API evidence

This verification used Home Assistant's text Conversation API on
`google-kukui`; it did not capture, synthesize, or play audio and therefore does
not replace the wake/ASR/TTS smoke test.

- Run `01KXR1SJDDW85SKZFXHEJMFJPP` answered `外面的风速是多少？` with only
  `静安现在东北风，风速 2 km/h。` through `local_weather` in 123 ms.
- Run `01KXR1QN6H1FB49YSYD7ME1WMV` committed `打开所有灯。` directly as
  `target_scope=all`; it did not enter clarification or call an LLM.
- The batch action excluded two unavailable lights and the Xiaomi fan indicator
  light (`entity_category:config`), and skipped two lights that were already on.
- During post-restart warm-up, the two remaining Yeelight service calls both
  raised `RuntimeError`, so the spoken result correctly reported execution
  failure. The trace retained `attempted_count=2`, `succeeded_count=0`,
  `failed_count=2`, and both bounded failed entity ids. One timed-out cloud
  action committed about 20 seconds later, proving that HA entity availability
  alone is not a complete cloud-control readiness signal.
- After the Xiaomi control path stabilized, run
  `01KXR27ABBT6EA44H3DTAKC0H1` executed the same request in 419 ms. It attempted
  two eligible off lights, succeeded on both, skipped two already-on lights,
  excluded the same indicator/unavailable entities, and answered
  `已打开所有灯。`. The two changed lights were restored to their original off
  state and monitored for 30 seconds with no late state change.
- Both stored runs carried `projection=recorder_safe_compact`, `complete=false`,
  `check_count=30`, and status counts `25 ok / 1 warning / 0 error / 4 blocked`.
  Earlier code incorrectly recomputed this projection as `0 ok`; the target
  trace now preserves the Recorder-safe totals.
- A same-conversation regression used caller-supplied id
  `codex-device-weather-20260717-final`. Run
  `01KXR3GNA391MBRYM8F71NG2CW` asked which light should be turned off and
  executed no action. The unrelated follow-up `外面的风速是多少？` became run
  `01KXR3GP457PR8D29PXWPZCWCZ`, suspended the `home_control` frame, cleared the
  active frame stack, and answered only `静安现在西风，风速 1 km/h。` through
  `local_weather` in 160 ms.
- The follow-up trace recorded `dialogue_relation=new_task`,
  `interaction_state=suspended`, and the display event
  `已取消上一操作，正在处理新请求。`. The event is display-only: the trace had
  the ordinary `captured` earcon and no cancellation earcon. No Home Assistant
  action was executed in either turn.

## 2026-07-12 retained-run baseline

The six Voice Harness runs retained on the deployed Home Assistant instance
were all complete. Their Gateway latency ranged from 69 to 202 ms, averaging
about 145 ms. Available ASR trace fields showed roughly 4 seconds to the final
result and about 1.7 seconds to the first result, so the dominant perceived
delay was upstream of Gateway routing.

The review found four user-visible defects: a wind-only question returned the
full weather summary, an explicit all-lights request entered clarification,
ambiguous-device prompts exposed integration-oriented entity names, and an
unrelated weather request silently left an earlier light clarification active.
The 2026-07-17 deployment fixes the scalar-weather, explicit batch-scope, and
silent frame-suspension defects. Friendly aliasing for ambiguous device
candidates remains follow-up work.

## Adapter matrix

Adapters should consume the same `display_status_event` without changing the
schema:

- Voice Harness: live banner, run detail, trace JSON, and deep links.
- Phosh/kukui-display-agent: local status event endpoint, lock-screen/AOD text,
  short state indicator, local cue playback, and playback stop/barge-in hooks.
- Android: notification or heads-up notification with lock-screen visibility.
- iOS: Live Activity when available, notification fallback otherwise.
- Browser: optional notification permission and floating overlay page.
