# LLM Gateway for Home Assistant

Use OpenAI-compatible models as a routed Home Assistant conversation agent.

LLM Gateway provides model routing, Home Assistant tool policy, web search,
short memory, bounded traces, and an admin Voice Harness.

It works with services that provide `/v1/models` and
`/v1/chat/completions`. Examples include LiteLLM, vLLM, OpenRouter, and
Ollama's OpenAI-compatible endpoint.

> [!IMPORTANT]
> A model response does not bypass Home Assistant action policy. High-risk
> actions require explicit confirmation.

## Features

### Model routing

- Fast, Mid, and Deep model tiers
- Live model discovery from the configured endpoint
- Separate token budgets, timeouts, and request bodies for each tier
- Ordered provider fallback for retryable provider failures
- Provider attempt and fallback evidence in diagnostic traces

Fast handles normal voice turns. Mid handles search and device diagnostics.
Deep runs long analysis as a Home Assistant background task.

Deep tasks do not control devices. Device actions use Fast or Mid with the same
tool policy.

### Home Assistant control

- Optional Assist LLM API tools
- Confirmation for high-risk actions
- Deterministic low-risk batch control
- Hidden, disabled, unavailable, and diagnostic entity exclusion
- State-match evidence for supported deterministic actions
- Local weather entity routing before external search

Chinese batch terms such as `所有`, `全部`, `每个`, and `每一` can select an
`all` target scope for supported low-risk domains.

### Search and response handling

- Search tools only appear when the request needs current information.
- Search provider order is Tavily, Serper, Firecrawl, then Brave.
- The final spoken response uses TTS-safe plain text.
- The conversation log can keep the richer Markdown response.
- Short session memory is scoped by conversation ID and a short time limit.

### Voice Harness

The integration adds an admin-only **Voice Harness** panel. The panel does not
need a manual `panel_custom` configuration.

The panel provides:

- recent runs and route evidence,
- provider state and latency probes,
- safe routing and retention settings,
- prompt-policy evaluation,
- bundled scenarios,
- short-memory inspection,
- earcon assets,
- satellite diagnostic summaries.

English and Simplified Chinese labels follow the Home Assistant or browser
locale.

## Installation

### HACS

1. Open HACS.
2. Add `https://github.com/Tinnci/llm-gateway` as a custom integration repository.
3. Install **LLM Gateway**.
4. Restart Home Assistant.

### Manual installation

1. Copy `custom_components/llm_gateway` to `<ha-config>/custom_components/llm_gateway`.
2. Restart Home Assistant.

## Configuration

1. Open **Settings > Devices & services**.
2. Add **LLM Gateway**.
3. Enter the OpenAI-compatible base URL and API key.
4. Select the Fast, Mid, and Deep models.
5. Enable only the Home Assistant LLM APIs that the agent needs.
6. Set LLM Gateway as the conversation agent in an Assist pipeline.

The options flow also controls search, fallback providers, timeouts, token
budgets, and diagnostic trace retention.

The old `chat_model`, `max_tokens`, `chat_timeout`, and `extra_body`
options remain valid Fast-tier fallbacks.

### Fallback provider example

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

## Voice Harness interface

The panel route is `voice-harness`. It uses these integration endpoints:

- `GET /api/llm_gateway/harness/status`
- `POST /api/llm_gateway/harness/evaluate`
- `/api/llm_gateway/static/...`

The panel can edit a small typed option list. It cannot edit API keys, provider
secrets, the base URL, the system prompt, or exposed Home Assistant LLM APIs.
Use the Home Assistant options flow for those values.

## Diagnostics and telemetry

Home Assistant can download native config-entry diagnostics. The System Health
page also shows aggregate provider and trace state.

Native diagnostics include:

- integration and routing configuration,
- enabled feature flags,
- aggregate provider health,
- trace counts and retention settings,
- satellite diagnostic status counts.

Native diagnostics omit API keys, prompts, provider error text, complete turns,
raw tool payloads, and Voice Harness records.

### Voice Harness traces

Voice Harness traces are separate from Home Assistant Recorder and short
session memory. They are disabled by default.

Enable `diagnostic_traces` only when you need per-turn evidence. Use
`trace_max_runs` and `trace_retention_hours` to bound storage.

`trace_include_raw_messages` adds redacted and compressed chat or tool
payloads. This option can still capture private household context. Disable it
after the investigation.

Do not put complete turns or full diagnostic JSON in Home Assistant Recorder.
Use low-cardinality counters and latency metrics for long-term telemetry.

### Satellite diagnostics

Voice Harness can read `sensor.kukui_diagnostic_snapshot`. The entity contains
a compact Recorder-safe projection. The satellite keeps the full snapshot on
its localhost diagnostic endpoint.

The compact projection preserves status counts and the first failed
prerequisite. It marks itself incomplete when it omits healthy checks.

## Runtime boundary

LLM Gateway owns the conversation, route, tool, and final speech-text stages.
It does not own:

- raw microphone audio,
- wake-word timing,
- VAD audio chunks,
- PipeWire or acoustic echo cancellation,
- capture muting,
- satellite playback,
- local offline fallback clips.

The satellite and ASR layers must provide those signals. LLM Gateway can consume
their bounded telemetry.

## Earcons

The repository includes a deterministic earcon tool.

```bash
cd tools/ha-earcon
uv run ha-earcon render packs/ha_voice_minimal_v0.yaml \
  --out ../../custom_components/llm_gateway/frontend/earcons/ha_voice_minimal_v0
uv run ha-earcon lint \
  ../../custom_components/llm_gateway/frontend/earcons/ha_voice_minimal_v0/*.wav
```

`processing_loop.wav` marks a slow provider wait.
`provider_fallback.wav` marks a provider change.

The satellite decides when and how to play these sounds.

## Development

Use `uv` for Python and `bun` for the panel.

```bash
uv sync --dev
bun install
uv run pytest
bun run typecheck
bun run build:panel
bun test
uvx ruff check custom_components tests tools/ha-earcon/src tools/ha-earcon/tests scripts
uvx ruff format --check custom_components tests tools/ha-earcon/src tools/ha-earcon/tests scripts
git diff --check
```

TypeScript contract checks use `tsgo` through
`@typescript/native-preview`.

## Security

- Do not log API keys, authorization headers, passwords, or tokens.
- Treat prompts, entity names, and tool payloads as private data.
- Keep raw trace capture off during normal operation.
- Apply the same action policy to search-derived and direct user requests.
- Download native diagnostics before you report a defect.

## Documentation

- [Voice Harness architecture](docs/harness-architecture.md)
- [Pipeline architecture](docs/pipeline-architecture.md)
- [Turn event stream](docs/turn-event-stream.md)
- [Voice audio audit](docs/voice-audio-audit-postmarketos-ha-docker.md)
- [Runtime verification](docs/voice-feedback-runtime-verification.md)

## Documentation style

This README applies practical rules from ASD-STE100 Simplified Technical
English, Issue 9. It uses active voice, short sentences, and consistent terms.

This use is not an ASD-STE100 compliance certification. Project-specific terms
remain necessary.

Reference: ASD STEMG. [ASD-STE100 Simplified Technical English](https://www.asd-ste100.org/), Issue 9, 2025.

## License

This source is available for non-commercial use under the
[PolyForm Noncommercial License 1.0.0](LICENSE).

Commercial use requires a separate license. This license is not an OSI
open-source license. See [NOTICE.md](NOTICE.md) for third-party terms.
