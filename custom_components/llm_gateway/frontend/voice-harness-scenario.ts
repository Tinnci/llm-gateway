export type ScenarioDraft = {
  user: string;
  response: string;
  expected: string;
};

export type ParsedScenarioExpected = {
  valid: boolean;
  expected: Record<string, unknown>;
};

export type ScenarioCheck =
  | { kind: "required_fields"; ok: boolean }
  | { kind: "expected_json"; ok: boolean }
  | { kind: "search_gate"; ok: boolean; mustSearch: boolean }
  | { kind: "spoken_length"; ok: boolean; count: number; limit: number }
  | { kind: "question_length"; ok: boolean; count: number; limit: number }
  | { kind: "hidden_internals"; ok: boolean; terms: string[] }
  | { kind: "required_phrase"; ok: boolean; terms: string[] };

export type ScenarioEvaluationResult = {
  passed: boolean;
  spoken: string;
  route: {
    kind: "fast" | "mid";
    model: string;
  };
  search: {
    allowed: boolean;
  };
  violations: string[];
};

type SpokenExpectation = Record<string, unknown>;

const SENTENCE_RE = /[^.!?。！？]+[.!?。！？]?/g;
const QUESTION_RE = /[?？]/g;

export function parseScenarioExpected(value: unknown): ParsedScenarioExpected {
  try {
    const parsed = typeof value === "string" ? JSON.parse(value || "{}") : value;
    if (!isRecord(parsed)) {
      return { valid: false, expected: {} };
    }
    return { valid: true, expected: parsed };
  } catch (_err) {
    return { valid: false, expected: {} };
  }
}

export function searchProviders(entries: Record<string, unknown>[] = []): string[] {
  return [
    ...new Set(
      entries.flatMap((entry) => {
        const search = isRecord(entry.search) ? entry.search : {};
        return Array.isArray(search.providers) ? search.providers.map(String) : [];
      })
    ),
  ];
}

export function scenarioPreflight(
  draft: ScenarioDraft,
  entries: Record<string, unknown>[] = []
): ScenarioCheck[] {
  const providers = searchProviders(entries);
  const { valid, expected } = parseScenarioExpected(draft.expected);
  const spoken = spokenExpectation(expected);
  const required = requiredTerms(spoken);
  const forbidden = forbiddenTerms(spoken);
  const response = String(draft.response || "");
  const mentionedForbidden = termsInText(forbidden, response);
  const missingRequired = termsMissingFromText(required, response);
  const mustSearch = expected.must_search === true;
  const checks: ScenarioCheck[] = [
    {
      kind: "required_fields",
      ok: Boolean(String(draft.user || "").trim()) && Boolean(response.trim()),
    },
    { kind: "expected_json", ok: valid },
    {
      kind: "search_gate",
      ok: !mustSearch || providers.length > 0,
      mustSearch,
    },
  ];
  if (spoken.max_sentences != null) {
    const limit = Number(spoken.max_sentences);
    const count = sentenceCount(response);
    checks.push({ kind: "spoken_length", ok: count <= limit, count, limit });
  }
  if (spoken.max_questions != null) {
    const limit = Number(spoken.max_questions);
    const count = questionCount(response);
    checks.push({ kind: "question_length", ok: count <= limit, count, limit });
  }
  if (forbidden.length) {
    checks.push({
      kind: "hidden_internals",
      ok: mentionedForbidden.length === 0,
      terms: mentionedForbidden,
    });
  }
  if (required.length) {
    checks.push({
      kind: "required_phrase",
      ok: missingRequired.length === 0,
      terms: missingRequired,
    });
  }
  return checks;
}

export function evaluateScenarioDraft(payload: {
  user?: string;
  response?: string;
  expected?: unknown;
}): ScenarioEvaluationResult {
  const expected = parseScenarioExpected(payload.expected || {}).expected;
  const spoken = spokenExpectation(expected);
  const response = String(payload.response || "");
  const violations: string[] = [];
  if (spoken.max_sentences != null) {
    const count = sentenceCount(response);
    if (count > Number(spoken.max_sentences)) {
      violations.push(`spoken_response_too_long:${count}/${spoken.max_sentences}`);
    }
  }
  if (spoken.max_questions != null) {
    const count = questionCount(response);
    if (count > Number(spoken.max_questions)) {
      violations.push(`spoken_response_too_many_questions:${count}/${spoken.max_questions}`);
    }
  }
  for (const term of termsMissingFromText(requiredTerms(spoken), response)) {
    violations.push(`spoken_missing:${term}`);
  }
  for (const term of termsInText(forbiddenTerms(spoken), response)) {
    violations.push(`spoken_forbidden:${term}`);
  }
  const mustSearch = expected.must_search === true;
  return {
    passed: violations.length === 0,
    spoken: response,
    route: {
      kind: mustSearch ? "mid" : "fast",
      model: mustSearch ? "doubao-search" : "qwen-fast",
    },
    search: { allowed: mustSearch },
    violations,
  };
}

export function sentenceCount(text: string): number {
  const trimmed = String(text || "").trim();
  if (!trimmed) {
    return 0;
  }
  const matches = trimmed.match(SENTENCE_RE) || [];
  return Math.max(1, matches.filter((item) => item.trim()).length);
}

export function questionCount(text: string): number {
  return (String(text || "").match(QUESTION_RE) || []).length;
}

function spokenExpectation(expected: Record<string, unknown>): SpokenExpectation {
  const spoken =
    expected.spoken_response ||
    expected.expected_spoken_style ||
    {};
  return isRecord(spoken) ? spoken : {};
}

function requiredTerms(spoken: SpokenExpectation): string[] {
  return [
    ...(Array.isArray(spoken.must_include) ? spoken.must_include : []),
    ...(Array.isArray(spoken.must_mention) ? spoken.must_mention : []),
  ].map(String).filter(Boolean);
}

function forbiddenTerms(spoken: SpokenExpectation): string[] {
  return [
    ...(Array.isArray(spoken.must_not_mention) ? spoken.must_not_mention : []),
    ...(Array.isArray(spoken.must_not_include) ? spoken.must_not_include : []),
  ].map(String).filter(Boolean);
}

function termsInText(terms: string[], text: string): string[] {
  const haystack = String(text || "").toLowerCase();
  return terms.filter((term) => haystack.includes(term.toLowerCase()));
}

function termsMissingFromText(terms: string[], text: string): string[] {
  const haystack = String(text || "").toLowerCase();
  return terms.filter((term) => !haystack.includes(term.toLowerCase()));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
