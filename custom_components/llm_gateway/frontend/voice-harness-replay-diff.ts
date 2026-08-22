import { diffLines } from "diff";

export type ReplayDiffPart = {
  added?: boolean;
  removed?: boolean;
  value: string;
};

export type ReplayDiffSection = {
  id: "route" | "actions" | "speech" | "events";
  changed: boolean;
  parts: ReplayDiffPart[];
};

export type ReplayPair = {
  source: RecordValue;
  fork: RecordValue;
  sourceId: string;
  forkId: string;
};

export const TRACE_VIRTUALIZATION_THRESHOLD = Object.freeze({
  turns: 200,
  eventsPerTurn: 1000,
});

export function shouldVirtualizeTrace(
  turnCount: number,
  maxEventsPerTurn: number,
): boolean {
  return (
    turnCount >= TRACE_VIRTUALIZATION_THRESHOLD.turns ||
    maxEventsPerTurn >= TRACE_VIRTUALIZATION_THRESHOLD.eventsPerTurn
  );
}

type RecordValue = Record<string, unknown>;

function object(value: unknown): RecordValue {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as RecordValue)
    : {};
}

function runId(record: RecordValue): string {
  return String(record.run_id || record.id || "");
}

export function resolveReplayPair(
  records: RecordValue[],
  selected?: { sourceId?: string; forkId?: string } | null,
): ReplayPair | null {
  const forks = records.filter((record) => object(record.lineage).mode === "dry_run");
  const fork = selected?.forkId
    ? forks.find((record) => runId(record) === selected.forkId)
    : forks[0];
  if (!fork) return null;
  const lineage = object(fork.lineage);
  const sourceId = String(selected?.sourceId || lineage.replay_of || "");
  const source = records.find((record) => runId(record) === sourceId);
  if (!source) return null;
  return { source, fork, sourceId, forkId: runId(fork) };
}

function stable(value: unknown): string {
  if (Array.isArray(value)) {
    return `[\n${value.map((item) => `  ${stable(item)}`).join(",\n")}\n]`;
  }
  if (value && typeof value === "object") {
    const record = value as RecordValue;
    return `{\n${Object.keys(record)
      .sort()
      .map((key) => `  ${JSON.stringify(key)}: ${stable(record[key])}`)
      .join(",\n")}\n}`;
  }
  return JSON.stringify(value ?? null);
}

function timeline(record: RecordValue): unknown[] {
  const spans = record.timeline_spans;
  const events = Array.isArray(spans) && spans.length ? spans : record.timeline;
  return Array.isArray(events)
    ? events.map((item) => {
        const event = object(item);
        return {
          stage: event.stage,
          status: event.status,
          start_ms: event.start_ms ?? event.t_ms,
          duration_ms: event.duration_ms ?? 0,
        };
      })
    : [];
}

function actions(record: RecordValue): unknown[] {
  if (Array.isArray(record.proposed_actions)) return record.proposed_actions;
  const raw = object(record.raw_payload);
  return Array.isArray(raw.proposed_actions) ? raw.proposed_actions : [];
}

function speech(record: RecordValue): string {
  const speechValue = object(record.speech);
  return String(
    speechValue.final || record.final_speech_text || record.assistant_text || "",
  );
}

export function replayDiffSections(
  source: RecordValue,
  fork: RecordValue,
): ReplayDiffSection[] {
  const values: Array<[ReplayDiffSection["id"], unknown, unknown]> = [
    ["route", object(source.route), object(fork.route)],
    ["actions", actions(source), actions(fork)],
    ["speech", speech(source), speech(fork)],
    ["events", timeline(source), timeline(fork)],
  ];
  return values.map(([id, before, after]) => {
    const left = typeof before === "string" ? before : stable(before);
    const right = typeof after === "string" ? after : stable(after);
    return {
      id,
      changed: left !== right,
      parts: diffLines(`${left}\n`, `${right}\n`),
    };
  });
}
