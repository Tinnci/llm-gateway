"""Tests for voice-safe Markdown rendering."""

from __future__ import annotations

import pytest

from custom_components.llm_gateway.voice_text import (
    TOOL_PROTOCOL_FALLBACK,
    enforce_output_contract,
    markdown_to_spoken_text,
    output_contract_error_speech,
)


def test_markdown_to_spoken_text_strips_formatting():
    spoken = markdown_to_spoken_text(
        "# 标题\n\n这是 **重要** 内容。\n\n- 第一项\n- [资料](https://example.com)"
    )
    assert spoken.startswith("标题 这是 重要 内容。")
    assert "第一项" in spoken
    assert "*" not in spoken
    assert "https://" not in spoken


def test_markdown_to_spoken_text_omits_code_fences():
    spoken = markdown_to_spoken_text("请看：\n```python\nprint('x')\n```\n下一步。")
    assert "```" not in spoken
    assert "print" not in spoken
    assert "代码已放到文本记录中" in spoken


def test_markdown_to_spoken_text_reads_short_unlabelled_quote_blocks():
    spoken = markdown_to_spoken_text(
        "这句话出自《诗经·周南·关雎》，原文是：\n\n```\n关关雎鸠，在河之洲。\n```\n"
    )
    assert "代码" not in spoken
    assert "关关雎鸠，在河之洲" in spoken


def test_markdown_to_spoken_text_limits_sentences():
    spoken = markdown_to_spoken_text("第一句。第二句！第三句？", max_sentences=2)
    assert spoken == "第一句。第二句！"


def test_captured_false_positive_now_passes_with_speakable_name():
    """The exact production sentence that misfired on 2026-08-23."""
    captured = (
        "目前我可以使用 search_web 工具来获取外部信息，"
        "例如查询可用的 AI 工具列表。通过该工具我可以检索最新的搜索结果。"
    )

    safe, modified, reason = enforce_output_contract(captured)

    assert not modified
    assert reason == ""
    assert "search_web" not in safe
    assert "联网搜索" in safe


def test_bare_ha_action_names_outside_json_pass():
    safe, modified, reason = enforce_output_contract(
        "你可以说打开客厅灯，我会调用相应的服务来完成。"
    )

    assert not modified
    assert reason == ""
    assert safe.startswith("你可以说")


@pytest.mark.parametrize(
    "payload",
    [
        '<tool_call>{"name":"search_web","arguments":{"q":"x"}}</tool_call>',
        '<tool_response>{"result":1}</tool_response>',
        '看这个 {"name": "HassTurnOn"} 的写法',
        '返回 {"tool_calls": []} 即可',
        "function= main()",
        '"arguments": {"query": "weather"}',
    ],
)
def test_structural_protocol_still_blocked(payload):
    safe, modified, reason = enforce_output_contract(payload)

    assert modified
    assert reason == "tool_protocol_leak"
    assert safe == TOOL_PROTOCOL_FALLBACK


def test_get_live_context_substituted_when_mentioned_in_prose():
    safe, modified, _reason = enforce_output_contract(
        "我可以调用 GetLiveContext 查状态。"
    )

    assert not modified
    assert "实时状态查询" in safe


def test_output_contract_blocks_tool_protocol_leaks():
    safe, modified, reason = enforce_output_contract(
        '<toolcall function="search_web" arguments="{\\"query\\":\\"weather\\"}" />'
    )

    assert modified
    assert reason == "tool_protocol_leak"
    assert safe == TOOL_PROTOCOL_FALLBACK


def test_output_contract_allows_plain_factual_text():
    safe, modified, reason = enforce_output_contract(
        "Virginia Woolf wrote Mrs Dalloway and To the Lighthouse."
    )

    assert not modified
    assert reason == ""
    assert safe.startswith("Virginia Woolf")


def test_output_contract_blocks_reasoning_repetition_loop():
    unsafe = (
        "We need to respond with spoken answer, plain text, no markdown. "
        'The user wants the full text. Likely "如梦令·常记溪亭日暮". '
        + 'She also wrote "如梦令·常记溪亭日暮". '
        * 12
    )

    safe, modified, reason = enforce_output_contract(unsafe)

    assert modified
    assert reason == "reasoning_repetition_leak"
    assert safe == output_contract_error_speech(reason)


def test_output_contract_retry_failed_speech_names_specific_problem():
    assert output_contract_error_speech("repetition_loop", retry_failed=True) == (
        "回答生成异常：重复内容循环。自动重试失败，请再试一次。"
    )
