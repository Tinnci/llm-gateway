"""Tests for the shared reference resolution and commitment kernel."""

from __future__ import annotations

from custom_components.llm_gateway.resolution import (
    DeviceReference,
    resolution_frame_from_entity_resolution,
    resolve_device_referent,
)


def _lights() -> tuple[DeviceReference, ...]:
    return (
        DeviceReference(
            id="light.yeelight_monitor",
            name="Yeelight 显示器挂灯 灯",
            domain="light",
            areas=("卧室",),
        ),
        DeviceReference(
            id="light.devcea_1055",
            name="宜家麦希瑟E27 1055lm智能球泡灯 灯",
            domain="light",
            areas=("客厅",),
        ),
        DeviceReference(
            id="light.cbulb",
            name="彩光灯 灯",
            domain="light",
            areas=("客厅",),
        ),
    )


def test_numeric_device_reference_prefers_1055lm_with_evidence() -> None:
    frame = resolve_device_referent(
        raw_text="1,055 00 的那个灯",
        domain="light",
        action="turn_on",
        devices=_lights(),
    )

    referent = frame.referents[0]
    top = referent.candidates[0]

    assert frame.frame_type == "home_control"
    assert referent.slot == "target_device"
    assert top.id == "light.devcea_1055"
    assert "numeric_match:1055" in top.evidence
    assert frame.commitment.state == "targeted_clarify"
    assert "1055lm" in frame.commitment.prompt
    assert frame.commitment.interaction_state == "awaiting_user_info"


def test_asr_device_reference_records_alias_evidence() -> None:
    frame = resolve_device_referent(
        raw_text="米家麦西色灯",
        domain="light",
        action="turn_on",
        devices=_lights(),
    )

    top = frame.referents[0].candidates[0]

    assert top.id == "light.devcea_1055"
    assert "asr_normalization:麦西色≈麦希瑟" in top.evidence
    assert frame.commitment.state == "targeted_clarify"


def test_clear_area_device_reference_can_execute() -> None:
    frame = resolve_device_referent(
        raw_text="客厅灯",
        domain="light",
        action="turn_on",
        devices=(
            DeviceReference(
                id="light.living_room",
                name="客厅灯",
                domain="light",
                areas=(),
            ),
        ),
        area="客厅",
    )

    assert frame.referents[0].candidates[0].id == "light.living_room"
    assert frame.commitment.state == "execute"
    assert frame.commitment.reason == "high_confidence"


def test_person_resolution_frame_preserves_candidate_evidence() -> None:
    frame = resolution_frame_from_entity_resolution(
        operation="resolve_entity",
        raw_entity="Virginia Hope",
        entity_resolution={
            "raw_entity": "Virginia Hope",
            "canonical_entity_candidates": ["Virginia Woolf"],
            "correction_type": "asr",
            "confidence": 0.42,
            "evidence": [
                "low_confidence_asr_similarity",
                "known_literary_candidate",
            ],
        },
        answerability="ambiguous_entity",
    )

    referent = frame.referents[0]
    candidate = referent.candidates[0]

    assert frame.frame_type == "knowledge_query"
    assert referent.status == "ambiguous"
    assert candidate.name == "Virginia Woolf"
    assert "low_confidence_asr_similarity" in candidate.evidence
    assert frame.commitment.state == "targeted_clarify"
