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
- **Tunable** — model, system prompt, max tokens, temperature and top-p are all
  exposed in the options flow.
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
3. Open the integration's **Configure** dialog to choose a **Model** from the live list,
   optionally enable **Control Home Assistant**, and tune the generation settings.

To use it as your voice/chat assistant, set it as the **Conversation agent** of an
Assist pipeline (*Settings → Voice assistants*).

## NVIDIA NIM

Create a free API key at <https://build.nvidia.com>. The default model is
`qwen/qwen3-next-80b-a3b-instruct` — a fast MoE model with strong multilingual
(incl. Chinese) and tool-calling behaviour, which suits voice assistants well.

## License

MIT
