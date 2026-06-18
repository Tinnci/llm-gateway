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
_MAX_EVIDENCE_RESULTS = 4
_MAX_EVIDENCE_CHARS = 900


@dataclass(frozen=True, slots=True)
class GroundingResult:
    """Result of source evidence verification."""

    status: GroundingStatus
    text: str
    candidates: list[str] = field(default_factory=list)
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
    """Return early grounding states that do not require a verifier call."""
    if not should_require_search(user_text):
        return GroundingResult(status="not_required", text=assistant_text)
    if not assistant_text:
        return GroundingResult(status="no_answer", text=assistant_text)

    candidates = source_title_candidates_from_results(search_results)
    if not search_results:
        return GroundingResult(status="no_evidence", text=assistant_text)

    return GroundingResult(status="ok", text=assistant_text, candidates=candidates)


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
        "instructions": [
            "Verify the draft answer only against the provided evidence.",
            "Ignore unrelated titles or sidebars in snippets.",
            "If the draft answer has the wrong work title, rewrite it concisely.",
            "For Chinese classical text, preserve exact titles such as "
            "诗经, 周南, 关雎.",
            "Return one short Chinese spoken answer.",
        ],
    }
    return [
        {
            "role": "system",
            "content": (
                "You are a strict source-grounding verifier for a voice assistant. "
                "You do not control Home Assistant devices. Output JSON only."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
                "Return exactly this JSON shape: "
                '{"status":"supported|corrected|unsupported",'
                '"answer":"短中文答案","confidence":0.0,'
                '"reason":"brief evidence reason"}'
            ),
        },
    ]


def parse_grounding_verifier_response(
    content: str,
    *,
    fallback_text: str,
    candidates: list[str],
) -> GroundingResult:
    """Parse the verifier JSON response into a grounding result."""
    data = _parse_json_object(content)
    if not data:
        return GroundingResult(
            status="verifier_error",
            text=fallback_text,
            candidates=candidates,
            reason="verifier_returned_non_json",
        )

    answer = str(data.get("answer") or fallback_text).strip() or fallback_text
    status = str(data.get("status") or "supported").strip().lower()
    confidence = _bounded_confidence(data.get("confidence"))
    reason = str(data.get("reason") or "").strip()[:500]

    if status == "corrected" or answer != fallback_text:
        mapped: GroundingStatus = "repaired"
    elif status == "unsupported":
        mapped = "unsupported"
    else:
        mapped = "ok"

    repairs = []
    if answer != fallback_text:
        repairs.append({"from": fallback_text, "to": answer})
    return GroundingResult(
        status=mapped,
        text=answer,
        candidates=candidates,
        repairs=repairs,
        confidence=confidence,
        reason=reason,
        verifier={"mode": "model"},
    )


def enrich_search_result_with_grounding(result: dict[str, Any]) -> dict[str, Any]:
    """Add exact-title candidates to a search result payload."""
    candidates = source_title_candidates_from_results([result])
    if not candidates:
        return result
    return {
        **result,
        "source_candidates": candidates[:8],
        "grounding_instruction": (
            "For source/origin answers, use exact work titles from "
            "source_candidates or search snippets. Do not rename titles."
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
