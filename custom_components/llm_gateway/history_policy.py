"""Model-visible history bounding for voice turns.

The HA chat log stays complete for humans; only the projection sent to the
provider is bounded — the same split dsh draws between its append-only
session log and the shadow-compacted model surface. Bounding is purely
structural: a message-count window that never splits an assistant tool-call
from its trailing tool results, plus one synthetic digest system note so the
model knows context was elided. There is no summarization call, so bounding
adds zero latency to the voice path.

@module llm_gateway.history_policy
"""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.json import json_dumps

MAX_HISTORY_MESSAGES = 40
"""Upper bound on provider-visible messages per model call."""

MIN_RECENT_MESSAGES = 12
"""Recent tail always kept verbatim once trimming starts."""

_DIGEST_TEMPLATE = (
    "[Earlier conversation omitted ({count} messages) to fit the voice turn "
    "budget; recent context follows.]"
)


def content_to_messages(content: list[Any]) -> list[dict[str, Any]]:
    """Convert HA chat-log content into OpenAI chat-completions messages."""
    messages: list[dict[str, Any]] = []
    for item in content:
        if item.role == "system":
            messages.append({"role": "system", "content": item.content})
        elif item.role == "user":
            messages.append({"role": "user", "content": item.content})
        elif item.role == "assistant":
            message: dict[str, Any] = {
                "role": "assistant",
                "content": item.content or "",
            }
            if item.tool_calls:
                message["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.tool_name,
                            "arguments": json_dumps(call.tool_args),
                        },
                    }
                    for call in item.tool_calls
                ]
            messages.append(message)
        elif item.role == "tool_result":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item.tool_call_id,
                    "content": json_dumps(item.tool_result),
                }
            )
    return messages


def _is_system(message: dict[str, Any]) -> bool:
    return message.get("role") == "system"


def _is_tool_result(message: dict[str, Any]) -> bool:
    return message.get("role") == "tool"


def bound_model_messages(
    messages: list[dict[str, Any]],
    *,
    max_messages: int = MAX_HISTORY_MESSAGES,
    min_recent: int = MIN_RECENT_MESSAGES,
) -> tuple[list[dict[str, Any]], int]:
    """Bound provider-visible messages, returning them plus the elided count.

    System messages are always retained. Trimming keeps the most recent
    non-system tail and never orphans a ``tool`` message away from the
    assistant ``tool_calls`` entry it answers: if the window would open
    between them, the orphaned tool results are dropped with the older
    span. A digest system note marks the elision point.
    """
    non_system = [index for index, m in enumerate(messages) if not _is_system(m)]
    overflow = len(non_system) - max_messages
    if overflow <= 0:
        return messages, 0

    keep = max(min_recent, len(non_system) - overflow)
    # Candidate cut inside `non_system`: keep the last `keep` entries.
    first_kept = non_system[len(non_system) - keep]

    # Never open the window between an assistant tool-call entry and the
    # tool results answering it: an orphaned `tool` message would reference
    # a call the model can no longer see. Advance past such strays.
    while first_kept < len(messages) and _is_tool_result(messages[first_kept]):
        first_kept += 1

    elided = sum(1 for index in range(first_kept) if not _is_system(messages[index]))
    if elided <= 0:
        return messages, 0

    digest = {
        "role": "system",
        "content": _DIGEST_TEMPLATE.format(count=elided),
    }
    bounded = [*messages[:first_kept], digest, *messages[first_kept:]]
    return bounded, elided


def bounded_chat_messages(
    content: list[Any],
    *,
    max_messages: int = MAX_HISTORY_MESSAGES,
    min_recent: int = MIN_RECENT_MESSAGES,
) -> tuple[list[dict[str, Any]], int]:
    """Convert chat-log content and bound it in one step."""
    return bound_model_messages(
        content_to_messages(content),
        max_messages=max_messages,
        min_recent=min_recent,
    )
