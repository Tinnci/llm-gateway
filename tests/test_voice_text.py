"""Tests for voice-safe Markdown rendering."""

from __future__ import annotations

from custom_components.llm_gateway.voice_text import (
    TOOL_PROTOCOL_FALLBACK,
    enforce_output_contract,
    markdown_to_spoken_text,
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
