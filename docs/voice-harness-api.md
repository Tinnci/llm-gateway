# Voice Harness inspection API

Voice Harness exposes one admin-only Home Assistant REST API for quick triage
and detailed investigation. It uses Home Assistant bearer-token authentication.
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
