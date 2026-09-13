# Phase 10: room intent and calm feedback / 空间意图与平静反馈

Gateway **0.3.56** was deployed and verified on `192.168.3.120` on
2026-09-14 (Asia/Shanghai). Room temperature queries now use the room's
observation source through the actual Assist pipeline. Comfort targets, device
setpoints, dispatch and device reports retain their separate meanings.

本轮完成 Phase 10 的语音与空间联动：听懂房间意图、减少重复澄清，并让界面诚实说明
请求保存到了哪里、设备回报了什么。长期行为说明见
[Voice and room intent / 语音与空间意图](voice-room-intent.md)。

## Delivered behavior / 交付行为

- Room queries use HA's designated area sensor, preserve numbered rooms and
  follow-up context, and respect sensor freshness and Assist exposure. The M1
  room temperature cannot be replaced by an AC's internal temperature.
- Room temperature requests write the existing RoomMind comfort entity. A
  matching active policy readback supports “舒适目标已保存”; it does not confirm
  a physical AC operation. Missing rooms ask only for the room and retain the
  requested temperature.
- Unavailable comfort control ends with an unavailable answer. Repeating the
  room name cannot restore a missing control, so this case no longer asks for
  clarification or leaves the microphone waiting for a reply.
- Explicit AC requests remove the spoken setpoint from device-name matching.
  Genuine device clarification preserves the setpoint and applies confirmation
  only to the selected name. Similar comfort/override entities do not cause a
  second confirmation of an already explicit AC request.
- Recorded events copy bounded attributes at capture time. Booleans, numbers
  and nulls retain their types at the depth limit and through trace storage.
  A completed local action counts as an answered turn; physical confirmation
  still requires its separate correlated evidence.
- Overview leads with the understood request, response and actual result.
  Runs opens on the conversation. Metrics, timing and individual audio gains
  expand when needed. The four-panel Lit UI retains streaming, cancellation,
  replay, diff, PCM preview, connection probes and JSON/YAML portability.

RoomMind's Control Cycle and immutable observation snapshots remain the owner
of climate planning and learning. Gateway uses HA entities and the companion
driver's existing context-correlated events. No parallel sensor, calibration
constant, polling loop, hash or release gate was added.

## Household evidence / 家庭数据

The local RoomMind CSV analysis covered **53,828 rows**:

| Dataset | Rows | Valid room-temperature values checked |
| --- | ---: | ---: |
| `wo_shi_history.csv` | 25,360 | 25,306 |
| `ke_ting_history.csv` | 25,336 | 23,100 |
| `wo_shi_2_history.csv` | 3,132 | — |

The bedroom device setpoint differed from its comfort target by
**−4.5 to +2.5°C**. These are different control quantities, not a sensor
calibration offset. Neither this difference nor a reported cooling mode proves
compressor activity.

The deployed zM1 entry retains temperature, humidity, PM2.5 and formaldehyde,
plus its existing diagnostic/light entities. Its entity registry contains no
CO₂, eCO₂ or TVOC entities. The bedroom temperature reported MQTT provenance,
a per-field observation time and a 300-second maximum age. This iteration
reuses the existing sensor/driver work; it does not claim a new firmware build
or a measurement of firmware scheduling and sleep behavior.

## Assist entry point / 实际语音入口

Before the pipeline correction, Norta had `prefer_local_intents: true`.
An actual temperature pipeline run bypassed Gateway and answered
“现在温度是None度”. A direct successful `conversation.process` call had not
exercised that path.

Norta now has **`prefer_local_intents: false`**, with its other pipeline fields
preserved. This setting survived the deployment restart. Gateway's room reads
still run locally without a model request. Every accepted verification turn
reported `processed_locally: false` at the HA pipeline boundary, meaning the
pipeline handed conversation ownership to Gateway.

## Deployed conversation checks / 实机对话

The first two turns injected 16 kHz mono signed 16-bit PCM into the deployed
Assist STT stage, then exercised Doubao ASR, Gateway and Edge TTS. Subsequent
text turns entered the same Assist pipeline at its intent stage.

| Request | Observed result | Pipeline wall time |
| --- | --- | ---: |
| 卧室现在多少度？ | 卧室现在 25.4 度。 | 4,579 ms |
| 那客厅呢？ | 客厅现在 29.06 度。 | 4,530 ms |
| 那卧室2呢？ | 卧室 2现在 28.74 度。 | 153 ms |
| 把客厅温度调到25度 | 舒适温度控制当前不可用；不继续收音。 | 120 ms |
| 把温度调到25度 | 只询问房间。 | 197 ms |
| 卧室 | 舒适目标已保存为25度；结束澄清。 | 233 ms |
| 把卧室空调设为25度 | 卧室空调已回报设定 25 度。 | 844 ms |

The audio timing includes injection, pipeline execution, reply download and
PCM decoding; it is not a microphone-to-audible-speech measurement. The first
two responses contained 16,128 and 17,280 encoded audio bytes. Their recognized
texts matched the injected questions.

The three room queries share conversation ID
`01M2E9G3VF9GR6JFNB0DBXJBA9`. Their retained observations match, respectively,
`sensor.wo_shi_zm1_ad46_temperature`, `sensor.wo_shi_atc_6e73_temperature` and
`sensor.bth_d533_temperature`. Each spoken number matches its recorded sensor
value, and none of these reads dispatched a climate action.

The room clarification and saved target share conversation ID
`01M2E9GEA5YN4FJEEHXPSK5J2X`. Run `01M2E9GEGR55465QC5PC09PH3G`
retains `matches_request: true`, `override_active: true`,
`override_suppressed: false` and numeric `override_temperature: 25.0`.
Its device confirmation remains `unknown`. The check reused the existing
indefinite 25°C hold, so the household policy did not need restoration.

The explicit device turn is run `01M2E9GERZKT0YGG2MGB9GW2RP`.
The dispatch and independently captured `tcl_udp_ac_command_result` event
share context ID `01M2E9GESFJRR1TWQYB3Z78F76` and entity
`climate.tcl_air_conditioner_2`. The driver reported `accepted_by_cloud` and
`applied`, with target temperature 25°C matching the request. UDP was skipped
for this operation. The reported `beep` and `display` remained false.

This verifies a device-reported setpoint, not compressor operation or a room
that has reached its comfort target. The setpoint check reused the device's
existing setting rather than changing the family's target for the test.

## Playback and panel checks / 播放与面板

The second generated response was sent through the installed satellite
`snd-command-wrapper.sh` under the `user` PipeWire session. Playback ID
**`666938182157076`** has paired `playback_started` and `playback_finished`
events, terminal status `ok`, and a 3,258 ms interval. The wrapper exited zero.
The 127,008-byte PCM contains 2.88 seconds at 22,050 Hz, mono s16le. The browser
trace preview reported exactly 2.88 seconds with the same sample rate.
The live audio card showed the automatic night level of 72%.

The layout check covered all four panels at 390, 820 and 1440 pixels in light
and dark themes: **24 states**, no document overflow, and inspected visible
buttons, summaries, selects and text inputs at least 44 pixels high. Real HA
browser checks also covered the conversation drawer, expandable six-stage
timing, missing measurements, reply diff, Escape dismissal and PCM preview.

Two real Fast-model previews using `nvidia/nemotron-3-super-120b-a12b`
completed, including one-click replay. Both showed 489 input and 97 output
tokens and passing response assertions. The preview did not replace the
latest real conversation on Overview. The device result displayed
“设备已回报请求的状态”; saved comfort and unavailable runs retained their distinct
answered/error classifications in Runs.

| Settings probe | Observed result |
| --- | --- |
| Model provider | Settings connection test reported connected |
| Wyoming ASR | TCP reachable, 6 ms |
| Wyoming satellite | TCP reachable, 3 ms |
| Edge TTS | 14 KB synthesized, 1,511 ms round trip; no playback in this probe |
| Kukui settings agent | Responded, 31 ms round trip |

JSON and YAML exports contained identical gateway/audio tuning and no
credential fields. The exported YAML was imported through Settings; the UI
reported that tuning was saved and the satellite acknowledged application.
A second export matched every original value. 配置回导没有改变家庭现有调音参数。

## Local verification / 本地验证

| Component | Result |
| --- | --- |
| Gateway Python | 461 passed |
| Gateway Bun | 59 passed |
| Earcon tool | 7 passed |
| RoomMind Python | 2,316 passed |
| RoomMind Bun | 75 passed |
| TCL driver, user-specified `uv run --with … unittest` command | 283 passed |
| zM1 Python | 60 passed, 7 subtests passed |

Ruff check/format, Gateway version synchronization and `uv lock --check`
passed. RoomMind mypy checked 66 source files. Both frontends passed tsgo
typechecking and Bun builds. The zM1 warning came from the test that verifies
external sockets remain blocked. Regressions exercise unavailable controls,
same-room entity ambiguity, temperature retention after clarification,
immutable event capture, persisted scalar types, and dispatch-versus-confirmed
UI semantics.

## Deployment and limits / 部署与边界

Before the final copy, all four components were backed up outside the config
tree at `/home/user/homeassistant/backups/codex/`, using suffix
`20260913T205723Z`; the Assist pipeline storage was backed up there too.
Gateway was compiled on the host and inside the container. RoomMind's
`SSH_AUTH_SOCK= ./deploy.sh 192.168.3.120` rebuilt and synchronized RoomMind,
TCL and zM1, then restarted Home Assistant at
**2026-09-13T21:02:50Z** (05:02:50 on September 14 in Shanghai).

The versioned `/llm_gateway/assets/0.3.56/voice-harness-panel.js` returned
HTTP 200. RoomMind 1.8.0, TCL 0.11.0, zM1 0.3.0, Gateway 0.3.56, Edge TTS and
both Wyoming entries were loaded. No component setup error appeared in the
checked restart window. This deployment does not create a HACS release or tag.

- Injected PCM and a successful player process do not measure wake-word
  recognition, far-field pickup, speaker audibility, clipping, barge-in or echo
  suppression. The existing missing-acoustic-measurement warning remains
  visible; these properties are not marked verified.
- The pre-existing TCL cloud token-refresh `InternalError` warning remains.
  The tested command was accepted through cloud and received a matching device
  report; the warning itself is not claimed fixed.
- Old traces retain their original evidence. No historical confirmation was
  synthesized from newly fixed types or a newer reply classification.

Local evidence is retained under `/tmp/roommind-phase10-delivery/` and
`output/playwright/phase10-*`. Raw household traces, audio and tuning exports
are not included in this public verification document.
