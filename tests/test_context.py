"""Tests for bounded Turn context composition."""

from custom_components.llm_gateway.context import (
    ContextSlice,
    ExistingContextContributor,
    StaticContextContributor,
    TurnContextComposer,
    TurnContextRequest,
)


async def test_composer_preserves_existing_context_and_bounds_injections() -> None:
    composition = await TurnContextComposer().async_compose(
        TurnContextRequest(None, "fast", "general", budget_chars=5),
        (
            ExistingContextContributor(["HA context"]),
            StaticContextContributor("contract", "1234", priority=100),
            StaticContextContributor("memory", "abcdef", priority=50),
        ),
    )

    assert [item.id for item in composition.slices] == [
        "ha_llm_data",
        "contract",
        "memory",
    ]
    assert composition.slices[0].preexisting is True
    assert [item.content for item in composition.injected] == ["1234", "a"]
    assert composition.truncated == ("memory",)


async def test_composer_deduplicates_equal_content() -> None:
    class DuplicateContributor:
        async def async_get_context(self, _request):
            return ContextSlice("duplicate", "test", "same", 1)

    composition = await TurnContextComposer().async_compose(
        TurnContextRequest("conversation", "mid", "general"),
        (
            StaticContextContributor("first", "same", priority=2),
            DuplicateContributor(),
        ),
    )

    assert [item.id for item in composition.slices] == ["first"]
    assert composition.skipped == ("duplicate",)
