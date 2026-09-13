# Voice Harness frontend design

Voice Harness is a Home Assistant diagnostic tool. It is not a general LLM
observability platform.

The four views use Lit and TypeScript. This document records their ownership,
visual rules, and evidence boundary. 四个面板共享设计系统，同时保留观测与执行的边界。

## Open-source comparison

| Project | Useful pattern | Pattern to avoid here |
| --- | --- | --- |
| [Langfuse](https://github.com/langfuse/langfuse) | A trace list opens a focused detail surface without losing list context. Filters and columns belong to the list, not each trace card. | Its configurable enterprise table, batch actions, scores, cost columns, and saved views exceed the bounded HA use case. |
| [Arize Phoenix](https://github.com/Arize-ai/phoenix) | Trace details use a master-detail layout: an execution tree selects one span and a separate panel renders that span. | Relay, GraphQL, React, resizable panels, and metrics dashboards would add a second application framework to HA. |
| [Home Assistant frontend](https://github.com/home-assistant/frontend) | Lit and TypeScript are native choices. A trace picker selects one run; timeline, detail, logbook, and configuration are subordinate views of that run. | Private HA components are not treated as a stable external design system API. Use simple `ha-*` elements only when HA already provides them at runtime. |
| [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) | Typed registration points separate shell, navigation, content, and detail capabilities. Components receive narrow data and callbacks. | Voice Harness does not need Cordis, arbitrary plugins, React, or a general session runtime. |

## Page model

The first navigation level follows administrator tasks:

1. **Overview** answers what is unhealthy and where investigation starts.
2. **Runs** lists recent turns and opens evidence for one turn.
3. **Test** evaluates scenarios and keeps prompt policy as reference material.
4. **Settings** owns provider, trace, satellite, and earcon configuration.

Satellite, Prompt Policies, and Memory are no longer peer applications.
Satellite health and memory are supporting evidence. Satellite controls and
earcons are settings. Prompt policies support scenario evaluation.

## Component boundary

Create a custom element when a unit owns at least one of these concerns:

- interaction or keyboard behavior,
- accessibility semantics,
- reactive state,
- an independently testable rendering contract,
- a stable extension or replacement point.

Use a function for a pure data projection. Use shared CSS for visual rules
without behavior. Do not create a component only to replace one `div`.

Current ownership:

| Module | Responsibility / 职责 |
| --- | --- |
| `voice-harness-shell.ts` | Four mounted views; switching keeps forms, selection, and stream state. |
| `voice-harness-navigation.ts` | Tabs, arrow keys, Home/End, and 1–4 shortcuts outside editable fields. |
| `voice-harness-overview.ts`, `voice-harness-stat.ts` | Bento composition, observed metrics, sparklines, and supporting diagnostics. |
| `voice-harness-runs.ts` | Filters, modal trace drawer, stage disclosure, dialogue, local audio, and comparison. |
| `voice-harness-playground.ts` | Scenario assertions and cancellable provider streaming. |
| `voice-harness-settings.ts`, `voice-harness-audio-settings.ts` | Four settings groups, probes, 400 ms audio saving, scene presets, and preview. |
| `voice-harness-portability.ts` | Allowlisted JSON/YAML tuning files; credentials remain excluded. |
| `voice-harness-model.ts`, `voice-harness-live-model.ts` | Pure evidence projections, fresh activity, and PCM conversion. |
| `voice-harness-styles.ts` | Shared surfaces, typography, spacing, colors, motion, controls, and focus. |
| `voice-harness-api.ts` | HA transport, response validation, and useful HA error messages. |
| `voice-harness-panel.js` | HA adapter and existing configuration editors; supplies snapshots and callbacks. |

The adapter polls visible runtime data every five seconds. It assigns new
entry snapshots and preserves configuration input nodes while polling. Saved
configuration and unsaved form values have separate lifetimes. Closing a trace
clears the selection and restores focus to its opener.

## Visual and interaction rules / 视觉与交互

Shared CSS tokens derive from Home Assistant theme colors. Warm and cool
gradients stay behind readable content. Bento grids reflow without a second
mobile interface; controls have a minimum 44 px touch target. Dialogs become
full-width inspection surfaces on narrow screens.

View Transitions enhance navigation when supported. Reduced-motion settings
disable nonessential animation. Fresh display events may animate activity;
expired events cannot imply a live microphone. Keyboard focus remains visible,
and native modal dialogs provide Escape handling and focus containment.

## Evidence and test boundaries / 证据边界

- Metrics use retained, settled live turns. Dry-run forks cannot improve live
  success rates. Empty samples and missing token counts render as unknown.
- The six-stage waterfall uses recorded offsets and durations. Independent
  producer clocks are never subtracted to invent a common timing axis.
- Failed speech validation remains a failed outcome if its bounded repair
  fails. A repaired answer may complete and request a follow-up normally.
- Model previews stream the configured primary provider. Tool calls remain
  proposals. Text scenarios do not measure acoustic or network reliability.
- Action replay only supports recorded deterministic local actions. General
  model replies can be compared; new model generation belongs in Test.
- The trace store has no microphone recordings. WAV/PCM audition uses a file
  selected by the administrator and keeps it inside the browser.
- Wyoming probes measure TCP connection latency. TTS probes measure synthesis,
  and audio preview reports the satellite's result; none proves human audibility.

## TypeScript and library policy

Use Lit for Web Components because Home Assistant uses the same model. New
TypeScript modules compile under strict mode. Existing JavaScript remains under
`checkJs` until a complete feature boundary moves to TypeScript.

Use Valibot only at untrusted runtime boundaries. A TypeScript interface alone
does not validate an HA API response.

Add a library only when it removes a complete responsibility:

- consider `@lit/task` when the panel load state moves into a Lit container;
- consider `@lit/context` when three or more nested view components need the
  same narrow service;
- consider `@lit-labs/virtualizer` only after measurement shows that retained
  trace rows cause a rendering problem;
- keep native `Intl` for dates and numbers;
- do not add React, TanStack Table, Relay, or a generic state store.

## Build and tests

TypeScript is the source of truth for migrated modules. The build script writes
bundles to a temporary directory and then synchronizes the browser `.js`
artifacts. This prevents stale generated JavaScript from surviving beside a
changed TypeScript source file.

Pure projections use Bun tests. Lit components use a DOM implementation and
assert rendered semantics and user events. A component test does not inspect
private CSS class names.

The Phase 9 migration removes the obsolete Overview, Runs, Test, and Settings
render paths from the adapter. Existing configuration editors remain slotted
into the Lit settings view. See [target-device verification](voice-harness-phase9-2026-09-13.md)
for measured layouts and runtime checks.
