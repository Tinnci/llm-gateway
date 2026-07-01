// custom_components/llm_gateway/frontend/voice-harness-scenario.ts
var SENTENCE_RE = /[^.!?。！？]+[.!?。！？]?/g;
var QUESTION_RE = /[?？]/g;
function parseScenarioExpected(value) {
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
function searchProviders(entries = []) {
  return [
    ...new Set(entries.flatMap((entry) => {
      const search = isRecord(entry.search) ? entry.search : {};
      return Array.isArray(search.providers) ? search.providers.map(String) : [];
    }))
  ];
}
function scenarioPreflight(draft, entries = []) {
  const providers = searchProviders(entries);
  const { valid, expected } = parseScenarioExpected(draft.expected);
  const spoken = spokenExpectation(expected);
  const required = requiredTerms(spoken);
  const forbidden = forbiddenTerms(spoken);
  const response = String(draft.response || "");
  const mentionedForbidden = termsInText(forbidden, response);
  const missingRequired = termsMissingFromText(required, response);
  const mustSearch = expected.must_search === true;
  const checks = [
    {
      kind: "required_fields",
      ok: Boolean(String(draft.user || "").trim()) && Boolean(response.trim())
    },
    { kind: "expected_json", ok: valid },
    {
      kind: "search_gate",
      ok: !mustSearch || providers.length > 0,
      mustSearch
    }
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
      terms: mentionedForbidden
    });
  }
  if (required.length) {
    checks.push({
      kind: "required_phrase",
      ok: missingRequired.length === 0,
      terms: missingRequired
    });
  }
  return checks;
}
function evaluateScenarioDraft(payload) {
  const expected = parseScenarioExpected(payload.expected || {}).expected;
  const spoken = spokenExpectation(expected);
  const response = String(payload.response || "");
  const violations = [];
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
      model: mustSearch ? "doubao-search" : "qwen-fast"
    },
    search: { allowed: mustSearch },
    violations
  };
}
function sentenceCount(text) {
  const trimmed = String(text || "").trim();
  if (!trimmed) {
    return 0;
  }
  const matches = trimmed.match(SENTENCE_RE) || [];
  return Math.max(1, matches.filter((item) => item.trim()).length);
}
function questionCount(text) {
  return (String(text || "").match(QUESTION_RE) || []).length;
}
function spokenExpectation(expected) {
  const spoken = expected.spoken_response || expected.expected_spoken_style || {};
  return isRecord(spoken) ? spoken : {};
}
function requiredTerms(spoken) {
  return [
    ...Array.isArray(spoken.must_include) ? spoken.must_include : [],
    ...Array.isArray(spoken.must_mention) ? spoken.must_mention : []
  ].map(String).filter(Boolean);
}
function forbiddenTerms(spoken) {
  return [
    ...Array.isArray(spoken.must_not_mention) ? spoken.must_not_mention : [],
    ...Array.isArray(spoken.must_not_include) ? spoken.must_not_include : []
  ].map(String).filter(Boolean);
}
function termsInText(terms, text) {
  const haystack = String(text || "").toLowerCase();
  return terms.filter((term) => haystack.includes(term.toLowerCase()));
}
function termsMissingFromText(terms, text) {
  const haystack = String(text || "").toLowerCase();
  return terms.filter((term) => !haystack.includes(term.toLowerCase()));
}
function isRecord(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
export {
  sentenceCount,
  searchProviders,
  scenarioPreflight,
  questionCount,
  parseScenarioExpected,
  evaluateScenarioDraft
};
