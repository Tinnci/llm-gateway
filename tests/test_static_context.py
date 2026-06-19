"""Tests for deterministic static context inventory answers."""

from __future__ import annotations

from homeassistant.components import conversation

from custom_components.llm_gateway.static_context import (
    is_device_inventory_query,
    parse_static_devices,
    render_device_inventory_answer,
)

STATIC_CONTEXT = (
    "Static Context: An overview of the areas and the devices in this smart "
    "home:\n"
    "- names: Homepod mini\n"
    "  domain: media_player\n"
    "  areas: 客厅\n"
    "- names: 客厅灯\n"
    "  domain: light\n"
    "  areas: 客厅\n"
    "- names: 彩光灯 灯\n"
    "  domain: light\n"
    "  areas: 客厅\n"
    "- names: 卧室空调\n"
    "  domain: climate\n"
    "  areas: 卧室\n"
    "- names: Yeelight 显示器挂灯 灯\n"
    "  domain: light\n"
    "  areas: 卧室\n"
    "- names: 米家循环扇 风扇\n"
    "  domain: fan\n"
    "  areas: 卧室\n"
    "- names: 静安天气 PM2.5\n"
    "  domain: sensor\n"
)


def _content() -> list[conversation.Content]:
    return [conversation.SystemContent(content=STATIC_CONTEXT)]


def test_parse_static_devices_from_home_assistant_context() -> None:
    devices = parse_static_devices(STATIC_CONTEXT)

    assert len(devices) == 7
    assert devices[0].name == "Homepod mini"
    assert devices[0].domain == "media_player"
    assert devices[0].areas == ("客厅",)


def test_inventory_intent_uses_semantic_slots_not_exact_phrase_list() -> None:
    assert is_device_inventory_query("你现在接入了哪些东西？")
    assert is_device_inventory_query("家里有啥可以控制？")
    assert is_device_inventory_query("卧室都有啥？")
    assert not is_device_inventory_query("打开客厅灯")
    assert not is_device_inventory_query("今天天气怎么样？")
    assert not is_device_inventory_query("卧室温度是多少？")
    assert not is_device_inventory_query("静安天气 PM2.5 是多少？")


def test_render_inventory_summary_uses_exposed_device_wording() -> None:
    answer = render_device_inventory_answer("你能看到哪些设备？", _content())

    assert answer
    assert "已暴露给助手的设备" in answer
    assert "客厅灯" in answer
    assert "卧室空调" in answer
    assert "没有权限" not in answer


def test_render_inventory_filters_by_area() -> None:
    answer = render_device_inventory_answer("卧室有哪些设备？", _content())

    assert answer
    assert "卧室里" in answer
    assert "卧室空调" in answer
    assert "米家循环扇" in answer
    assert "客厅灯" not in answer


def test_render_inventory_filters_by_light_domain() -> None:
    answer = render_device_inventory_answer("有哪些灯？", _content())

    assert answer
    assert "已暴露给助手的灯" in answer
    assert "客厅灯" in answer
    assert "Yeelight 显示器挂灯" in answer
    assert "卧室空调" not in answer


def test_render_inventory_filters_weather_like_context() -> None:
    answer = render_device_inventory_answer("你能看到天气吗？", _content())

    assert answer
    assert "已暴露给助手的天气" in answer
    assert "静安天气 PM2.5" in answer


def test_render_inventory_lists_control_capabilities() -> None:
    answer = render_device_inventory_answer("你能控制什么？", _content())

    assert answer
    assert "我能控制已暴露给助手的" in answer
    assert "灯" in answer
    assert "空调" in answer
    assert "高风险设备仍需要先确认" in answer


def test_render_inventory_empty_context_does_not_claim_permission_loss() -> None:
    answer = render_device_inventory_answer("你能看到哪些设备？", [])

    assert answer == "我暂时看不到已暴露给助手的设备列表。"
