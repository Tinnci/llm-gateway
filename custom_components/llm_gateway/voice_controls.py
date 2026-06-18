"""Deterministic local controls for the voice assistant runtime."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

DEFAULT_PAUSE_SECONDS = 30 * 60
MAX_PAUSE_SECONDS = 24 * 60 * 60
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
UNCONFIGURED_SPEECH = "语音暂停功能还没有配置好。"

VoiceControlAction = Literal["pause", "resume"]

_DURATION_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?|半|[一二两三四五六七八九十]+)\s*(?:个)?\s*"
    r"(?P<unit>秒|分钟|分|小时|钟头)"
)

_PAUSE_PHRASES = (
    "闭嘴",
    "别说话",
    "不要说话",
    "安静一下",
    "暂停语音",
    "暂停唤醒",
    "停止响应",
    "停止唤醒",
    "关闭语音识别",
    "关闭语音唤醒",
    "不要响应语音",
    "别听了",
    "休息一下",
)

_RESUME_PHRASES = (
    "恢复语音",
    "恢复唤醒",
    "恢复响应",
    "继续响应",
    "打开语音识别",
    "开启语音识别",
    "打开语音唤醒",
    "开启语音唤醒",
)

_CHINESE_DIGITS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


@dataclass(frozen=True, slots=True)
class VoiceRuntimeCommand:
    """A local voice assistant runtime control command."""

    action: VoiceControlAction
    seconds: int
    speech: str


def parse_voice_runtime_command(text: str) -> VoiceRuntimeCommand | None:
    """Parse explicit commands that pause or resume voice wake handling."""
    normalized = _normalize(text)
    if not normalized:
        return None

    if any(phrase in normalized for phrase in _RESUME_PHRASES):
        return VoiceRuntimeCommand("resume", 0, "语音唤醒已恢复。")

    if not _is_pause_command(normalized):
        return None

    seconds = _parse_duration_seconds(normalized)
    return VoiceRuntimeCommand(
        "pause",
        seconds,
        f"我会停止响应语音唤醒 {_format_duration(seconds)}。",
    )


async def async_handle_voice_runtime_command(
    hass: HomeAssistant, text: str
) -> str | None:
    """Execute a parsed runtime control command and return spoken feedback."""
    command = parse_voice_runtime_command(text)
    if command is None:
        return None

    handled = (
        await _async_call_pause_service(hass, command)
        if command.action == "pause"
        else await _async_call_resume_service(hass)
    )
    if handled:
        return command.speech
    return UNCONFIGURED_SPEECH


async def _async_call_pause_service(
    hass: HomeAssistant, command: VoiceRuntimeCommand
) -> bool:
    if hass.services.has_service("rest_command", "kukui_voice_pause"):
        await hass.services.async_call(
            "rest_command",
            "kukui_voice_pause",
            {"seconds": command.seconds, "reason": "voice_command"},
            blocking=True,
        )
        return True
    if hass.services.has_service("script", "kukui_voice_pause"):
        await hass.services.async_call(
            "script",
            "kukui_voice_pause",
            {
                "minutes": max(1, round(command.seconds / SECONDS_PER_MINUTE)),
                "reason": "voice_command",
            },
            blocking=True,
        )
        return True
    return False


async def _async_call_resume_service(hass: HomeAssistant) -> bool:
    if hass.services.has_service("rest_command", "kukui_voice_resume"):
        await hass.services.async_call(
            "rest_command", "kukui_voice_resume", {}, blocking=True
        )
        return True
    if hass.services.has_service("script", "kukui_voice_resume"):
        await hass.services.async_call(
            "script", "kukui_voice_resume", {}, blocking=True
        )
        return True
    return False


def _normalize(text: str) -> str:
    return re.sub(r"[\s，。！？,.!?、]", "", text.strip().lower())


def _is_pause_command(normalized: str) -> bool:
    if any(phrase in normalized for phrase in _PAUSE_PHRASES):
        return True
    return "静音" in normalized and any(
        scope in normalized for scope in ("语音", "助手", "你")
    )


def _parse_duration_seconds(normalized: str) -> int:
    match = _DURATION_RE.search(normalized)
    if not match:
        return DEFAULT_PAUSE_SECONDS

    value = _parse_number(match.group("value"))
    unit = match.group("unit")
    if unit == "秒":
        seconds = round(value)
    elif unit in {"小时", "钟头"}:
        seconds = round(value * SECONDS_PER_HOUR)
    else:
        seconds = round(value * SECONDS_PER_MINUTE)
    return min(max(1, seconds), MAX_PAUSE_SECONDS)


def _parse_number(value: str) -> float:
    if value == "半":
        return 0.5
    try:
        return float(value)
    except ValueError:
        pass

    if value == "十":
        return 10
    if "十" in value:
        left, _, right = value.partition("十")
        tens = _CHINESE_DIGITS.get(left, 1) if left else 1
        ones = _CHINESE_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    return float(_CHINESE_DIGITS.get(value, 0) or 0)


def _format_duration(seconds: int) -> str:
    if seconds >= SECONDS_PER_HOUR:
        hours = seconds // SECONDS_PER_HOUR
        minutes = (seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
        return f"{hours} 小时 {minutes} 分钟" if minutes else f"{hours} 小时"
    if seconds >= SECONDS_PER_MINUTE:
        return f"{max(1, round(seconds / SECONDS_PER_MINUTE))} 分钟"
    return f"{seconds} 秒"
