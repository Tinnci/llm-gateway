# Voice feedback runtime verification

This note records the verification path for the Earcon and Live Status work.
It is intentionally operational: every feedback feature should be visible in
trace data, in the Voice Harness UI, and through a manual debugging step.

## Consensus mapping

Earcons are short, abstract, structured status sounds. The v0 pack keeps the
surface small but covers the maintained voice states: `wake`, `follow_up`, `captured`,
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

Scheduling an earcon leaves `played_at_ms` unknown. A completed HA playback
service call records `dispatched=true`, `played=false`; it cannot establish
physical playback time. First-response updates replace stored snapshots and
return copies. The satellite independently reports player completion and the
opening of a follow-up capture window. The dedicated follow-up cue belongs to
that capture callback, not the model's request to continue.

提示音计划、HA 服务下发、播放器退出与真实听感分别记录。仅有服务成功返回时，
Harness 显示“已下发，播放未确认”；不会用计划时间伪造播放时间。

## Audio settings / 声音设置

The Lit audio card groups wake/follow-up, day/night speech and status feedback.
Edits debounce for 400 ms, serialize partial updates and hot-apply in the display
agent. A failed save retains pending edits for retry. Preview first flushes edits
and accepts only six fixed audio fields. Mute and night mode share the same
settings as the lock-screen buttons. The UI caps linear gain at 1.0.

Install the updated `phosh-ha-status/home-assistant/packages/kukui_display.yaml`
and satellite agent together. The card calls `rest_command.kukui_voice_config_read`,
`kukui_voice_config_update` and `kukui_voice_audio_preview` with HA's
`?return_response`; a successful service transport without a successful agent
response is an error. Add `/llm_gateway/static/voice-harness-components.js` as a
JavaScript module resource to use this dashboard card:

```yaml
type: custom:voice-harness-audio-settings
```

默认线性增益：唤醒和追问 1.0，白天播报 1.0，夜间播报 0.72，处理中提示 0.58。
调节后自动保存，无需“应用”按钮；每一项支持在平板试听。普通音量修改不重启录音。

## 2026-09-13 target validation / 本轮实机验证

The deployed Fast/Mid model `minimaxai/minimax-m3` returned HTTP 410 because it
retired on September 9. A live provider catalog and short probes confirmed the
already configured Deep model `nvidia/nemotron-3-super-120b-a12b` was available.
Fast/Mid were migrated to that model on the same provider, retaining their
token/time limits. HTTP 410 now permits an already configured fallback candidate;
request errors and exhausted quota remain terminal under their existing rules.

A controlled quiz used synthetic speech played into the kukui microphone.
The real wake detector, Doubao ASR, Gateway, Edge TTS, satellite player and
follow-up capture completed two turns with the same conversation ID. Gateway
latencies were 1,219 and 1,375 ms, with zero recorded errors. This is a near-field
device test, not a human far-field or listening-quality result. Satellite timing,
gain measurements and remaining operator checks are owned by
`phosh-ha-status/docs/phase7-target-validation-2026-09-13.md`.

Validation: 385 Gateway Python tests, 28 Bun tests, 7 mastering tests, Ruff,
tsgo type checking and panel build passed. The actual Lit component was checked
in desktop/mobile Chinese and mobile English at 390 px, including saving,
preview and mute. That browser fixture mocked HA transport; physical playback
was measured separately on the target.

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
  --target-lufs -10.5 \
  --lufs-tolerance 2 \
  --max-peak-dbfs -0.99
uv run pytest tests/test_mastering.py -q
```

Expected result: every wav reports `OK`.

The tablet pack uses 120 Hz high-pass filtering, soft-knee compression and a
2 ms lookahead limiter, followed by 4× oversampled peak normalization to −1 dBFS.
Encoded WAVs have 6–9 dB crest factors. LUFS is measured, not used as a second
normalization target; the lint window above checks the rendered pack's roughly
−10.5 LUFS short-clip range. Other packs retain the original loudness mode and
CLI defaults. These waveform checks do not measure the tablet speaker or room.

平板提示音采用 120 Hz 高通、软拐点压缩与前瞻限幅，编码后峰均比为
6–9 dB，过采样峰值不超过 −1 dBFS。LUFS 仅记录实测值；扬声器失真、
房间听感与回声消除仍需实机测量。

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
