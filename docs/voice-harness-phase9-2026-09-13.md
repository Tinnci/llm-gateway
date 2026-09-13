# Phase 9: Voice Harness / 全面板改造与实机验证

The four-panel redesign is delivered in 0.3.52. 四个面板共享 Lit + TypeScript
组件、Home Assistant 主题变量和一致的触控、焦点与动效规则。

## Delivered behavior / 交付行为

| Surface | Behavior |
| --- | --- |
| Overview / 概览 | Bento system overview, observed reply metrics, sparklines and activity driven by fresh evidence. Missing measurements remain unknown. |
| Runs / 运行记录 | Outcome filters, search, six-stage waterfall, modal evidence drawer, conversation bubbles, token usage, expandable JSON and reply comparison. |
| Test / 测试 | Scenario cards, reference assertions, actual provider streaming, proposed tool calls, cancellation, connection-loss handling and replay. |
| Settings / 设置 | Audio, model routing, ASR/TTS and Wyoming, and storage groups; connection probes; reviewed JSON/YAML tuning import and export. |

Settings inputs survive polling and view changes. A stream cancelled before its
subscription acknowledgement is still unsubscribed when that acknowledgement
arrives. Connection loss does not silently start another provider request.

派发、接收与物理确认保持独立。模型演练中的工具调用只是提案；动作重放使用
已有的 dry-run 路径。参考回答断言不会声称完成了模型请求，切换场景会清除上一轮
Token 统计。未通过输出校验且修复失败的回答保留失败结果。

The trace store does not contain microphone recordings. Local WAV/PCM audition
keeps the chosen file in the browser. The sample-rate selector includes the
satellite's native 22050 Hz playback format as well as 16000 Hz capture.

## Local verification / 本地验证

| Check | Result |
| --- | --- |
| Gateway `uv run pytest -q` | 395 passed |
| Earcon tool `uv run pytest -q` | 7 passed |
| Gateway `bun test` | 53 passed |
| Gateway tsgo typecheck and Bun panel build | Passed |
| Gateway Ruff check and format check | Passed |
| Version synchronization and `uv lock --check` | Passed |
| RoomMind `uv run pytest -q` | 2,316 passed |
| RoomMind `bun test` | 75 passed |
| RoomMind Ruff, tsgo typecheck and build | Passed |
| TCL companion driver unittest suite | 283 passed |

Browser verification used Chromium through Playwright, launched with Bun.
The four views were inspected at 390, 820 and 1440 px widths in dark mode,
with light-mode desktop and phone checks. No panel had horizontal overflow.
Measured buttons, summaries and selects met the 44 px target; model pickers
were corrected from 38 to 48 px. Screenshots were captured after View
Transitions finished. The trace dialog has an accessible name and Escape
closes it while retaining the list context.

Local visual evidence is in `output/playwright/phase9-*.png`. Fixture images
exercise layout; target-device checks below use the deployed HA APIs.

## Household data / 家庭数据

Loaded 50,696 existing rows from `wo_shi_history.csv` and
`ke_ting_history.csv` in the RoomMind workspace, covering June 14 to
September 10, 2026. The bedroom has 25,306 valid temperature readings;
the living room has 23,100. Bedroom device setpoints differ from comfort
targets by −4.5 to +2.5 °C in these historical records. Living-room device
setpoints are absent, so that comparison remains unmeasured.

这些历史值用于核对观测、舒适目标与设备设定的边界，不作为界面中的实时状态，
也不用于推断压缩机活动、指令确认或实测节能率。

## Deployment / 部署

Target: `192.168.3.120`, Home Assistant container `homeassistant`.

- Before deployment, RoomMind, TCL, zM1 and Gateway were copied to
  `/home/user/homeassistant/backups/codex/<component>-20260913T170243`.
- Gateway was compiled on the target. RoomMind `./deploy.sh` built and copied
  RoomMind, `tcl_udp_ac` and `zm1`, then restarted Home Assistant.
- The final Gateway patch uses `/llm_gateway/assets/0.3.52/` so existing
  browser caches receive the new components. The versioned panel returned
  HTTP 200. The preceding Gateway copy was retained as
  `llm_gateway-20260913T175916` before the final restart.
- The deployed RoomMind, zM1, both TCL entries and Gateway were observed in
  the `loaded` state. Component setup errors were absent from the checked
  restart log window.

This deployment does not create a HACS release or a Git tag. 正式发布仍使用
[Release workflow](releasing.md)。

## Runtime checks / 实机链路

The deployed browser completed a real streaming preview using the configured
Fast model, `nvidia/nemotron-3-super-120b-a12b`. It rendered the response,
496 input tokens, 97 output tokens and passing assertions. Two retained runs
were selected for comparison; the diff drawer rendered and Escape closed it.
On the final deployment, replay completed another real generation with passing
assertions. The 1–4 navigation shortcuts worked outside the editor and did not
intercept numeric input while the text field was focused.

The Settings probes measured:

| Probe | Observed result |
| --- | --- |
| Wyoming ASR | TCP connection, 5 ms |
| Wyoming satellite | TCP connection, 4 ms |
| Edge TTS | About 14 KB synthesized, 1,588 ms browser round trip |
| Kukui settings agent | Response received, 102 ms browser round trip |

JSON and YAML exports contained identical gateway/audio tuning and no
credentials. The browser imported the exported YAML, saved the gateway values
and received the satellite's application acknowledgement for audio settings.
Transport connectivity, synthesis and playback remain separate
results; none of these probe timings establishes acoustic latency.

Two PCM samples were injected at the deployed Assist STT boundary. Doubao
recognized “卧室现在多少度？” and “那客厅呢？” exactly. Both turns completed
STT, intent and TTS in the same conversation. Measured end-to-end times were
5,942 ms and 16,616 ms, with 17,568 and 19,872 bytes of synthesized audio.
The second turn produced Gateway trace `01M2D17P2BAP5ZADFW3WCEFVXS`.

The second response was then played through the installed satellite wrapper
and PipeWire. Playback ID `627036754131238` has both `playback_started` and
`playback_finished` with status `ok`; the observed interval was 3,739 ms.
The same PCM file loaded in the deployed trace drawer at 22050 Hz with a
browser duration of 3.311973 s, matching its sample count. This confirms the
player path and correct preview rate, not human audibility.

## Evidence limits and follow-up / 边界与后续

- Injected PCM verifies deployed services and their handoff. It does not
  measure wake-word recognition, a person speaking at a distance, microphone
  sensitivity, audibility or echo suppression. The existing missing acoustic
  measurement remains visible as a diagnostic warning.
- Absent wake, ASR, synthesis or playback offsets remain unmeasured in the
  waterfall. Independent monotonic clocks are not placed on a fabricated
  common axis.
- The first temperature question used HA's local temperature intent. Its
  24.4 °C reply matched the AC's internal reading; subsequent inspection showed
  M1 and RoomMind comfort at 26.2 °C. This is not accepted as validation of a
  RoomMind comfort-temperature query. Phase 10 must resolve the preference
  between room observations and device-internal temperature in HA intents.
- The follow-up recovered from an unavailable `HassClimateGetTemperature`
  tool by querying live context. Its failed tool attempt remains visible in
  the trace; the completed answer does not erase that evidence.
