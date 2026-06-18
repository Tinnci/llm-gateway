"""Evidence grounding helpers for source-backed voice answers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from .policy import should_require_search

GroundingStatus = Literal[
    "not_required",
    "no_answer",
    "no_evidence",
    "ok",
    "repaired",
    "unsupported",
    "verifier_error",
]

_CHINESE_TITLE_RE = re.compile(r"《([^》]{1,40})》")
_JSON_OBJECT_RE = re.compile(r"\{.*\}", flags=re.DOTALL)
_SOURCE_QUESTION_RE = re.compile(r"(出处|出自哪里|出自哪|来源|典故|原文)")
_DIRECT_SOURCE_RE = re.compile(r"出自《([^》]{1,80})》")
_WORK_IN_PARENT_RE = re.compile(r"《([^》]{1,30})》[^。；\n]{0,30}是《([^》]{1,80})》")
_MAX_EVIDENCE_RESULTS = 4
_MAX_EVIDENCE_CHARS = 900
_MAX_VERIFIER_RAW_EXCERPT = 240


@dataclass(frozen=True, slots=True)
class GroundingResult:
    """Result of source evidence verification."""

    status: GroundingStatus
    text: str
    candidates: list[str] = field(default_factory=list)
    canonical_answers: list[str] = field(default_factory=list)
    repairs: list[dict[str, str]] = field(default_factory=list)
    confidence: float | None = None
    reason: str = ""
    verifier: dict[str, Any] = field(default_factory=dict)

    @property
    def repaired(self) -> bool:
        """Return whether the verifier changed the answer."""
        return self.status == "repaired"

    def as_dict(self) -> dict[str, Any]:
        """Return a trace-safe representation."""
        return {
            "status": self.status,
            "candidates": self.candidates,
            "canonical_answers": self.canonical_answers,
            "repairs": self.repairs,
            "confidence": self.confidence,
            "reason": self.reason,
            "verifier": self.verifier,
        }


def initial_grounding_result(
    user_text: str,
    assistant_text: str,
    search_results: list[dict[str, Any]],
) -> GroundingResult:
    """Return cheap source-grounding state for the voice critical path."""
    if not _is_source_question(user_text) and not should_require_search(user_text):
        return GroundingResult(status="not_required", text=assistant_text)
    if not assistant_text:
        return GroundingResult(status="no_answer", text=assistant_text)

    candidates = source_title_candidates_from_results(search_results)
    canonical_answers = source_canonical_answers_from_results(search_results)
    if not search_results:
        return GroundingResult(
            status="not_required",
            text=assistant_text,
            reason="no_voice_path_evidence",
        )

    if len(canonical_answers) == 1:
        answer = _source_answer_sentence(canonical_answers[0])
        if _normalized(canonical_answers[0]) not in _normalized(assistant_text):
            return GroundingResult(
                status="repaired",
                text=answer,
                candidates=candidates,
                canonical_answers=canonical_answers,
                repairs=[{"from": assistant_text, "to": answer}],
                confidence=0.92,
                reason="single_canonical_evidence_answer",
                verifier={"mode": "cheap_evidence"},
            )

    if not canonical_answers:
        return GroundingResult(
            status="no_evidence",
            text=assistant_text,
            candidates=candidates,
            reason="no_canonical_source_answer",
            verifier={"mode": "cheap_evidence"},
        )

    return GroundingResult(
        status="ok",
        text=assistant_text,
        candidates=candidates,
        canonical_answers=canonical_answers,
        verifier={"mode": "cheap_evidence"},
    )


def build_grounding_verifier_messages(
    *,
    user_text: str,
    assistant_text: str,
    search_results: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build a narrow verifier sub-agent prompt."""
    payload = {
        "user_request": user_text,
        "draft_answer": assistant_text,
        "evidence": _evidence_for_prompt(search_results),
        "allowed_answers": source_canonical_answers_from_results(search_results),
        "instructions": [
            "Verify the draft answer only against the provided evidence.",
            "You are an auditor, not a writer.",
            "Ignore unrelated titles or sidebars in snippets.",
            "If the draft answer has the wrong work title, select exactly one "
            "string from allowed_answers.",
            "If allowed_answers is empty or insufficient, abstain.",
            "Never invent, merge, or reorder titles.",
            "For Chinese classical text, preserve exact titles such as "
            "诗经, 周南, 关雎.",
        ],
    }
    return [
        {
            "role": "system",
            "content": (
                "You are a strict source-grounding verifier for a voice assistant. "
                "You do not control Home Assistant devices. Output JSON only. "
                "Your selected_answer must be empty or exactly one allowed answer."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
                "Return exactly this JSON shape: "
                '{"verdict":"accept|select|reject|abstain",'
                '"selected_answer":"","confidence":0.0,'
                '"reason":"brief evidence reason"}'
            ),
        },
    ]


def parse_grounding_verifier_response(
    content: str,
    *,
    fallback_text: str,
    candidates: list[str],
    canonical_answers: list[str] | None = None,
) -> GroundingResult:
    """Parse the verifier JSON response into a grounding result."""
    allowed_answers = canonical_answers or []
    data = _parse_json_object(content)
    if not data:
        return GroundingResult(
            status="verifier_error",
            text=fallback_text,
            candidates=candidates,
            canonical_answers=allowed_answers,
            reason="verifier_returned_non_json",
            verifier={
                "mode": "model",
                "raw_excerpt": _raw_excerpt(content),
            },
        )

    selected = str(data.get("selected_answer") or data.get("answer") or "").strip()
    verdict = str(data.get("verdict") or data.get("status") or "accept").strip().lower()
    confidence = _bounded_confidence(data.get("confidence"))
    reason = str(data.get("reason") or "").strip()[:500]

    if verdict in {"select", "corrected"} and selected:
        if selected not in allowed_answers:
            return GroundingResult(
                status="verifier_error",
                text=fallback_text,
                candidates=candidates,
                canonical_answers=allowed_answers,
                confidence=confidence,
                reason="verifier_selected_unlisted_answer",
                verifier={
                    "mode": "model",
                    "selected_answer": selected[:160],
                },
            )
        answer = _source_answer_sentence(selected)
        mapped: GroundingStatus = "repaired"
    elif verdict in {"reject", "unsupported"}:
        answer = fallback_text
        mapped = "unsupported"
    else:
        answer = fallback_text
        mapped = "ok"

    repairs = []
    if answer != fallback_text:
        repairs.append({"from": fallback_text, "to": answer})
    return GroundingResult(
        status=mapped,
        text=answer,
        candidates=candidates,
        canonical_answers=allowed_answers,
        repairs=repairs,
        confidence=confidence,
        reason=reason,
        verifier={"mode": "model", "verdict": verdict},
    )


def enrich_search_result_with_grounding(result: dict[str, Any]) -> dict[str, Any]:
    """Add exact-title candidates to a search result payload."""
    candidates = source_title_candidates_from_results([result])
    canonical_answers = source_canonical_answers_from_results([result])
    if not candidates and not canonical_answers:
        return result
    return {
        **result,
        "source_candidates": candidates[:8],
        "source_canonical_answers": canonical_answers[:4],
        "grounding_instruction": (
            "For source/origin answers, prefer source_canonical_answers. "
            "Do not build new titles by combining unrelated source_candidates."
        ),
    }


def source_title_candidates_from_results(
    search_results: list[dict[str, Any]],
) -> list[str]:
    """Extract unique Chinese book/article title candidates from search results."""
    candidates: list[str] = []
    for result in search_results:
        for candidate in result.get("source_candidates") or []:
            _append_candidate(candidates, candidate)
        for item in result.get("results") or []:
            if not isinstance(item, dict):
                continue
            text = f"{item.get('title') or ''}\n{item.get('content') or ''}"
            for candidate in _CHINESE_TITLE_RE.findall(text):
                _append_candidate(candidates, candidate)
    return candidates


def source_canonical_answers_from_results(
    search_results: list[dict[str, Any]],
) -> list[str]:
    """Extract canonical source answers backed by one evidence item."""
    answers: list[str] = []
    for result in search_results:
        for candidate in result.get("source_canonical_answers") or []:
            _append_candidate(answers, candidate)
        for item in result.get("results") or []:
            if not isinstance(item, dict):
                continue
            _append_canonical_answers_from_text(
                answers,
                f"{item.get('title') or ''}\n{item.get('content') or ''}",
            )
    return answers


def _evidence_for_prompt(search_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for result in search_results:
        for item in result.get("results") or []:
            if not isinstance(item, dict):
                continue
            evidence.append(
                {
                    "title": str(item.get("title") or "")[:220],
                    "url": str(item.get("url") or "")[:500],
                    "content": str(item.get("content") or "")[:_MAX_EVIDENCE_CHARS],
                }
            )
            if len(evidence) >= _MAX_EVIDENCE_RESULTS:
                return evidence
    return evidence


def _parse_json_object(content: str) -> dict[str, Any] | None:
    text = str(content or "").strip()
    match = _JSON_OBJECT_RE.search(text)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _raw_excerpt(content: str) -> str:
    text = re.sub(r"\s+", " ", str(content or "")).strip()
    return text[:_MAX_VERIFIER_RAW_EXCERPT]


def _append_canonical_answers_from_text(answers: list[str], text: str) -> None:
    normalized = _normalized(text)
    for match in _DIRECT_SOURCE_RE.findall(text):
        _append_candidate(answers, f"《{match}》")

    for child, parent in _WORK_IN_PARENT_RE.findall(text):
        if child and parent and child not in parent:
            _append_candidate(answers, f"《{parent}·{child}》")

    if "关雎" in normalized and "诗经" in normalized and "周南" in normalized:
        if "国风" in normalized:
            _append_candidate(answers, "《诗经·国风·周南·关雎》")
        _append_candidate(answers, "《诗经·周南·关雎》")


def _source_answer_sentence(answer: str) -> str:
    return f"这句诗出自{answer}。"


def _is_source_question(text: str) -> bool:
    return bool(_SOURCE_QUESTION_RE.search(text))


def _normalized(text: str) -> str:
    return re.sub(r"[\s《》「」『』“”\"'`·.。,:：，、_\-—]+", "", str(text or ""))


def _bounded_confidence(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, parsed))


def _append_candidate(candidates: list[str], value: object) -> None:
    candidate = str(value or "").strip()
    if candidate and candidate not in candidates:
        candidates.append(candidate)
