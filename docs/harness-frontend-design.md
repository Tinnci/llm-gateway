# Voice Harness frontend design

Voice Harness is a Home Assistant diagnostic tool. It is not a general LLM
observability platform.

This document compares relevant open-source interfaces and defines the
frontend boundary for this repository.

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

Current foundation:

- `voice-harness-navigation.ts` owns tab semantics and keyboard navigation;
- `voice-harness-run-list.ts` owns compact run selection and list keyboard behavior;
- `voice-harness-stat.ts` owns the shared status metric presentation;
- `voice-harness-styles.ts` owns component box, spacing, control, and focus rules;
- `voice-harness-api.ts` owns transport and runtime validation;
- `voice-harness-model.ts` owns pure display projections;
- `voice-harness-view-registry.js` owns top-level capability registration.

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

## Migration order

1. Keep the four-task shell and shared foundation stable.
2. Move Overview into a Lit view with narrow typed input.
3. Continue moving selected-run detail sections out of the panel after the
   run list and single-detail surface are stable.
4. Move Test and Settings one complete workflow at a time.
5. Convert the remaining panel container to Lit and replace manual full-root
   `innerHTML` rendering.

Do not split helpers only to lower line count. Each migration must remove an
owned behavior from `voice-harness-panel.js`.
