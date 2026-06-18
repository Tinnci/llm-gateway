# LLM Gateway for Home Assistant

LLM Gateway is a voice-first Home Assistant conversation agent for
OpenAI-compatible chat endpoints. It is tuned for NVIDIA NIM by default, but the
integration works with any compatible gateway that exposes `/v1/models` and
`/v1/chat/completions`, including LiteLLM, vLLM, OpenRouter, Ollama's OpenAI
shim, and similar providers.

The current implementation is no longer a single-model chat proxy. It is a
routed assistant runtime with short spoken answers, Home Assistant tool policy,
search gating, short session memory, compressed diagnostic traces, a localized
Voice Harness panel, and a small earcon toolchain.

## Current capabilities

- **Live model discovery**: the config flow validates the API key against
  `/v1/models` and populates model pickers from the endpoint's actual model
  list.
- **Fast / Mid / Deep routing**: normal voice turns use Fast, search and device
  diagnostics use Mid, and long reasoning uses Deep as a Home Assistant
  background task.
- **Home Assistant tool control**: Assist LLM API tools can be enabled from the
  options flow. High-risk actions are blocked until the user explicitly confirms.
- **Search gating**: `search_web` is only exposed when search is enabled, a
  provider key exists, and the user request actually needs current external
  information. Provider priority is Tavily, Serper, Firecrawl, then Brave.
- **TTS-safe Markdown cleanup**: only the final spoken response is converted to
  voice-safe plain text with `mistune`; the model's richer Markdown remains in
  the conversation log.
- **Short session memory**: recent turns are stored with a short TTL using Home
  Assistant `Store` and injected only when a conversation id is present.
- **Diagnostic run traces**: when explicitly enabled, completed turns are stored
  as bounded Voice Harness records. Summary fields are readable in the panel;
  optional raw chat/tool payloads are redacted and stored as `json+zlib+base64`.
- **Voice Harness panel**: the integration auto-registers an admin-only sidebar
  panel named `Voice Harness`; no manual `panel_custom` YAML is required. Panel
  chrome, prompt policies, scenarios, and earcon descriptions render in English
  or Simplified Chinese based on the Home Assistant/browser locale.
- **Earcon pack support**: rendered WAV earcons are served through the panel's
  static path. The `tools/ha-earcon` uv project renders and lints deterministic
  prompt sounds.

## What is intentionally not done yet

- Full Assist pipeline event capture is not complete yet. LLM Gateway records
  the post-STT text/LLM/tool/final-speech turn, but not wake word timing, raw
  audio, VAD chunks, or OPUS clips from the satellite.
- Local OPUS spoken fallback clips for network/TTS/port failures are not wired
  into the satellite playback chain yet.
- Durable alias memory and vector RAG are intentionally not defaults. Chinese
  embedding quality still needs validation before this becomes a first-class
  route.
- Deep tasks do not directly control Home Assistant devices. They produce
  analysis and notifications; actions still go through Fast/Mid plus policy.

## Installation

### HACS custom repository

1. HACS -> menu -> Custom repositories.
2. Add `https://github.com/Tinnci/llm-gateway` with category `Integration`.
3. Install `LLM Gateway`, then restart Home Assistant.

### Manual install

Copy `custom_components/llm_gateway` into:

```text
<ha-config>/custom_components/llm_gateway
```

Then restart Home Assistant.

## Configuration

1. Go to Settings -> Devices & services -> Add integration -> LLM Gateway.
2. Enter the OpenAI-compatible base URL and API key.
3. Open Configure to set:
   - routing mode,
   - Fast / Mid / Deep model ids,
   - token budgets and request timeouts,
   - extra request JSON per tier,
   - Home Assistant control exposure,
   - optional search provider keys,
   - optional diagnostic trace recording for the Voice Harness panel.

Set LLM Gateway as the Conversation agent in the Assist pipeline that serves
your voice satellite.

## Recommended NVIDIA NIM defaults

The current default profile is:

- Fast: `nvidia/nemotron-3-nano-30b-a3b`
- Mid: `nvidia/nemotron-3-nano-30b-a3b`
- Deep: `nvidia/nemotron-3-super-120b-a12b`

The legacy `chat_model`, `max_tokens`, `chat_timeout`, and `extra_body` options
still work as Fast-route fallbacks so older entries continue to load.

## Voice Harness

The panel is registered during integration setup with:

- `hass.http.async_register_static_paths([StaticPathConfig(...)])`
- `frontend.async_register_built_in_panel(...)`

The sidebar URL is `voice-harness`, and the panel calls:

- `GET /api/llm_gateway/harness/status`
- `POST /api/llm_gateway/harness/evaluate`
- `/api/llm_gateway/static/...` for the panel module and earcon assets

Current panel views:

- `Runs / 运行记录`: config entries, model routes, provider state, recent
  diagnostic text traces, latency, tool event counts, and optional compressed
  raw payloads.
- `Prompt Policies / 提示策略`: spoken prompt policies and risk rules.
- `Scenarios / 场景测试`: ad hoc prompt policy evaluation.
- `Search Lab / 搜索实验室`: search gate visibility and scenario checks.
- `Memory Lab / 记忆实验室`: short memory snapshots.
- `Earcons / 提示音`: rendered earcon manifest and playback.
- `Regression / 回归测试`: bundled scenario samples.

Home Assistant translation files cover the config/options flow. The custom
panel has its own small frontend dictionary because HA custom panel modules do
not automatically receive integration translation strings.

## Diagnostic traces and chat history

Diagnostic traces are separate from short session memory:

- Memory is runtime context for the assistant. It keeps a small recent window
  for follow-up turns such as "make it dimmer".
- Traces are admin diagnostics for Voice Harness. They are disabled by default
  and are meant for reproducing routing, prompt, search, and Home Assistant tool
  behaviour after a bad run.

Options:

- `diagnostic_traces`: enables bounded per-turn records.
- `trace_include_raw_messages`: additionally stores redacted raw chat/tool
  payloads as `json+zlib+base64`.
- `trace_max_runs`: caps records per config entry.
- `trace_retention_hours`: drops older records.

Each trace summary includes timestamp, conversation id, user text, final spoken
assistant text, route tier/model, latency, status, tool event summary, and
compressed payload size. Raw payload capture is opt-in because it can contain
household state, entity names, prompts, and device context. Secret-looking keys
such as API keys, authorization headers, passwords, tokens, and secrets are
redacted before compression.

This follows the same operational pattern used by production LLM observability
systems such as LangSmith-style run traces and OpenTelemetry-style spans:
record small indexed summaries by default, keep raw payload capture explicit,
bound retention, redact secrets before storage, and make traces replayable
enough for diagnosis without turning them into permanent user transcripts.
LLM Gateway does not store raw microphone audio; OPUS/FLAC audio history should
be implemented in the satellite or ASR project with its own short retention and
local-only controls.

## Earcon workflow

Render the bundled pack:

```bash
cd tools/ha-earcon
uv run ha-earcon render packs/ha_voice_minimal_v0.yaml --out ../../custom_components/llm_gateway/frontend/earcons/ha_voice_minimal_v0
uv run ha-earcon lint ../../custom_components/llm_gateway/frontend/earcons/ha_voice_minimal_v0/*.wav
```

The pack currently uses WAV for deterministic short cues. OPUS fallback spoken
clips are a separate satellite-level task and are not part of this integration
yet.

The pack includes two latency-oriented cues:

- `processing_loop.wav`: a short loopable cue for slow LLM/search waits. The
  satellite should play it at reduced gain after a soft latency threshold and
  stop it before final TTS starts.
- `provider_fallback.wav`: a one-shot cue for future model-provider fallback
  when the primary provider is too slow or fails.

Provider fallback should be implemented as ordered failover with per-provider
health scoring, not as blind round-robin load balancing. Search provider
fallback already follows a priority list. Model provider fallback is a planned
next layer that needs provider profiles, soft timeouts, circuit breakers, and
diagnostic trace fields for provider and fallback reason.

## Development

Use `uv` for Python and `bun` for frontend syntax/build checks:

```bash
uv sync --dev
uv run pytest
bun build --target=browser custom_components/llm_gateway/frontend/voice-harness-panel.js --outfile=/tmp/voice-harness-panel.js
```

## Security notes

- API keys are configuration data and must not be logged.
- Search traces should record provider, query, latency, and result count, but
  never provider secrets.
- Diagnostic traces are off by default. Enable raw payload capture only while
  debugging, then disable it again.
- Home Assistant actions from search results must still pass the same tool
  policy as direct user requests.

## License

Source-available for non-commercial use under the PolyForm Noncommercial
License 1.0.0. See `LICENSE`.

Commercial use is not permitted without a separate license. This is not an OSI
open-source license because commercial use is restricted.

Third-party dependencies and services keep their own licenses and terms. See
`NOTICE.md`.
