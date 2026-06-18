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

## Latency feedback

Voice latency should be handled as a user-interface state, not as extra model
output. The model should not invent "please wait" text after it has already
blocked too long; the satellite/display layer should play deterministic local
cues while the request is still in flight.

Recommended thresholds:

- `0-1.2s`: no extra cue; normal low-latency voice path.
- `1.2-2.5s`: show visual "processing" state on the lock screen or Voice
  Harness trace, but avoid extra audio.
- `2.5-5s`: play `processing_loop.wav` at a reduced gain every 1.2-1.8 seconds
  until final TTS starts.
- `5-8s`: play one local spoken clip such as "还在查询，请稍等。" or the
  localized equivalent. Do not repeat this phrase in a loop.
- `>8s`: either hand off to a background task or return a short repair prompt
  that names the failing stage.

Stop conditions:

- stop the loop before TTS starts,
- stop the loop when a provider fallback cue is played,
- stop the loop on pipeline cancellation,
- never play the loop while the microphone is unmuted for user speech.

This keeps long waits audible without turning the assistant into a repeating
chatty status announcer.

## Provider fallback

Search provider fallback is already implemented as a priority list:
Tavily -> Serper -> Firecrawl -> Brave. It fails over when a provider errors or
times out.

Model provider fallback is not implemented yet. The current Gateway has one
OpenAI-compatible `base_url/api_key` client and three model tiers. The next
provider layer should add provider profiles rather than overloading model route
selection:

```yaml
providers:
  - name: nvidia
    base_url: https://integrate.api.nvidia.com/v1
    api_key_ref: primary
    fast_model: nvidia/nemotron-3-nano-30b-a3b
    mid_model: nvidia/nemotron-3-nano-30b-a3b
    deep_model: nvidia/nemotron-3-super-120b-a12b
    soft_timeout_s:
      fast: 2.5
      mid: 6
      deep: 20
  - name: openrouter
    base_url: https://openrouter.ai/api/v1
    api_key_ref: openrouter
    fast_model: provider/model
    mid_model: provider/model
    deep_model: provider/model
```

Selection should be "ordered failover with health scoring", not round-robin load
balancing:

- prefer the first healthy provider for each route kind,
- use a soft timeout to cancel a slow primary and try the next provider,
- fail over on network errors, 429, and 5xx responses,
- do not fail over on prompt/schema/tool-policy errors,
- keep a short in-memory circuit breaker per provider and route kind,
- record selected provider, fallback reason, elapsed time, and final status in
  diagnostic traces,
- play `provider_fallback.wav` once when a voice-visible failover happens.

Fast route fallback must be conservative: if a simple HA control request cannot
complete quickly, prefer deterministic HA intent/tool repair over asking a
remote deep model. Deep route fallback can be slower because it is already a
background task.

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
- processing_loop
- success
- failure
- clarification
- confirmation
- search
- provider_fallback
- deep_task

The current integration only serves these WAV assets to the panel and Home
Assistant frontend. Local OPUS spoken fallback clips, such as "网络连接失败" or
"Home Assistant 暂时无响应", should live at the satellite playback layer so they
can still play when HA, TTS, or the network path is unavailable.

`processing_loop.wav` is intentionally short. It should be looped or scheduled
locally by the satellite at a reduced output gain, then stopped before final
TTS. Do not ask the LLM to produce this status cue.

## Satellite playback boundary

LLM Gateway should not manage hardware volume, microphone gain, or ALS policy.
Those belong to the satellite/display layer.

Recommended next satellite work:

- wrap `snd-command` with a playback script that records start/end/failure,
- set output volume based on day/night/user preference,
- play local OPUS fallback clips for network/TTS failures,
- play `processing_loop.wav` when a remote LLM/search request crosses the soft
  latency threshold,
- play `provider_fallback.wav` once when model provider fallback is triggered,
- keep microphone mute gates around wake cues and TTS playback,
- log enough audio-chain telemetry for Voice Harness or lock-screen display.

Audio processing that should stay local:

- wake word detection,
- VAD and echo/mic gating,
- capture gain and noise suppression,
- resampling to the ASR provider's expected format,
- local earcons and fallback OPUS clips,
- day/night output gain and limiter policy.

Audio/text processing that can be remote:

- ASR when the local model is not accurate enough,
- LLM reasoning and search summarization,
- TTS when network is healthy and the voice quality is preferred.

Audio/text processing that should have local fallback:

- ASR: fall back to a local or lower-quality recognizer for simple HA intents,
- TTS: fall back to local OPUS clips for fixed failure/status phrases,
- LLM: fall back to deterministic HA intents and short repair prompts before
  trying slower remote models for control requests.

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
