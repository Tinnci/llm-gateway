# Voice and LLM Gateway pipeline architecture

## Current fixed path

1. `wyoming-openwakeword` detects the wake word.
2. `wyoming-satellite` starts the Home Assistant Assist pipeline.
3. Doubao ASR returns transcript text.
4. Home Assistant local intents run first when possible.
5. `conversation.llm_gateway` handles open-ended or tool-assisted turns.
6. TTS plays the response while the tablet microphone is muted.

The satellite now responds to HA ping/pong, gates the wake cue, gates TTS playback,
and uses the built-in `alexa` wake word.

## Model routing

Use three execution classes instead of one model for every turn:

- `local_control`: HA local intents and deterministic services. Use for device control,
  timers, scenes, and room state. Target latency: under 2 seconds after ASR.
- `fast_model`: low-latency chat, clarification, tool repair, short summaries. Target
  latency: under 5 seconds. This should be the default voice model.
- `deep_model`: high-capability reasoning such as Nemotron Ultra with large
  `reasoning_budget`. This should be explicit or auto-escalated as an async task, not
  the default blocking voice response.

Routing policy:

- If the user asks for direct home control, try `local_control` before any LLM.
- If an action tool fails, force the model to call a tool again until an action succeeds
  or the bounded loop ends.
- If the user asks for analysis, planning, coding, comparison, or long reasoning, return
  a short acknowledgement through the fast path and submit a `deep_model` task.
- If the model output would exceed the voice latency budget, continue the task in the
  background and notify through HA notification, dashboard card, or a later spoken
  summary.

Implemented v1 routes:

- `fast`: default for normal voice turns and Home Assistant control repair.
- `mid`: selected for search, device manuals, error codes, firmware, diagnostics,
  weather, news, traffic, and other freshness-sensitive requests.
- `deep`: selected for explicit deep analysis, architecture/planning/comparison, or
  long requests. It returns a short spoken acknowledgement and runs a background
  non-tool model call; the result is posted as a Home Assistant persistent
  notification.

Legacy `chat_model`, `max_tokens`, `chat_timeout`, and `extra_body` still work as
fallbacks for the Fast route.

## Spoken output

The Gateway keeps the model's Markdown content in the chat log, then rewrites only the
final `IntentResponse` speech into voice-safe plain text. This prevents Edge TTS from
reading formatting such as `**bold**`, links, tables, and code fences literally while
preserving richer text for non-voice surfaces.

The spoken response is limited to the first two sentences by default. Long details
should be shown in Home Assistant notifications, traces, or a future Voice Harness
panel.

## Tool policy and search

Every model tool call is checked before execution:

1. Schema validation is handled by Home Assistant for HA tools.
2. Gateway policy blocks high-risk HA actions unless the user explicitly confirms.
3. Search tools are exposed only when web search is enabled, a provider key exists, and
   the user request is search-appropriate.
4. Tool results are appended back into the chat log for the next model turn.

High-risk targets include locks, alarms, covers, valves, and switch-like devices whose
name suggests doors, alarms, heaters, ovens, high-power loads, or whole-home actions.

Search provider priority is Tavily, Serper, Firecrawl, then Brave. Search logs include
provider, latency and result count, but never API keys.

## Context and memory

Keep context in explicit layers:

- `turn`: current transcript, device id, area, selected pipeline, exposed entities.
- `session`: recent N turns for the same satellite/conversation, with a TTL such as
  5-10 minutes since last interaction.
- `summary`: rolling compressed summary generated when the session exceeds a token or
  turn threshold.
- `long_memory`: durable facts and preferences, for example room aliases, device aliases,
  user preferences, recurring task state, and stable corrections.

Do not pass raw long history to every request. Build each request as:

1. System prompt and HA Assist API context.
2. Relevant long-memory snippets.
3. Current session summary.
4. Last few raw turns.
5. Current user turn.

Memory writes should be asynchronous. The voice path should not wait for memory
extraction unless the user explicitly says to remember something.

Implemented v1 memory stores recent conversation turns for 10 minutes using Home
Assistant `Store`. It injects a compact local-memory system message only when a
conversation id is present. Durable aliases and vector RAG are intentionally left as the
next layer, because the NVIDIA embedding options need per-language validation before
becoming defaults.

## Continuous conversation

Implement continuous conversation as a session lease:

- Start lease on wake detection.
- Keep lease alive while the user continues within a configured silence window.
- Reuse `conversation_id` during the lease.
- End lease after timeout, explicit stop, or long TTS completion with no follow-up.
- Summarize and persist the session at lease end.

Suggested first values:

- Follow-up window: 8 seconds after TTS played.
- Session TTL: 10 minutes.
- Raw window: last 6 turns.
- Summarize threshold: 3,000-5,000 tokens or 8 turns.

## Deep task handoff

Deep tasks need an explicit queue:

- Store task id, user request, current context pack, selected deep model, and status.
- Immediately respond with a short acknowledgement.
- Run the deep model outside the wake/ASR/TTS critical path.
- Save result and surface it through HA notification/dashboard, with optional spoken
  summary when the user next wakes the tablet.

This avoids blocking voice on a 16k-token reasoning request.

## Harness structure

The harness should have four layers:

- `unit`: payload construction, `extra_body` merging, tool-choice forcing, memory pack
  assembly, routing decisions.
- `component`: HA `conversation/process` with mocked NIM responses and fake tools.
- `remote integration`: real HA plus real NIM, no audio. Assert response, logs, tool
  result, and entity state.
- `acoustic e2e`: real wake word, mic, ASR, TTS, and entity state. Run only when the
  room is quiet and the satellite state is `listening`.

Each remote run should capture:

- wall-clock start and end timestamps,
- satellite journal,
- ASR request id/transcript length,
- Gateway request metrics,
- tool names and success/error flags,
- entity state before/after,
- microphone mute state after completion.

Avoid synthetic speaker injection while a user is actively testing; it contaminates ASR
and wake-word results.

Implemented v1 adds a pure Python scenario harness that evaluates search gating, spoken
style, forbidden phrases, confirmation requirements, and unsafe service-call markers
from YAML-like scenario dictionaries.
