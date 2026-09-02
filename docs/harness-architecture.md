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
