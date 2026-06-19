# Voice and LLM Gateway pipeline architecture

This document describes the current maintained design for the Home Assistant
voice stack around LLM Gateway. It separates the deployed runtime from
satellite/ASR/display boundaries so operational decisions stay clear.

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

The bundled editable model examples are:

- Fast: `nvidia/nemotron-3-nano-30b-a3b`
- Mid: `nvidia/nemotron-3-nano-30b-a3b`
- Deep: `nvidia/nemotron-3-super-120b-a12b`

These are examples, not a provider requirement. Legacy `chat_model`,
`max_tokens`, `chat_timeout`, and `extra_body` remain fallbacks for the Fast
route.

## First response controller

Voice turns run a local first-response controller before slow model, search, or
grounding work can dominate the critical path. The controller is intentionally
small and deterministic: it classifies the turn for immediate feedback and
selects a local cue policy, but it does not own complex reasoning.

Current local task classes:

- `home_control`: ordinary device control; avoid extra audio before completion.
- `home_state`: state questions; prefer HA context/tool answers over web search.
- `search_needed`: explicit or current-information search; start the processing
  cue quickly while search/model work runs.
- `stable_fact`: stable knowledge such as canonical quote origins; prefer local
  cache or fast model before web search.
- `planning`: long planning/automation requests; acknowledge quickly, then use
  the Deep background path.
- `high_risk`: lock/alarm/whole-home/high-power requests; confirmation policy
  takes priority over model confidence.

This is a race-to-first-safe policy, not a race-to-first-answer policy. Fast
local answers can be committed only when they are low risk and high confidence.
Strong models can still help with complex reasoning, but they should not block
ordinary spoken feedback.

The first-response controller also drives the local processing cue delay:
explicit search and planning requests can start the display-agent processing
loop quickly, while ordinary HA control remains quiet unless it actually takes
too long.

## Turn controller

LLM Gateway keeps a small runtime turn controller for conversation ownership.
Each new run receives a generation token. When a newer user turn starts, the
previous active turn is marked stale, `rest_command.kukui_voice_barge_in` is
requested when available, and late provider/tool results from the old turn are
discarded before they can execute more tools, update final display state, write
memory, or schedule more speech.

This is not a full audio VAD implementation. The satellite/display-agent layer
still owns real-time microphone and speaker control. The gateway controller is
the backend safety layer that prevents old asynchronous work from winning the
race after the user has moved on.

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

Model provider fallback is implemented as ordered failover. The primary
OpenAI-compatible `base_url/api_key` client remains the first candidate; optional
provider profiles add fallback candidates without overloading route selection:

```json
{
  "providers": [
    {
      "name": "fallback-cloud",
      "base_url": "https://example.invalid/v1",
      "api_key": "replace-me",
      "models": {
        "fast": "provider/fast-model",
        "mid": "provider/mid-model",
        "deep": "provider/deep-model"
      },
      "soft_timeout_s": {
        "fast": 3,
        "mid": 8,
        "deep": 30
      }
    }
  ]
}
```

Selection is ordered failover, not round-robin load balancing:

- prefer the primary provider and then configured fallbacks for each route kind,
- use configured request timeouts per provider and route kind,
- fail over on network errors, authentication errors, 429, and 5xx responses,
- do not fail over on prompt/schema/tool-policy errors,
- record selected provider, fallback reason, elapsed time, attempts, and final
  status in diagnostic traces,
- apply a short in-memory cooldown after repeated provider failures for the same
  route kind,
- start the local `processing_loop.wav` cue if a voice-visible provider request
  crosses the soft latency threshold.

Fast route fallback must be conservative: if a simple HA control request cannot
complete quickly, prefer deterministic HA intent/tool repair over asking a
remote deep model. Deep route fallback can be slower because it is already a
background task.

The provider cooldown is intentionally small and in-memory. It avoids repeated
slow attempts during a live incident without turning provider selection into
cost-based load balancing.

## Voice run timeline

Each LLM Gateway turn records a recent in-memory `voice_run` timeline and, when
diagnostic traces are enabled, stores the same timeline in the compressed trace
summary. Current Gateway-owned stages include request receipt, HA LLM data
preparation, route selection, provider attempts, tool calls/results, search
results, TTS Markdown cleanup, and completion.

Wake word, ASR, playback, and microphone-gate events still originate in the
satellite/display layer. They are surfaced through the lock-screen status and HA
entities, and can be correlated with Gateway timelines by timestamp.

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

## Source grounding

Source grounding does not use a Deep model synchronously in the voice critical
path. The previous design could add 10+ seconds of latency and allowed a
generative verifier to invent merged titles from polluted search candidates.

The current voice-path grounding is a cheap evidence Module:

- distinguish noisy `source_candidates` from `source_canonical_answers`,
- repair only when one canonical answer is directly supported by an evidence
  span,
- never construct a new title by combining unrelated candidates,
- preserve the original answer when evidence is missing or ambiguous,
- record candidates, canonical answers, repairs, confidence, and reason in
  Voice Harness traces.

The model verifier prompt remains available for future background audit work,
but its interface is now `accept/select/reject/abstain`. `select` must choose an
exact string from `allowed_answers`; unlisted answers are treated as verifier
errors and cannot replace spoken output.

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

- `运行记录`: loaded entries, route examples, model/search provider visibility,
  provider fallback attempts, latency, tools, and optional raw payload metadata.
- `配置`: safe editable options for routing, model ids, budgets, timeouts, and
  bounded trace retention.
- `提示策略`: spoken prompt policies and risk levels.
- `场景测试`: ad hoc scenario evaluation.
- `搜索实验室`: search gate evaluation.
- `记忆实验室`: active short-memory sessions.
- `提示音`: rendered earcon pack playback and metadata.
- `回归测试`: sample scenario runner.

Current APIs:

- `GET /api/llm_gateway/harness/status`
- `POST /api/llm_gateway/harness/evaluate`
- `POST /api/llm_gateway/harness/options`

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

The integration serves these WAV assets to the panel and Home Assistant
frontend. Local OPUS spoken fallback clips, such as "网络连接失败" or
"Home Assistant 暂时无响应", live at the satellite playback layer so they can
still play when HA, TTS, or the network path is unavailable.

`processing_loop.wav` is intentionally short. LLM Gateway starts the local
display-agent loop only after the provider request crosses the soft threshold,
and stops it when the request returns or fails. Do not ask the LLM to produce
this status cue.

## Satellite playback boundary

LLM Gateway should not manage hardware volume, microphone gain, or ALS policy.
Those belong to the satellite/display layer.

Satellite work owned outside this integration:

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

Owned by adjacent layers or live-test harnesses:

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
