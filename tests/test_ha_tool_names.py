"""HA namespaces cannot broaden tool permissions or rewrite dispatch names."""

from dataclasses import replace

import pytest

from custom_components.llm_gateway.capabilities import decide_route
from custom_components.llm_gateway.conversation import _filter_visible_tools
from custom_components.llm_gateway.ha_tool_names import canonical_ha_tool_name


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("GetLiveContext", "GetLiveContext"),
        ("homeassistant__GetLiveContext", "GetLiveContext"),
        ("intent__HassTurnOn", "HassTurnOn"),
        ("thirdparty__GetLiveContext", "thirdparty__GetLiveContext"),
        ("thirdparty__HassTurnOn", "thirdparty__HassTurnOn"),
        ("homeassistant__HassTurnOn", "homeassistant__HassTurnOn"),
    ],
)
def test_only_known_ha_namespaces_match_policy_names(name, expected):
    assert canonical_ha_tool_name(name) == expected


def test_visible_tools_keep_real_names_and_exclude_other_namespaces():
    route = replace(
        decide_route("打开卧室灯"), allowed_tools=("GetLiveContext", "HassTurnOn")
    )
    tools = [
        {"type": "function", "function": {"name": name}}
        for name in (
            "homeassistant__GetLiveContext",
            "intent__HassTurnOn",
            "intent__HassTurnOff",
            "thirdparty__GetLiveContext",
        )
    ]
    assert _filter_visible_tools(tools, route) == tools[:2]
