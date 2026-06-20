"""Reference resolution kernel and commitment policy.

The router decides what the user is trying to do.  This module decides what the
user is referring to, how confident the system is, and whether the current risk
level permits execution or only clarification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

ReferentKind = Literal["device", "person", "location", "time", "area", "unknown"]
ReferentStatus = Literal["unresolved", "resolved", "ambiguous", "missing"]
CommitmentState = Literal[
    "execute",
    "answer",
    "targeted_clarify",
    "list_candidates",
    "ask_missing_slot",
    "blocked",
    "high_risk_confirm",
]

_NORMALIZE_RE = re.compile(r"[\s《》「」『』“”\"'`·.。,:：，、_\-—!?！？]+")
_DIGIT_RE = re.compile(r"\d+")
_LIGHT_DOMAIN_ALIASES = {"light": "灯", "fan": "风扇", "media_player": "播放器"}
_ASR_NORMALIZATIONS = (
    ("麦西色", "麦希瑟"),
    ("麦希色", "麦希瑟"),
    ("麦瑟色", "麦希瑟"),
    ("米家", "宜家"),
)
_TARGET_FILLER_WORDS = (
    "那个",
    "这个",
    "的",
    "一下",
    "帮我",
    "请",
)

EXECUTE_THRESHOLD = 0.96
TARGETED_CLARIFY_THRESHOLD = 0.72
LIST_CANDIDATE_THRESHOLD = 0.45
CLOSE_CANDIDATE_DELTA = 0.08
MIN_NUMERIC_TOKEN_LEN = 3
NUMERIC_PREFIX_LEN = 4


@dataclass(frozen=True, slots=True)
class Candidate:
    """One possible target for a referent."""

    id: str
    name: str
    score: float
    evidence: tuple[str, ...] = ()
    source: str = ""
    rejected_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "score": round(self.score, 3),
            "evidence": list(self.evidence),
            "source": self.source,
            "rejected_reason": self.rejected_reason,
        }


@dataclass(frozen=True, slots=True)
class Referent:
    """A user-mentioned object slot and its candidate lattice."""

    slot: str
    kind: ReferentKind
    raw_text: str
    normalized_text: str
    candidates: tuple[Candidate, ...] = ()
    status: ReferentStatus = "unresolved"

    def as_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "kind": self.kind,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "status": self.status,
            "candidates": [candidate.as_dict() for candidate in self.candidates],
        }


@dataclass(frozen=True, slots=True)
class CommitmentDecision:
    """Whether this frame can act/answer or must ask the user first."""

    state: CommitmentState
    reason: str
    prompt: str = ""
    interaction_state: str = "classifying"
    earcon: str | None = None
    display_state: str = "thinking"
    allowed_next_user_actions: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "reason": self.reason,
            "prompt": self.prompt,
            "interaction_state": self.interaction_state,
            "earcon": self.earcon,
            "display_state": self.display_state,
            "allowed_next_user_actions": list(self.allowed_next_user_actions),
        }


@dataclass(frozen=True, slots=True)
class SemanticResolutionFrame:
    """Frame + referents + commitment in one auditable object."""

    frame_type: str
    operation: str
    constraints: dict[str, Any] = field(default_factory=dict)
    referents: tuple[Referent, ...] = ()
    risk: str = "low"
    commitment: CommitmentDecision = field(
        default_factory=lambda: CommitmentDecision(
            state="blocked",
            reason="not_evaluated",
            interaction_state="blocked",
            display_state="blocked",
        )
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "frame_type": self.frame_type,
            "operation": self.operation,
            "constraints": dict(self.constraints),
            "referents": [referent.as_dict() for referent in self.referents],
            "risk": self.risk,
            "commitment": self.commitment.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class DeviceReference:
    """Minimal entity view consumed by the device resolver."""

    id: str
    name: str
    domain: str
    areas: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    state: str = ""
    source: str = "ha_state"


def normalize_reference_text(text: str) -> str:
    """Normalize ASR spelling, punctuation, spaces, and common alias variants."""
    value = _NORMALIZE_RE.sub("", str(text or "")).lower()
    for source, target in _ASR_NORMALIZATIONS:
        value = value.replace(source, target)
    for word in _TARGET_FILLER_WORDS:
        value = value.replace(word, "")
    return value


def resolve_device_referent(  # noqa: PLR0913 - public kernel API mirrors frame context.
    *,
    raw_text: str,
    domain: str,
    action: str,
    devices: tuple[DeviceReference, ...],
    area: str = "",
    risk: str = "low",
) -> SemanticResolutionFrame:
    """Resolve a home-control target device and make a commitment decision."""
    normalized = normalize_reference_text(raw_text)
    candidates = tuple(
        sorted(
            (
                candidate
                for device in devices
                if device.domain == domain
                if (
                    candidate := _score_device(
                        device, raw_text, normalized, domain, area
                    )
                )
                and candidate.score >= LIST_CANDIDATE_THRESHOLD
            ),
            key=lambda item: item.score,
            reverse=True,
        )
    )
    referent = Referent(
        slot="target_device",
        kind="device",
        raw_text=raw_text,
        normalized_text=normalized,
        candidates=candidates,
        status=_referent_status(candidates),
    )
    commitment = _device_commitment(
        referent=referent,
        domain=domain,
        risk=risk,
    )
    return SemanticResolutionFrame(
        frame_type="home_control",
        operation=action,
        constraints={"domain": domain, "area": area},
        referents=(referent,),
        risk=risk,
        commitment=commitment,
    )


def resolution_frame_from_entity_resolution(
    *,
    operation: str,
    raw_entity: str,
    entity_resolution: dict[str, Any],
    answerability: str,
) -> SemanticResolutionFrame:
    """Convert existing person/entity resolution into the common frame schema."""
    evidence = tuple(str(item) for item in entity_resolution.get("evidence", ()))
    correction_type = str(entity_resolution.get("correction_type") or "none")
    if correction_type != "none" and not evidence:
        evidence = (f"{correction_type}_correction",)
    candidates = tuple(
        Candidate(
            id=str(candidate),
            name=str(candidate),
            score=float(entity_resolution.get("confidence") or 0.0),
            evidence=evidence or ("entity_resolution_candidate",),
            source="known_entity_index",
        )
        for candidate in entity_resolution.get("canonical_entity_candidates", ())
    )
    referent = Referent(
        slot="person",
        kind="person",
        raw_text=raw_entity,
        normalized_text=normalize_reference_text(raw_entity),
        candidates=candidates,
        status="ambiguous" if answerability == "ambiguous_entity" else "resolved",
    )
    commitment = (
        CommitmentDecision(
            state="targeted_clarify",
            reason="ambiguous_entity",
            prompt="",
            interaction_state="awaiting_user_info",
            display_state="clarifying",
            allowed_next_user_actions=("clarify_entity", "search"),
        )
        if answerability == "ambiguous_entity"
        else CommitmentDecision(
            state="answer",
            reason="high_confidence_entity",
            interaction_state="committed_answering",
            display_state="done",
        )
    )
    return SemanticResolutionFrame(
        frame_type="knowledge_query",
        operation=operation,
        referents=(referent,),
        commitment=commitment,
    )


def weather_resolution_frame(
    *,
    operation: str,
    location_hint: str,
    time_horizon: str,
    missing_requirements: tuple[str, ...],
) -> SemanticResolutionFrame:
    """Return the common resolution frame for weather location/time slots."""
    referents = (
        Referent(
            slot="location",
            kind="location",
            raw_text=location_hint,
            normalized_text=normalize_reference_text(location_hint),
            status="missing" if "location_hint" in missing_requirements else "resolved",
        ),
        Referent(
            slot="time",
            kind="time",
            raw_text=time_horizon,
            normalized_text=time_horizon,
            status="resolved" if time_horizon else "missing",
        ),
    )
    if missing_requirements:
        commitment = CommitmentDecision(
            state="ask_missing_slot",
            reason="missing_location",
            prompt="你想查哪个地方明天的天气？",
            interaction_state="awaiting_user_info",
            display_state="clarifying",
            allowed_next_user_actions=("provide_location", "cancel"),
        )
    else:
        commitment = CommitmentDecision(
            state="execute",
            reason="required_referents_resolved",
            interaction_state="searching",
            earcon="search",
            display_state="searching",
        )
    return SemanticResolutionFrame(
        frame_type="weather_forecast",
        operation=operation,
        constraints={"time_horizon": time_horizon},
        referents=referents,
        commitment=commitment,
    )


def _score_device(  # noqa: PLR0912 - explicit evidence scoring keeps resolution auditable.
    device: DeviceReference,
    raw_mention: str,
    normalized_mention: str,
    domain: str,
    area: str,
) -> Candidate | None:
    names = (device.name, *device.aliases)
    normalized_names = tuple(normalize_reference_text(name) for name in names if name)
    if not normalized_names:
        return None

    score = 0.0
    evidence: list[str] = []
    if device.domain == domain:
        score += 0.18
        evidence.append(f"domain_match:{domain}")

    normalized_device_name = normalize_reference_text(device.name)
    if area and (area in device.areas or area in normalized_device_name):
        score += 0.25
        evidence.append(f"area_match:{area}")
    elif area:
        score -= 0.18
        evidence.append(f"area_mismatch:{area}")

    if normalized_mention:
        if "已确认" in str(raw_mention or ""):
            score += 0.35
            evidence.append("confirmed_target")
        best_name = max(
            normalized_names, key=lambda name: _overlap_score(normalized_mention, name)
        )
        overlap = _overlap_score(normalized_mention, best_name)
        if overlap:
            score += overlap * 0.38
            evidence.append(f"lexical_overlap:{overlap:.2f}")
        if normalized_mention in best_name or best_name in normalized_mention:
            score += 0.24
            evidence.append("substring_match")
        if _asr_variant_evidence(normalized_mention, device.name):
            score += 0.25
            evidence.append(_asr_variant_evidence(normalized_mention, device.name))
        numeric = _numeric_evidence(normalized_mention, best_name)
        if numeric:
            score += 0.34
            evidence.append(numeric)
    elif area and domain:
        score += 0.5
        evidence.append("area_domain_target")

    domain_label = _LIGHT_DOMAIN_ALIASES.get(domain, domain)
    if domain_label and domain_label in normalize_reference_text(device.name):
        score += 0.08
        evidence.append(f"name_domain_label:{domain_label}")

    score = max(0.0, min(1.0, score))
    if not evidence:
        return None
    return Candidate(
        id=device.id,
        name=device.name,
        score=score,
        evidence=tuple(evidence),
        source=device.source,
    )


def _device_commitment(
    *,
    referent: Referent,
    domain: str,
    risk: str,
) -> CommitmentDecision:
    if risk == "high":
        return CommitmentDecision(
            state="high_risk_confirm",
            reason="high_risk",
            prompt="这个需要确认。",
            interaction_state="confirming_high_risk",
            earcon="confirmation",
            display_state="confirming",
            allowed_next_user_actions=("confirm", "cancel"),
        )
    candidates = referent.candidates
    if not candidates:
        return CommitmentDecision(
            state="ask_missing_slot",
            reason="no_matching_entity",
            prompt=f"你想操作哪个{_LIGHT_DOMAIN_ALIASES.get(domain, '设备')}？",
            interaction_state="awaiting_user_info",
            display_state="clarifying",
            allowed_next_user_actions=("provide_target", "cancel"),
        )
    top = candidates[0]
    if len(candidates) > 1 and candidates[1].score >= top.score - CLOSE_CANDIDATE_DELTA:
        return CommitmentDecision(
            state="list_candidates",
            reason="ambiguous_target",
            prompt=_list_candidate_prompt(domain, candidates),
            interaction_state="awaiting_user_info",
            display_state="clarifying",
            allowed_next_user_actions=("choose_candidate", "cancel"),
        )
    if top.score >= EXECUTE_THRESHOLD and not _needs_confirmation_for_evidence(top):
        return CommitmentDecision(
            state="execute",
            reason="high_confidence",
            interaction_state="committed_executing",
            display_state="executing",
        )
    if top.score >= TARGETED_CLARIFY_THRESHOLD:
        return CommitmentDecision(
            state="targeted_clarify",
            reason="score_near_threshold",
            prompt=f"你是说{_spoken_candidate_label(top)}吗？",
            interaction_state="awaiting_user_info",
            display_state="clarifying",
            allowed_next_user_actions=("confirm", "provide_target", "cancel"),
        )
    return CommitmentDecision(
        state="ask_missing_slot",
        reason="low_target_confidence",
        prompt=(
            f"我没确定是哪一个{_LIGHT_DOMAIN_ALIASES.get(domain, '设备')}。"
            "可以说房间或名字。"
        ),
        interaction_state="awaiting_user_info",
        display_state="clarifying",
        allowed_next_user_actions=("provide_target", "cancel"),
    )


def _referent_status(candidates: tuple[Candidate, ...]) -> ReferentStatus:
    if not candidates:
        return "unresolved"
    if (
        len(candidates) > 1
        and candidates[1].score >= candidates[0].score - CLOSE_CANDIDATE_DELTA
    ):
        return "ambiguous"
    return "resolved"


def _needs_confirmation_for_evidence(candidate: Candidate) -> bool:
    if "confirmed_target" in candidate.evidence:
        return False
    return any(
        item.startswith(("numeric_match", "asr_normalization"))
        for item in candidate.evidence
    )


def _overlap_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    left_chars = set(left)
    right_chars = set(right)
    return len(left_chars & right_chars) / max(len(left_chars), 1)


def _numeric_evidence(mention: str, candidate_name: str) -> str:
    mention_numbers = _DIGIT_RE.findall(mention)
    candidate_numbers = _DIGIT_RE.findall(candidate_name)
    for mention_number in mention_numbers:
        if len(mention_number) >= MIN_NUMERIC_TOKEN_LEN:
            prefix = (
                mention_number[:NUMERIC_PREFIX_LEN]
                if len(mention_number) >= NUMERIC_PREFIX_LEN
                else mention_number
            )
            if prefix in candidate_name:
                return f"numeric_match:{prefix}"
        for candidate_number in candidate_numbers:
            if len(candidate_number) >= MIN_NUMERIC_TOKEN_LEN and (
                mention_number.startswith(candidate_number)
                or candidate_number.startswith(mention_number)
            ):
                return f"numeric_match:{candidate_number}"
    return ""


def _asr_variant_evidence(normalized_mention: str, candidate_name: str) -> str:
    candidate = normalize_reference_text(candidate_name)
    if "麦希瑟" in normalized_mention and "麦希瑟" in candidate:
        return "asr_normalization:麦西色≈麦希瑟"
    return ""


def _list_candidate_prompt(domain: str, candidates: tuple[Candidate, ...]) -> str:
    label = _LIGHT_DOMAIN_ALIASES.get(domain, "设备")
    names = "、".join(
        _spoken_candidate_label(candidate) for candidate in candidates[:2]
    )
    return f"我找到几个{label}，是{names}？"


def _spoken_candidate_label(candidate: Candidate) -> str:
    name = candidate.name
    if "1055" in name:
        return "宜家 1055lm 那个灯"
    return name
