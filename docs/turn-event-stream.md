# Voice turn event stream

LLM Gateway records each run as an append-only sequence of trace-safe events.
The stored timeline remains the source for Voice Harness spans; the event
envelope is not a second log.

Each event includes:

- `event_id`: globally unique event identity;
- `turn_id`: the Gateway run and cancellation identity;
- `event_type`: namespaced event name such as `gateway.route.selected`;
- `source` and `source_sequence`: producer identity and zero-based order;
- `occurred_at`: UTC wall-clock time for cross-process correlation;
- `monotonic_ms`: elapsed time from the local turn start for latency;
- `caused_by`: the preceding event id in the local causal chain;
- `privacy`: payload handling classification;
- `payload`: bounded trace-safe event data.

New events carry only the envelope fields above; consumers derive the former
`stage` / `t_ms` / `status` / `attrs` view through the `event_stage()` and
`event_payload()` projections in `voice_runs.py`, which also accept records
persisted before the migration.

Wall-clock timestamps from different devices are approximate and must not be
used to calculate latency. Monotonic values are precise only within their
source process and must not be compared across devices.

## Cross-component correlation

Gateway creates `turn_id` when Home Assistant delivers the final transcript.
Upstream ASR evidence that predates that boundary is correlated by its provider
request id and a bounded 30-second UTC interval. The satellite playback adapter
receives the Gateway `turn_id` as its `request_id`; the observed stop is only
joined to a request when that producer identity matches and its timestamp falls
inside the same interval. TTS adapters should propagate `turn_id` when their
integration seam supports it. A time-window correlation is evidence rather than
proof of strict global ordering; a producer request-id match is stronger but
still does not make clocks comparable for latency calculations.

`DiagnosticSnapshot` continues to describe current composed-system health. The
turn event stream describes what happened during one interaction; neither is a
replacement for the other.

Programmatic clients first select a run through the bounded
`GET /api/llm_gateway/harness/runs` projection. They can then query matching
events through `GET /api/llm_gateway/harness/runs/{run_id}/events` with
`event_type`, `source`, and `status` filters. See
[Voice Harness inspection API](voice-harness-api.md) for the full contract.

For Harness Loop turns, the causal sequence includes
`gateway.harness.step.start`, effect-specific tool events,
`gateway.outcome.evaluated`, and `gateway.harness.step.end`. The terminal event
does not infer correctness from transport status: its paired outcome verdict
records whether the requested target was actually covered.

## Diagnostic drawer rendering

The Voice Harness panel renders trace diagnostics through a validated static
definition (`voice-harness-diagnostic-tabs.js`). The composition root defines
each tab once with `{ id, labelKey, order, render }`; the drawer iterates the
ordered collection, renders sections whose body is non-empty, and remembers
the selected tab per record by tab id. Adding a diagnostic section requires one
tab definition plus its render function while the drawer remains unchanged.
Record fields no panel consumes fall through a generic raw-tab fallback, so a
new backend diagnostic field is visible without any frontend change. Records
persisted before `schema_version` existed are versioned as `0` on read and get
`turn_summary` and `search_path` backfilled from their legacy fields.

## Dry-run replay and fork

Voice Harness can fork a stored deterministic turn through
`POST /api/llm_gateway/harness/runs/{run_id}/replay`. Replay reconstructs the
input from the bounded stored record and runs the selected `TurnLoop` with a
dry-run capability adapter. The adapter parses a proposed action but has no
path that calls a live Home Assistant service.

The fork is stored as a normal trace with `lineage.replay_of`, its own
`lineage.fork_id`, bounded overrides, proposed actions, and replay lifecycle
events. A dry-run fork does not ingest current satellite evidence because that
evidence belongs to the live device timeline rather than the historical fork.
Recorded replay uses the source route decision exactly. `reclassify` evaluates
the stored input with the current router, while `local_action` is an explicit
dry-run action proposal. The deterministic replay contract accepts route and
loop choices; model-prompt comparison belongs to a model-backed replay path.
