"""Tests for voice-safe Markdown rendering."""

from __future__ import annotations

from custom_components.llm_gateway.voice_text import markdown_to_spoken_text


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
    assert "代码内容已省略" in spoken


def test_markdown_to_spoken_text_limits_sentences():
    spoken = markdown_to_spoken_text("第一句。第二句！第三句？", max_sentences=2)
    assert spoken == "第一句。第二句！"
