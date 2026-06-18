# LLM Gateway for Home Assistant

LLM Gateway is a voice-first Home Assistant conversation agent for
OpenAI-compatible chat endpoints. It is tuned for NVIDIA NIM by default, but the
integration works with any compatible gateway that exposes `/v1/models` and
`/v1/chat/completions`, including LiteLLM, vLLM, OpenRouter, Ollama's OpenAI
shim, and similar providers.

The current implementation is no longer a single-model chat proxy. It is a
routed assistant runtime with short spoken answers, Home Assistant tool policy,
search gating, short session memory, a Chinese Voice Harness panel, and a small
earcon toolchain.

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
- **Voice Harness panel**: the integration auto-registers an admin-only sidebar
  panel named `语音测试台`; no manual `panel_custom` YAML is required.
- **Earcon pack support**: rendered WAV earcons are served through the panel's
  static path. The `tools/ha-earcon` uv project renders and lints deterministic
  prompt sounds.

## What is intentionally not done yet

- Real run capture for every Assist pipeline event is not complete yet; the
  panel currently exposes configuration state, scenario evaluation, policies,
  memory snapshots, search provider visibility, and earcon playback.
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
   - optional search provider keys.

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

- `运行记录`: config entries, model routes, provider state.
- `提示策略`: spoken prompt policies and risk rules.
- `场景测试`: ad hoc prompt policy evaluation.
- `搜索实验室`: search gate visibility and scenario checks.
- `记忆实验室`: short memory snapshots.
- `提示音`: rendered earcon manifest and playback.
- `回归测试`: bundled scenario samples.

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
- Home Assistant actions from search results must still pass the same tool
  policy as direct user requests.

## License

MIT
