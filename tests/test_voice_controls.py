"""Tests for deterministic voice runtime controls."""

from __future__ import annotations

from custom_components.llm_gateway.voice_controls import (
    DEFAULT_PAUSE_SECONDS,
    parse_voice_runtime_command,
)


def test_parse_pause_command_with_minutes() -> None:
    command = parse_voice_runtime_command("闭嘴 5 分钟")

    assert command is not None
    assert command.action == "pause"
    assert command.seconds == 300
    assert command.speech == "我会停止响应语音唤醒 5 分钟。"


def test_parse_pause_command_with_half_hour() -> None:
    command = parse_voice_runtime_command("语音助手静音半小时")

    assert command is not None
    assert command.action == "pause"
    assert command.seconds == 1800


def test_parse_pause_defaults_to_30_minutes() -> None:
    command = parse_voice_runtime_command("休息一下")

    assert command is not None
    assert command.seconds == DEFAULT_PAUSE_SECONDS


def test_parse_resume_command() -> None:
    command = parse_voice_runtime_command("恢复语音唤醒")

    assert command is not None
    assert command.action == "resume"
    assert command.speech == "语音唤醒已恢复。"


def test_unrelated_mute_command_is_not_intercepted() -> None:
    assert parse_voice_runtime_command("把电视静音") is None
