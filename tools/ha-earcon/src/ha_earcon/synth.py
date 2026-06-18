"""Small deterministic earcon synthesizer."""

from __future__ import annotations

from collections.abc import Iterable
from math import pi
from typing import Any

import numpy as np

Array = np.ndarray


def silence(sample_rate: int, ms: float) -> Array:
    """Return a silent mono buffer."""
    return np.zeros(_samples(sample_rate, ms), dtype=np.float32)


def sine(
    sample_rate: int,
    freq: float,
    ms: float,
    *,
    amp: float = 0.22,
    harmonics: Iterable[tuple[float, float]] = (),
) -> Array:
    """Return a sine tone with optional quiet harmonics."""
    n = _samples(sample_rate, ms)
    if n == 0:
        return np.zeros(0, dtype=np.float32)

    t = np.arange(n, dtype=np.float32) / sample_rate
    wave = np.sin(2 * pi * freq * t)
    for multiple, gain in harmonics:
        wave += gain * np.sin(2 * pi * freq * multiple * t)
    return (amp * wave).astype(np.float32)


def chirp(
    sample_rate: int,
    start_freq: float,
    end_freq: float,
    ms: float,
    *,
    amp: float = 0.20,
) -> Array:
    """Return a linear frequency chirp."""
    n = _samples(sample_rate, ms)
    if n == 0:
        return np.zeros(0, dtype=np.float32)

    t = np.arange(n, dtype=np.float32) / sample_rate
    duration_s = max(ms / 1000, 0.001)
    slope = (end_freq - start_freq) / duration_s
    phase = 2 * pi * (start_freq * t + 0.5 * slope * t * t)
    return (amp * np.sin(phase)).astype(np.float32)


def apply_envelope(
    x: Array,
    sample_rate: int,
    *,
    attack_ms: float = 6,
    release_ms: float = 24,
) -> Array:
    """Apply a simple attack/release envelope."""
    y = x.astype(np.float32, copy=True)
    attack = min(len(y), _samples(sample_rate, attack_ms))
    release = min(len(y), _samples(sample_rate, release_ms))

    if attack > 0:
        y[:attack] *= np.linspace(0, 1, attack, dtype=np.float32)
    if release > 0:
        y[-release:] *= np.linspace(1, 0, release, dtype=np.float32)
    return y


def render_earcon(spec: dict[str, Any], sample_rate: int) -> Array:
    """Render one earcon spec to mono float32 audio."""
    if spec.get("type") != "tone_sequence":
        raise ValueError(f"Unsupported earcon type: {spec.get('type')}")

    env = spec.get("envelope") or {}
    harmonics = _harmonics(spec.get("harmonics") or [])
    chunks: list[Array] = []

    for item in spec.get("tones") or []:
        if "silence_ms" in item:
            chunks.append(silence(sample_rate, float(item["silence_ms"])))
            continue
        if "start_freq" in item and "end_freq" in item:
            tone = chirp(
                sample_rate,
                float(item["start_freq"]),
                float(item["end_freq"]),
                float(item["ms"]),
                amp=float(item.get("amp", spec.get("amp", 0.20))),
            )
        else:
            tone = sine(
                sample_rate,
                float(item["freq"]),
                float(item["ms"]),
                amp=float(item.get("amp", spec.get("amp", 0.22))),
                harmonics=harmonics,
            )
        chunks.append(
            apply_envelope(
                tone,
                sample_rate,
                attack_ms=float(env.get("attack_ms", 6)),
                release_ms=float(env.get("release_ms", 24)),
            )
        )

    if not chunks:
        return np.zeros(0, dtype=np.float32)

    out = np.concatenate(chunks).astype(np.float32)
    peak = float(np.max(np.abs(out))) if len(out) else 0.0
    if peak > 0:
        out = out / peak * float(spec.get("peak", 0.25))
    return out.astype(np.float32)


def _samples(sample_rate: int, ms: float) -> int:
    return max(0, round(sample_rate * ms / 1000))


def _harmonics(raw: list[dict[str, Any]]) -> list[tuple[float, float]]:
    return [
        (float(item.get("multiple", 1)), float(item.get("gain", 0)))
        for item in raw
        if isinstance(item, dict)
    ]
