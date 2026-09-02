import {
  array,
  looseObject,
  number,
  safeParse,
  string,
} from "valibot";
import type { InferOutput } from "valibot";

export type HarnessHttpMethod = "GET" | "POST";

export interface HomeAssistantApi {
  callApi?: (
    method: HarnessHttpMethod,
    path: string,
    payload?: unknown,
  ) => Promise<unknown>;
}

const rangeSchema = looseObject({ min: number(), max: number() });

const harnessStatusSchema = looseObject({
  entries: array(
    looseObject({
      entry_id: string(),
      state: string(),
      title: string(),
    }),
  ),
  editable: looseObject({
    max_tokens: rangeSchema,
    routing_modes: array(string()),
    timeouts: rangeSchema,
    trace_max_runs: rangeSchema,
    trace_retention_hours: rangeSchema,
  }),
});

export type HarnessStatusEnvelope = InferOutput<typeof harnessStatusSchema>;

export function parseHarnessStatus(input: unknown): HarnessStatusEnvelope {
  const result = safeParse(harnessStatusSchema, input);
  if (result.success) {
    return result.output;
  }
  const fields = result.issues
    .map((issue) => issue.path?.map((item) => String(item.key)).join("."))
    .filter(Boolean);
  const detail = fields.length ? `: ${[...new Set(fields)].join(", ")}` : "";
  throw new Error(`Invalid Voice Harness status response${detail}`);
}

export async function requestHarnessJson<T = unknown>(
  hass: HomeAssistantApi | null | undefined,
  method: HarnessHttpMethod,
  path: string,
  payload?: unknown,
): Promise<T> {
  if (hass?.callApi) {
    return (await hass.callApi(method, path, payload)) as T;
  }
  const response = await fetch(`/api/${path}`, {
    method,
    credentials: "same-origin",
    headers: payload === undefined ? undefined : { "Content-Type": "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  if (response.ok) {
    return (await response.json()) as T;
  }

  let message = `${response.status} ${response.statusText}`;
  let code = "";
  try {
    const body: unknown = await response.json();
    if (isRecord(body)) {
      message = typeof body.message === "string" ? body.message : message;
      code = typeof body.code === "string" ? body.code : "";
    }
  } catch {
    // Keep the HTTP status fallback when the response body is not JSON.
  }
  throw Object.assign(new Error(message), { code });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
