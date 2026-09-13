"""Measure encoded assets and reject transient overshoot or lost silence."""

import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from ha_earcon.cli import app
from ha_earcon.loudness import peak_dbfs
from ha_earcon.mastering import crest_factor_db, master_earcon
from scipy.signal import resample_poly
from typer.testing import CliRunner


def test_all_pack_assets_meet_tablet_dynamics(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app, ["render", "packs/ha_voice_minimal_v0.yaml", "--out", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["mastering"] == "tablet"
    assert manifest["target_lufs"] is None
    assert "follow_up" in manifest["files"]
    for name, entry in manifest["files"].items():
        audio, _ = sf.read(tmp_path / entry["path"])
        assert 6 <= crest_factor_db(audio) <= 9, (name, crest_factor_db(audio))
        assert -1.3 <= peak_dbfs(audio) <= -0.99, name
        assert peak_dbfs(resample_poly(audio, 4, 1)) <= -0.99, name
        assert entry["highpass_hz"] == 120
        assert abs(crest_factor_db(audio) - entry["crest_factor_db"]) < 0.05


def test_silent_and_invalid_samples() -> None:
    assert not np.any(master_earcon(np.zeros(1600), 16000))
    with pytest.raises(ValueError, match="finite mono samples"):
        master_earcon(np.array([np.nan]), 16000)


def test_highpass_rejects_subsonic_energy() -> None:
    time = np.arange(16000) / 16000
    mixed = np.sin(2 * np.pi * 35 * time) + np.sin(2 * np.pi * 700 * time)
    mastered = master_earcon(mixed, 16000)
    spectrum = np.abs(np.fft.rfft(mastered))
    assert spectrum[35] < spectrum[700] * 0.13


def test_short_audio_does_not_extend_compression_window() -> None:
    audio = np.array([0.1, -0.1], dtype=np.float32)
    mastered = master_earcon(audio, 16000)
    assert mastered.shape == audio.shape
    assert np.isfinite(mastered).all()
