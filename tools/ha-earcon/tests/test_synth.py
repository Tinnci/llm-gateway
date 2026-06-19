"""Tests for ha-earcon synthesis."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import numpy as np
from ha_earcon.cli import app
from ha_earcon.loudness import (
    limit_peak,
    measure_lufs,
    normalize_lufs,
    peak_dbfs,
)
from ha_earcon.synth import render_earcon
from typer.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

EXPECTED_SAMPLES = 1920
TARGET_LUFS = -24.0
PEAK_CEILING = -12.0
TOLERANCE = 0.2
REQUIRED_EARCONS = {
    "wake",
    "captured",
    "thinking",
    "search",
    "confirmation",
    "success",
    "failure",
    "cancel",
}


def test_render_tone_sequence_duration_and_peak() -> None:
    audio = render_earcon(
        {
            "type": "tone_sequence",
            "peak": 0.2,
            "tones": [
                {"freq": 440, "ms": 50},
                {"silence_ms": 20},
                {"freq": 660, "ms": 50},
            ],
            "envelope": {"attack_ms": 2, "release_ms": 8},
        },
        16000,
    )

    assert len(audio) == EXPECTED_SAMPLES
    assert audio.dtype == np.float32
    assert np.max(np.abs(audio)) <= 0.2001


def test_loudness_normalize_and_peak_limit() -> None:
    audio = render_earcon(
        {
            "type": "tone_sequence",
            "tones": [{"freq": 880, "ms": 140}],
            "envelope": {"attack_ms": 5, "release_ms": 20},
        },
        16000,
    )

    normalized = normalize_lufs(audio, 16000, TARGET_LUFS)
    limited = limit_peak(normalized, PEAK_CEILING)

    assert abs(measure_lufs(normalized, 16000) - TARGET_LUFS) < TOLERANCE
    assert peak_dbfs(limited) <= PEAK_CEILING


def test_render_cli_writes_policy_manifest(tmp_path: Path) -> None:
    runner = CliRunner()
    pack = "packs/ha_voice_minimal_v0.yaml"
    out = tmp_path / "earcons"

    result = runner.invoke(app, ["render", pack, "--out", str(out)])

    assert result.exit_code == 0
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    files = manifest["files"]
    assert REQUIRED_EARCONS.issubset(files)
    for name in REQUIRED_EARCONS:
        item = files[name]
        assert item["name"] == name
        assert item["semantic_state"]
        assert isinstance(item["priority"], int)
        assert isinstance(item["can_play_while_listening"], bool)
        assert item["quiet_hours_behavior"]
        assert item["trace_event_name"].startswith("earcon_")
        assert (out / item["path"]).exists()
