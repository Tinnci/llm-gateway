"""Evidence grounding helpers for source-backed voice answers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from .policy import should_require_search

GroundingStatus = Literal["not_required", "no_answer", "no_evidence", "ok", "repaired"]

_CHINESE_TITLE_RE = re.compile(r"《([^》]{1,40})》")
_TITLE_SEPARATOR_RE = re.compile(r"[·・/／\-\s]+")


@dataclass(frozen=True, slots=True)
class GroundingResult:
    """Result of lightweight evidence verification."""

    status: GroundingStatus
    text: str
    candidates: list[str] = field(default_factory=list)
    repairs: list[dict[str, str]] = field(default_factory=list)

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
        }


def verify_and_repair_source_answer(
    user_text: str,
    assistant_text: str,
    search_results: list[dict[str, Any]],
) -> GroundingResult:
    """Repair obvious source-title drift against search evidence."""
    if not should_require_search(user_text):
        return GroundingResult(status="not_required", text=assistant_text)
    if not assistant_text:
        return GroundingResult(status="no_answer", text=assistant_text)

    candidates = source_title_candidates_from_results(search_results)
    if not candidates:
        return GroundingResult(status="no_evidence", text=assistant_text)

    repaired = assistant_text
    repairs: list[dict[str, str]] = []
    for answer_title in _CHINESE_TITLE_RE.findall(assistant_text):
        replacement = _repair_title(answer_title, candidates)
        if replacement and replacement != answer_title:
            repaired = repaired.replace(f"《{answer_title}》", f"《{replacement}》")
            repairs.append({"from": answer_title, "to": replacement})

    return GroundingResult(
        status="repaired" if repairs else "ok",
        text=repaired,
        candidates=candidates,
        repairs=repairs,
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


def _append_candidate(candidates: list[str], value: object) -> None:
    candidate = str(value or "").strip()
    if candidate and candidate not in candidates:
        candidates.append(candidate)


def _repair_title(answer_title: str, candidates: list[str]) -> str | None:
    segments = [part for part in _TITLE_SEPARATOR_RE.split(answer_title) if part]
    if not segments:
        return None
    for index, segment in enumerate(segments):
        for candidate in candidates:
            if segment == candidate:
                continue
            if _is_one_char_drift(segment, candidate):
                fixed = [*segments]
                fixed[index] = candidate
                return "·".join(fixed)
    return None


def _is_one_char_drift(left: str, right: str) -> bool:
    if len(left) != len(right) or not left or left == right:
        return False
    return sum(1 for a, b in zip(left, right, strict=True) if a != b) == 1
