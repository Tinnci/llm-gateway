# Voice Harness architecture

Voice Harness is an admin diagnostic surface for the Home Assistant voice
runtime. It is not a second agent runtime.

The design uses selected ideas from DeepSeek Harness (DSH). It keeps the Home
Assistant deployment model and voice latency constraints.

## Runtime topology

```text
Home Assistant conversation request
    -> conversation kernel
        -> registered Turn Loop adapter
        -> append-only Turn events
        -> action and provider evidence
    -> bounded Trace Store
    -> Harness API projections
    -> Voice Harness panel
        -> registered top-level view
        -> registered diagnostic drawer tab
        -> Replay Inspector
```

The conversation kernel owns mutable Home Assistant state. A Turn Loop adapter
can propose a result, but it cannot commit dialogue frames or device actions
outside the kernel contract.

## Harness Loop lifecycle

The runtime loop is a bounded decision cycle, not a synonym for the diagnostic
page:

```text
route decision
    -> select one loop
    -> start step
    -> plan effects
    -> execute through an injected service
    -> observe bounded evidence
    -> evaluate answerability and target coverage
    -> continue or stop
    -> kernel commits events, dialogue state, and speech
```

A loop returns either `TurnLoopContinuation`, `TurnLoopResult`, or `None` when
it cannot own the turn. The driver records `harness_step_start` and
`harness_step_end`, carries continuation reasons, and enforces a two-step voice
budget. A terminal result includes `stop_reason`, `step_count`, and an
`outcome_verdict`. Continuations carry an immutable `TurnLoopState`; the driver
assigns the step number, records phase transitions and durations, and rejects a
continuation that changes the route decision selected at the safety boundary.

Device-state reads are the first fully migrated query loop. The capability
router resolves a target domain and hint, `GetLiveContext` receives that domain,
and the renderer must prove that the returned entity covers the requested
target before it may answer. A successful HTTP/tool call is therefore not
treated as a successful turn when, for example, a fan question returns only
temperature sensors.

The device-state recovery policy is deliberately bounded:

1. query the target domain;
2. retry the same read once after a structured transient tool error, or remove
   only the area filter once when the requested target is absent while keeping
   the capability domain fixed;
3. stop with an answer, an actionable clarification, or a failure verdict.

Every continuation remains a read and retains the original route and risk
decision.

Retries keep one `operation_id` and increment `iteration`, so the inspection
API presents them as attempts of one logical read. Mixed multi-intent turns
use an atomic capability preflight. Fully supported local children compose one
answer; other combinations request separate turns before action dispatch.

Weather and generic environmental summaries keep their established providers
and renderers. Migrating one route family at a time preserves their fallback
semantics.

## Path ownership roadmap

Paths migrate by capability family, not by utterance. The intended ownership
order is:

1. device state and its bounded read recovery;
2. weather provider → live-context fallback;
3. indoor environment metric coverage;
4. device actions plus post-action state verification;
5. multi-intent composition over child loop results;
6. model/tool iteration, without forcing durable deep tasks into the voice-step
   budget.

Inventory and stable local answers can use single-step adapters later. Deep
tasks remain a separate durable lifecycle because they outlive the voice turn.

## DSH patterns that fit this project

### Append facts, derive views

Turn events record ordered runtime facts. The panel derives timelines,
trajectories, and replay comparisons from those facts.

The provider receives a bounded history projection. The Home Assistant chat log
remains complete for its own retention policy.

### Register capabilities at a composition root

Turn Loop adapters use a backend registry. Top-level Harness views and
diagnostic drawer tabs use frontend registries.

Each registration has a stable key. Duplicate keys fail immediately. A
registration returns a disposer for tests and future lifecycle management.

The consumer reads a detached registry snapshot. It does not contain a switch
statement for each capability.

### Keep channels separate

Assistant text, tool calls, tool results, and diagnostic events keep distinct
schemas. Parser boundaries remove leaked inline tool syntax before downstream
speech processing.

### Replay without physical side effects

Replay and Fork use stored evidence and dry-run evaluation. They do not repeat a
Home Assistant device action.

### Evaluate outcomes, not only transport

Scenario evaluation can consume captured `route_decision`, `tool_args`, and
`outcome_verdict` evidence. This catches semantic failures where every service
returned successfully but the final answer did not cover the user's target.

## Patterns that do not fit

Voice Harness does not embed the Cordis runtime. It does not load arbitrary
third-party code in Home Assistant.

The panel does not use React, Tailwind, a terminal, or a code editor. Those
dependencies do not improve the current voice diagnostic tasks.

The voice path does not run a general event-sourcing database. Trace retention
is bounded. Full turns remain opt-in private diagnostic data.

## Frontend extension contract

The page information architecture, component policy, and open-source
comparison are defined in [Voice Harness frontend design](harness-frontend-design.md).

A top-level view registration contains:

- `id`
- `labelKey`
- `icon`
- `order`
- `render(panel, entries)`
- optional `visible(panel)`

A diagnostic drawer registration contains:

- `id`
- `labelKey`
- `order`
- `render(panel, record, context)`

Both registries reject malformed entries and duplicate IDs. Both return a
disposer.

The current composition root registers the built-in views. A later change can
move one view renderer into its own module without changing navigation code.

## Remaining boundaries

`voice-harness-panel.js` still owns too many render and interaction methods.
Move one complete view at a time into a module. Do not split helpers only to
reduce line count.

`views.py` still owns status projection, configuration actions, scenario
evaluation, and provider probes. Extract a domain controller only when one
complete route family can own its validation and response schema.

Keep these invariants:

- The Home Assistant config entry owns secrets.
- Harness APIs require an administrator.
- A panel action uses a typed server-side allowlist.
- Replay does not call physical Home Assistant services.
- A full turn does not enter Home Assistant Recorder.
- Registry dispatch does not add work to the normal voice path.

## Source reference

DeepSeek Harness uses a plugin composition model for runtime and client
capabilities. This project adopts the registration and projection patterns, not
the complete framework.

- [DeepSeek Harness repository](https://github.com/deepseek-ai/deepseek-harness)
- [DSH introduction](https://dsh.hicyou.com/en/docs/getting-started/introduction)
