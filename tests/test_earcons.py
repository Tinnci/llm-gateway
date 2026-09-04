"""Tests for the canonical generated earcon manifest."""

from custom_components.llm_gateway.earcons import EARCON_PACK, earcon_library
from custom_components.llm_gateway.feedback import EARCON_LIBRARY


def test_feedback_policy_uses_generated_earcon_metadata() -> None:
    library = earcon_library()

    assert EARCON_PACK == "ha_voice_minimal_v0"
    assert library == EARCON_LIBRARY
    assert library["confirmation"]["priority"] == 90
    assert library["thinking"]["quiet_hours_behavior"] == "suppress_noncritical"
    assert library["provider_fallback"]["path"] == "provider_fallback.wav"
