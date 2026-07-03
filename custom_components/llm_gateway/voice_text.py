"""Voice-safe text rendering for TTS."""

from __future__ import annotations

import re
from typing import Any

import mistune

_MARKDOWN = mistune.create_markdown(renderer="ast", plugins=["table"])
_MAX_SPOKEN_BLOCK_CHARS = 120
_MAX_SPOKEN_BLOCK_NEWLINES = 2
_WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_URL_RE = re.compile(r"https?://\S+")
_MARKDOWN_CONTROL_RE = re.compile(r"[*_`#>|~\[\]{}]")
_SENTENCE_END_RE = re.compile(r"(?<=[。！？!?])")
_FENCED_CODE_RE = re.compile(r"```([^\n`]*)\n?(.*?)```", flags=re.DOTALL)
_CODE_HINT_RE = re.compile(
    r"(^|\s)(async\s+def|def|class|function|const|let|var|import|from|return|"
    r"print\s*\(|curl\s+|docker\s+|git\s+|uv\s+|SELECT\s+|INSERT\s+|UPDATE\s+)",
    flags=re.IGNORECASE,
)
_CODE_SYMBOL_RE = re.compile(r"(\{|\}|=>|==|!=|<=|>=|;|</|/>|\w+\([^)]*\))")
_TOOL_PROTOCOL_RE = re.compile(
    r"(<\s*/?\s*tool[_-]?call\b|"
    r"\bfunction\s*=|"
    r"\barguments\s*=|"
    r"\bsearch[_-]?web\b|"
    r"\btool_calls?\b|"
    r"\bHass(?:TurnOn|TurnOff|CallService)\b|"
    r"\bGetLiveContext\b)",
    re.IGNORECASE,
)
_REASONING_LEAK_RE = re.compile(
    r"(^|\n)\s*(we need to respond|we need to answer|we should answer|"
    r"the user wants|the user asks|likely\b|need to provide|"
    r"analysis\s*:|reasoning\s*:|final answer\s*:|"
    r"需要回答用户|用户想要|用户要求|我们需要回答)",
    re.IGNORECASE,
)
_REASONING_META_RE = re.compile(
    r"\b(spoken answer|plain text,?\s*no markdown|the user wants to|"
    r"the user asks for|system prompt|assistant response)\b",
    re.IGNORECASE,
)
_QUOTED_PHRASE_RE = re.compile(r"[\"'“”‘’]([^\"'“”‘’]{4,80})[\"'“”‘’]")
_SENTENCE_CHUNK_RE = re.compile(r"[。！？!?;；\n]+")
_LOOP_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]")
_MIN_LOOP_TEXT_CHARS = 180
_MIN_REPEATED_PHRASE_CHARS = 4
_REPEATED_PHRASE_LIMIT = 4
_MIN_REPEATED_CHUNK_CHARS = 12
_MAX_REPEATED_CHUNK_CHARS = 160
_REPEATED_CHUNK_LIMIT = 4
_MIN_LOOP_TOKENS = 60
_MIN_LOOP_NGRAM_WIDTH = 4
_MAX_LOOP_NGRAM_WIDTH = 10
_REPEATED_NGRAM_LIMIT = 8
TOOL_PROTOCOL_FALLBACK = "我不能直接展示内部工具调用。请换个说法或稍后重试。"
_OUTPUT_CONTRACT_REASON_LABELS = {
    "tool_protocol_leak": "内部工具调用泄漏",
    "reasoning_leak": "内部推理文本泄漏",
    "repetition_loop": "重复内容循环",
    "reasoning_repetition_leak": "内部推理文本泄漏并出现重复循环",
}
_OUTPUT_CONTRACT_DEFAULT_LABEL = "模型输出不适合播报"


def markdown_to_spoken_text(
    markdown_text: str | None, *, max_sentences: int = 2
) -> str:
    """Convert Markdown into concise plain text suitable for TTS."""
    if not markdown_text:
        return ""

    try:
        blocks = _MARKDOWN(markdown_text)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        text = _fallback_strip(markdown_text)
    else:
        text = "\n".join(
            part for token in blocks if (part := _render_token(token).strip())
        )

    text = _normalize_text(text)
    return _limit_sentences(text, max_sentences=max_sentences)


def enforce_output_contract(text: str | None) -> tuple[str, bool, str]:
    """Return voice-safe final text and whether internal protocol text was blocked."""
    value = str(text or "").strip()
    if not value:
        return "", False, ""
    reasoning_leak = _looks_like_reasoning_leak(value)
    repetition_loop = _has_repetition_loop(value)
    if reasoning_leak and repetition_loop:
        return (
            output_contract_error_speech("reasoning_repetition_leak"),
            True,
            "reasoning_repetition_leak",
        )
    if reasoning_leak:
        return output_contract_error_speech("reasoning_leak"), True, "reasoning_leak"
    if repetition_loop:
        return (
            output_contract_error_speech("repetition_loop"),
            True,
            "repetition_loop",
        )
    if _TOOL_PROTOCOL_RE.search(value):
        return TOOL_PROTOCOL_FALLBACK, True, "tool_protocol_leak"
    return value, False, ""


def output_contract_reason_label(reason: str) -> str:
    """Return a short user-facing label for an output-contract failure."""
    return _OUTPUT_CONTRACT_REASON_LABELS.get(reason, _OUTPUT_CONTRACT_DEFAULT_LABEL)


def output_contract_error_speech(reason: str, *, retry_failed: bool = False) -> str:
    """Return concise speech that explains why the unsafe answer was not spoken."""
    label = output_contract_reason_label(reason)
    if retry_failed:
        return f"回答生成异常：{label}。自动重试失败，请再试一次。"
    return f"回答生成异常：{label}。已停止播报，请再试一次。"


def _render_token(token: dict[str, Any]) -> str:  # noqa: PLR0911, PLR0912
    kind = token.get("type")

    if kind in {"blank_line", "thematic_break"}:
        return ""
    if kind == "text":
        return str(token.get("raw", ""))
    if kind in {"strong", "emphasis", "strikethrough", "paragraph", "heading"}:
        return _render_children(token)
    if kind == "softbreak":
        return " "
    if kind == "linebreak":
        return "\n"
    if kind == "codespan":
        return str(token.get("raw", "")).strip()
    if kind == "block_code":
        return _render_code_block(token)
    if kind == "link":
        return _render_children(token)
    if kind == "image":
        return str(token.get("attrs", {}).get("alt") or "")
    if kind == "list":
        return _join_rendered_children(token)
    if kind == "list_item":
        return _render_children(token)
    if kind in {"block_text", "table_cell", "table_row"}:
        return _render_children(token)
    if kind in {"table", "table_head", "table_body"}:
        return _join_rendered_children(token)
    if "children" in token:
        return _render_children(token)
    return str(token.get("raw") or "")


def _render_children(token: dict[str, Any]) -> str:
    return "".join(_render_token(child) for child in token.get("children", []))


def _join_rendered_children(token: dict[str, Any]) -> str:
    return "；".join(
        part
        for child in token.get("children", [])
        if (part := _render_token(child).strip())
    )


def _render_code_block(token: dict[str, Any]) -> str:
    raw = str(token.get("raw", "")).strip()
    info = str(token.get("attrs", {}).get("info") or "").strip()
    return _render_fenced_block_text(raw, info=info)


def _render_fenced_block_text(raw: str, *, info: str = "") -> str:
    raw = _collapse_block_text(raw)
    if not raw:
        return ""
    if _should_spoken_render_fenced_block(raw, info=info):
        return raw
    return "代码已放到文本记录中。"


def _should_spoken_render_fenced_block(raw: str, *, info: str = "") -> bool:
    if info:
        return False
    if len(raw) > _MAX_SPOKEN_BLOCK_CHARS:
        return False
    if "\n" in raw and raw.count("\n") > _MAX_SPOKEN_BLOCK_NEWLINES:
        return False
    return not _looks_like_code(raw)


def _looks_like_code(text: str) -> bool:
    return bool(_CODE_HINT_RE.search(text) or _CODE_SYMBOL_RE.search(text))


def _looks_like_reasoning_leak(text: str) -> bool:
    return bool(_REASONING_LEAK_RE.search(text) or _REASONING_META_RE.search(text))


def _has_repetition_loop(text: str) -> bool:
    normalized = _WHITESPACE_RE.sub(" ", text.strip().lower())
    if len(normalized) < _MIN_LOOP_TEXT_CHARS:
        return False

    quoted_counts: dict[str, int] = {}
    for phrase in _QUOTED_PHRASE_RE.findall(normalized):
        key = _normalize_loop_phrase(phrase)
        if len(key) < _MIN_REPEATED_PHRASE_CHARS:
            continue
        quoted_counts[key] = quoted_counts.get(key, 0) + 1
        if quoted_counts[key] >= _REPEATED_PHRASE_LIMIT:
            return True

    chunk_counts: dict[str, int] = {}
    for chunk in _SENTENCE_CHUNK_RE.split(normalized):
        key = _normalize_loop_phrase(chunk)
        if not _MIN_REPEATED_CHUNK_CHARS <= len(key) <= _MAX_REPEATED_CHUNK_CHARS:
            continue
        chunk_counts[key] = chunk_counts.get(key, 0) + 1
        if chunk_counts[key] >= _REPEATED_CHUNK_LIMIT:
            return True

    tokens = _LOOP_TOKEN_RE.findall(normalized)
    if len(tokens) < _MIN_LOOP_TOKENS:
        return False
    for width in range(_MIN_LOOP_NGRAM_WIDTH, _MAX_LOOP_NGRAM_WIDTH + 1):
        counts: dict[tuple[str, ...], int] = {}
        for index in range(len(tokens) - width + 1):
            ngram = tuple(tokens[index : index + width])
            counts[ngram] = counts.get(ngram, 0) + 1
            if counts[ngram] >= _REPEATED_NGRAM_LIMIT:
                return True
    return False


def _normalize_loop_phrase(text: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff·]+", "", text, flags=re.UNICODE)
    return text.strip().lower()


def _collapse_block_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r" *\n *", " ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _normalize_text(text: str) -> str:
    text = _URL_RE.sub("", text)
    text = _MARKDOWN_CONTROL_RE.sub("", text)
    text = text.replace("\\", "")
    text = _WHITESPACE_RE.sub(" ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    text = re.sub(r"\s+([，。！？；：、,.!?;:])", r"\1", text)
    text = re.sub(r"([，；：、]){2,}", r"\1", text)
    return text.strip()


def _limit_sentences(text: str, *, max_sentences: int) -> str:
    if max_sentences <= 0:
        return text

    normalized = text.replace("\n", " ").strip()
    if not normalized:
        return ""

    parts = [
        part.strip() for part in _SENTENCE_END_RE.split(normalized) if part.strip()
    ]
    if len(parts) <= max_sentences:
        return normalized
    return "".join(parts[:max_sentences]).strip()


def _fallback_strip(text: str) -> str:
    text = _FENCED_CODE_RE.sub(_fallback_code_replacement, text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


def _fallback_code_replacement(match: re.Match[str]) -> str:
    return _render_fenced_block_text(match.group(2), info=match.group(1).strip())
