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

The legacy `stage`, `t_ms`, `status`, and `attrs` fields remain available while
existing Voice Harness projections migrate to the envelope.

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
