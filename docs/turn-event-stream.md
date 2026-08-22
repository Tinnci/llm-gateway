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
session id and the closest compatible UTC interval. TTS and satellite playback
adapters should propagate `turn_id` when their integration boundary supports
it; until then, their bounded traces are correlated by entity/source identity
and UTC interval. A correlation is evidence, not proof of strict global event
ordering.

`DiagnosticSnapshot` continues to describe current composed-system health. The
turn event stream describes what happened during one interaction; neither is a
replacement for the other.
