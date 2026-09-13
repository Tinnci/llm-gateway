# Voice Harness inspection API

Voice Harness exposes admin-only Home Assistant REST endpoints and a WebSocket
subscription for quick triage and detailed investigation. They use Home
Assistant authentication.
It does not add an MCP server, CLI daemon, credential store, or network port.

Use the coarse run query to find a relevant turn. Then use its `run_id` for
detail, event, or comparison queries. Responses include `api_version: 1` so a
programmatic client can validate the projection that it consumes.

## Authentication

Send a Home Assistant long-lived access token in the standard header:

```http
Authorization: Bearer <home-assistant-token>
```

Every endpoint requires a Home Assistant administrator. When more than one LLM
Gateway config entry exists, pass `entry_id` to select one.

## Status and runtime state

```http
GET /api/llm_gateway/harness/status
GET /api/llm_gateway/harness/runtime?entry_id={entry_id}
```

Status contains stable configuration, provider availability, bundled assets,
and satellite summaries. It excludes per-turn traces and mutable runtime
collections. Runtime detail contains short memory, feedback events, active
voice runs, deep tasks, and aggregate trace-storage metadata for one entry.
Recent completed replies remain in the paginated run query below.

## Coarse query

```http
GET /api/llm_gateway/harness/runs
```

The response contains lightweight newest-first summaries instead of complete
trace records. Supported query parameters are:

- `limit`: page size from 1 to 200, default 30;
- `cursor`: the last `run_id` from the previous page;
- `since`: a timezone-aware ISO 8601 lower timestamp bound;
- `status`, `route`, `provider`, and `capability`: exact-match filters;
- `outcome`: `answered`, `not_answered`, or the stored run status for legacy
  and non-loop runs;
- `failure_stage`: exact terminal reason for a non-answerable loop, such as
  `requested_target_missing`, `ambiguous_target`, or `tool_error`;
- `contains`: case-insensitive search in user, assistant, and final speech;
- `has_error`: `true` or `false`;
- `entry_id`: optional config-entry selector.

The response returns `records`, `has_more`, and `next_cursor`. Each summary
contains identifiers, bounded reply text, route, latency, tools, error types,
and a compact Harness Loop outcome. It does not contain the event stream or a
decompressed raw payload.

Example:

```http
GET /api/llm_gateway/harness/runs?limit=20&since=2026-09-02T00:00:00%2B08:00&has_error=true
```

Semantic-failure example:

```http
GET /api/llm_gateway/harness/runs?capability=device_state_query&outcome=not_answered
```

## Detailed query

```http
GET /api/llm_gateway/harness/runs/{run_id}
```

The detail response includes the stored trace, timeline, route evidence,
diagnostics, and bounded tool metadata. Raw messages are omitted by default.
For migrated loops, `route.harness_loop` shows the selected loop, step count,
continuation reasons, stop reason, answerability, and target coverage. The event
stream exposes the complete ordered step chain. `final_phase` distinguishes a
targeted result from `retry_targeted`, `relax_area`, and invariant
failure outcomes; `total_duration_ms` measures the complete local loop.
Pass `include_raw=true` only during an active investigation and only when the
raw-message trace option was enabled at capture time:

```http
GET /api/llm_gateway/harness/runs/{run_id}?include_raw=true
```

Raw payloads can contain private household context. Keep them out of Home
Assistant Recorder, metric labels, tickets, and routine agent context.

### Event stream query

```http
GET /api/llm_gateway/harness/runs/{run_id}/events
```

Filter with `event_type`, `source`, or `status`. `event_type` accepts a
comma-separated list and suffix wildcards such as `gateway.tool.*`. This lets a
client inspect one stage without loading an entire trace.

### Comparison query

```http
GET /api/llm_gateway/harness/runs/compare?left_run_id={id}&right_run_id={id}
```

The bounded comparison reports changes in status, route, latency, reply, tool
names, error types, and event types. It does not return two full records.

## Health query

```http
GET /api/llm_gateway/harness/health
```

This returns aggregate entry, provider, trace-storage, and satellite diagnostic
counts. Use it for a cheap first check before querying runs. It excludes full
turns and raw diagnostic JSON.

## Error behavior

Invalid filters and cursors return HTTP 400 with code `invalid_query`. Missing
runs return HTTP 404 with code `run_not_found`. A missing config entry returns
HTTP 404 with code `entry_not_found`.

## Streaming model preview / 流式模型演练

Send this subscription through the authenticated Home Assistant WebSocket:

```json
{
  "id": 42,
  "type": "llm_gateway/harness/stream",
  "entry_id": "YOUR_ENTRY_ID",
  "user": "用一句话介绍语音助手。",
  "route": "fast",
  "expected": {}
}
```

`route` accepts `auto`, `fast`, `mid`, or `deep`. `user` must contain 1–12,000
characters. The server copies options when it accepts the subscription, then
requests the selected model from the configured primary provider. This preview
does not invoke provider fallback or the production device-action loop.

Events arrive in Home Assistant subscription envelopes:

| `type` | Fields and meaning |
| --- | --- |
| `route` | Selected `route` and `model`. |
| `token` | Provider `text` delta. |
| `tool` | Accumulated `index`, `name`, `arguments`, and `status: proposed`. |
| `usage` | Provider-reported `usage`; absent counts stay unknown. |
| `finish` | Provider completion `reason`. |
| `complete` | `response`, `passed`, `violations`, `finish_reason`, `tool_calls`, and `mode: model_preview`. |
| `error` | A failure `message`; this is not a successful completion. |

Assertions evaluate the generated answer. Length limits and provider content
filter termination fail the result. An empty answer without a tool proposal,
malformed frames, or a stream ending without completion evidence also fail.
Tool calls are displayed but never executed; no sensor state is invented for
the prompt. 文本演练不等于真实麦克风、扬声器或弱网测试。

Use HA `unsubscribe_events` with `subscription: 42` to cancel. Disconnecting
also cancels the provider task. The panel disables automatic resubscription so
reconnecting cannot silently launch a second generation.

## Wyoming transport probe / 链路连通性

```http
POST /api/llm_gateway/harness/probe-wyoming
Content-Type: application/json

{}
```

The server probes hosts and ports from existing HA Wyoming config entries.
It does not accept an arbitrary target. Each result contains `name` and
`connected`; a connection also includes `latency_ms` and
`evidence: tcp_connection`. An unsuccessful connection returns
`error: unreachable`. The timeout is five seconds per endpoint, with probes
running concurrently. An empty configuration returns an empty `results` list.

This measures transport reachability, not speech recognition or audio playback.
No capture or playback command is sent.

## Tuning files / 调音配置导入导出

The Settings panel reads JSON or YAML in the browser and previews changes
before applying them through the existing Gateway settings and satellite
configuration APIs. The `gateway` section supports routing, tier models,
token budgets, timeouts, generation parameters, and trace retention. The
`audio` section supports cue and TTS gains, `audio_muted`, and `night_mode`.
Credentials, provider profiles, and arbitrary request bodies are excluded.

The existing configuration revision protects concurrent Gateway edits. HA
errors preserve their `body.message` and `body.code`, including
`revision_conflict`, so the panel can explain a rejected edit. Satellite
application remains a separate result; importing both sections is not a
cross-system transaction.

## Failed response validation / 回答校验失败

If unsafe final speech cannot be repaired, the persisted run has
`status: error`, `route.terminal_outcome: failed`, and an outcome verdict with
`answerable: false`, `reason: output_contract_failed`. Final display feedback
is `failed`, and automatic continuation is disabled. Successful repair keeps
the original failure evidence but allows the turn to complete normally.
