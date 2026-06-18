# LLM Gateway for Home Assistant

A Home Assistant conversation agent for any **OpenAI-compatible** chat endpoint, with
**automatic model discovery**. Ships configured for [NVIDIA NIM](https://build.nvidia.com)
(a free-tier, OpenAI-compatible API) out of the box, but works with any compatible
gateway (vLLM, LiteLLM, Ollama's OpenAI shim, OpenRouter, Azure OpenAI-compatible, …).

## Features

- **Auto model list** — the model dropdown is populated live from the endpoint's
  `/v1/models`, so you always pick from what the gateway actually serves (custom ids
  are still allowed).
- **Home Assistant control** — opt in to the Assist LLM API and the model can call
  tools to control your devices (function calling).
- **Voice-first routing** — configure Fast, Mid and Deep models. Fast handles normal
  voice turns, Mid handles search/diagnostics, and Deep runs as a background task.
- **TTS-safe Markdown** — Markdown formatting is stripped from spoken responses so TTS
  does not read literal `**` or code fences.
- **Policy and search gates** — high-risk Home Assistant actions require explicit
  confirmation, and `search_web` is only exposed for search-appropriate requests.
- **Tunable** — model tiers, prompt, max tokens, temperature, top-p, request timeouts
  and extra request JSON are exposed in the options flow.
- **Lightweight** — talks to the endpoint over `aiohttp`; no heavy SDK dependency.

## Installation

### HACS (custom repository)

1. HACS → ⋮ → *Custom repositories*.
2. Add `https://github.com/Tinnci/llm-gateway` with category **Integration**.
3. Install **LLM Gateway**, then restart Home Assistant.

### Manual

Copy `custom_components/llm_gateway` into your Home Assistant `config/custom_components`
directory and restart.

## Configuration

1. *Settings → Devices & Services → Add Integration → LLM Gateway*.
2. Enter the **Base URL** (default `https://integrate.api.nvidia.com/v1`) and your
   **API key**. The key is validated against `/v1/models` before the entry is created.
3. Open the integration's **Configure** dialog to choose **Fast**, **Mid** and **Deep**
   models from the live list, optionally enable **Control Home Assistant**, configure
   search keys, and tune the generation settings.

To use it as your voice/chat assistant, set it as the **Conversation agent** of an
Assist pipeline (*Settings → Voice assistants*).

## NVIDIA NIM

Create a free API key at <https://build.nvidia.com>. The default model is
`nvidia/nemotron-3-nano-30b-a3b` for Fast voice turns. The same model is also the
default Mid route with a larger token budget for diagnostics/search summaries. The
recommended Deep model is `nvidia/nemotron-3-super-120b-a12b`.

Deep turns are submitted as Home Assistant background tasks and surfaced through
persistent notifications. They do not directly control Home Assistant devices.

## License

MIT
