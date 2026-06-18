# Voice and LLM Gateway pipeline architecture

This document describes the current maintained design for the Home Assistant
voice stack around LLM Gateway. It separates the deployed runtime from planned
next layers so operational decisions stay clear.

## Current deployed path

1. `wyoming-openwakeword` detects the wake word.
2. `wyoming-satellite` starts the Home Assistant Assist pipeline.
3. Doubao ASR returns transcript text.
4. Home Assistant local intents run first when possible.
5. `conversation.llm_gateway` handles open-ended, routed, or tool-assisted turns.
6. The final speech text is cleaned for TTS and played by the satellite while
   the tablet microphone is muted.

The satellite side is responsible for wake cue playback, microphone gating, and
local audio behavior. LLM Gateway is responsible for routing, prompt policy, HA
tool policy, search gating, short memory, and Voice Harness visibility.

## Model routing

LLM Gateway uses three route classes:

- `fast`: default voice path, ordinary HA control, short answers,
  clarifications, and tool repair.
- `mid`: search-backed answers, device manuals, error codes, firmware,
  diagnostics, weather, news, traffic, and other freshness-sensitive requests.
- `deep`: explicit deep analysis, architecture/planning/comparison, or long
  requests. Deep turns return a short spoken acknowledgement and run as a
  background task.

The current NVIDIA NIM-oriented defaults are:

- Fast: `nvidia/nemotron-3-nano-30b-a3b`
- Mid: `nvidia/nemotron-3-nano-30b-a3b`
- Deep: `nvidia/nemotron-3-super-120b-a12b`

Legacy `chat_model`, `max_tokens`, `chat_timeout`, and `extra_body` remain
fallbacks for the Fast route.

## Spoken output

The Gateway preserves the model's raw Markdown in the conversation log, then
rewrites only the final `IntentResponse` speech into voice-safe plain text.

Implemented cleanup:

- strips bold/italic markers,
- avoids reading links as URLs,
- drops code fence syntax,
- flattens lists, tables, and headings,
- limits spoken output to a short default of two sentences.

Long details should be surfaced through Home Assistant notifications, the Voice
Harness panel, or a later visual surface rather than spoken in one turn.

## Tool policy

Every model tool call is checked before execution.

Current policy:

- Search tools are marked external to HA and can never directly execute HA
  actions.
- `search_web` is exposed only when a provider key exists and the user request
  is search-appropriate.
- High-risk HA targets require explicit confirmation before service execution.
- Deep tasks do not directly control HA devices.

High-risk domains include locks, alarm control panels, covers, valves, sirens,
and switch-like devices whose names imply doors, alarms, ovens, heaters,
high-power equipment, or whole-home actions.

Search provider priority is:

1. Tavily
2. Serper
3. Firecrawl
4. Brave

Search logs may include provider, query, latency, and result count. They must
not include API keys.

## Memory

Implemented v1 memory is intentionally small:

- sessions are keyed by Home Assistant conversation id,
- recent turns are stored for a short TTL,
- a compact memory context is injected only when a conversation id is present,
- data is persisted with Home Assistant `Store`.

Durable room aliases, device aliases, long-term user preferences, and vector RAG
are next layers. They should be added only after the retrieval model and Chinese
quality are validated.

## Deep task handoff

Deep turns are queued by `DeepTaskManager`:

1. The voice response says a short acknowledgement.
2. A background task calls the Deep model outside the voice critical path.
3. The result is posted as a Home Assistant persistent notification.
4. The Voice Harness panel can show task snapshots.

This prevents long reasoning requests from blocking wake -> ASR -> intent -> TTS.

## Voice Harness panel

The integration auto-registers an admin-only sidebar panel named `语音测试台`.
It uses the modern static path API and does not require `panel_custom` YAML.

Current views:

- `运行记录`: loaded entries, route examples, search provider visibility.
- `提示策略`: spoken prompt policies and risk levels.
- `场景测试`: ad hoc scenario evaluation.
- `搜索实验室`: search gate evaluation.
- `记忆实验室`: active short-memory sessions.
- `提示音`: rendered earcon pack playback and metadata.
- `回归测试`: sample scenario runner.

Current APIs:

- `GET /api/llm_gateway/harness/status`
- `POST /api/llm_gateway/harness/evaluate`

The status API reads the earcon manifest through Home Assistant's executor to
avoid blocking the event loop.

## Earcons and local audio fallbacks

The repository includes `tools/ha-earcon`, a small uv-managed Typer CLI that
renders deterministic WAV earcons from YAML packs and lints loudness/peak levels.

Current deployed earcon pack:

- wake
- listening_start
- listening_end
- success
- failure
- clarification
- confirmation
- search
- deep_task

The current integration only serves these WAV assets to the panel and Home
Assistant frontend. Local OPUS spoken fallback clips, such as "网络连接失败" or
"Home Assistant 暂时无响应", should live at the satellite playback layer so they
can still play when HA, TTS, or the network path is unavailable.

## Satellite playback boundary

LLM Gateway should not manage hardware volume, microphone gain, or ALS policy.
Those belong to the satellite/display layer.

Recommended next satellite work:

- wrap `snd-command` with a playback script that records start/end/failure,
- set output volume based on day/night/user preference,
- play local OPUS fallback clips for network/TTS failures,
- keep microphone mute gates around wake cues and TTS playback,
- log enough audio-chain telemetry for Voice Harness or lock-screen display.

## Harness layers

Implemented:

- unit tests for routing, policy, search, TTS Markdown cleanup, memory, and
  panel registration,
- a pure Python scenario harness that checks search gating, spoken style,
  forbidden phrases, confirmation requirements, and unsafe service-call markers.

Planned:

- real Assist run trace capture,
- search evidence/citation auditing,
- satellite playback trace ingestion,
- remote no-audio conversation tests,
- acoustic end-to-end tests run only when the satellite is idle and the room is
  quiet.

Each remote/acoustic run should capture:

- timestamps,
- satellite journal,
- ASR transcript/request metadata,
- Gateway request metrics,
- tool names and success/error flags,
- entity state before/after,
- microphone mute state after completion,
- final spoken text.
