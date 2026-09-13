"""Offline dynamics processing for the tablet's short, deterministic earcons."""

from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import maximum_filter1d
from scipy.signal import butter, resample_poly, sosfilt

from .loudness import peak_dbfs, rms_dbfs

SOFT_KNEE_DB = 6.0
COMPRESSION_RATIO = 3.0
MIN_CREST_DB = 6.0


def crest_factor_db(audio: np.ndarray) -> float:
    return peak_dbfs(audio) - rms_dbfs(audio) if np.any(audio) else 0.0


def compress(audio: np.ndarray, sample_rate: int, threshold_db: float) -> np.ndarray:
    """Use a 6 dB soft knee and 3:1 ratio, with 2 ms attack and 35 ms release."""
    window = max(1, min(len(audio), round(sample_rate * 0.003)))
    envelope = np.sqrt(np.convolve(audio**2, np.ones(window) / window, mode="same"))
    level = 20 * np.log10(np.maximum(envelope, 1e-12))
    above = level - threshold_db
    half_knee = SOFT_KNEE_DB / 2
    reduction = np.where(
        above < -half_knee,
        0,
        np.where(
            above > half_knee, above, (above + half_knee) ** 2 / (2 * SOFT_KNEE_DB)
        ),
    ) * (1 - 1 / COMPRESSION_RATIO)
    target = 10 ** (-reduction / 20)
    gain = 1.0
    attack, release = (
        math.exp(-1 / (sample_rate * 0.002)),
        math.exp(-1 / (sample_rate * 0.035)),
    )
    output = np.empty_like(audio)
    for index, desired in enumerate(target):
        coefficient = attack if desired < gain else release
        gain = coefficient * gain + (1 - coefficient) * desired
        output[index] = audio[index] * gain
    return output


def master_earcon(
    audio: np.ndarray, sample_rate: int, *, peak: float = -1.0
) -> np.ndarray:
    """High-pass, compress, and limit without extending the audible cue latency."""
    audio = np.asarray(audio, dtype=np.float64)
    if audio.ndim != 1 or not np.isfinite(audio).all():
        raise ValueError("earcons must contain finite mono samples")
    if not len(audio) or not np.any(audio):
        return audio.astype(np.float32)
    filtered = sosfilt(
        butter(2, 120, btype="highpass", fs=sample_rate, output="sos"), audio
    )
    filtered /= max(float(np.max(np.abs(filtered))), 1e-12)
    candidates = [
        filtered,
        *(
            compress(filtered, sample_rate, threshold)
            for threshold in (-8, -12, -18, -24, -30)
        ),
    ]
    chosen = min(candidates, key=lambda item: abs(crest_factor_db(item) - 7.5))
    # Very flat tones need a gentle phrase envelope, not added transient peaks.
    if crest_factor_db(chosen) < MIN_CREST_DB:
        envelope = np.sin(np.linspace(0, np.pi, len(chosen))) ** 2
        candidates = [
            chosen * ((1 - amount) + amount * envelope)
            for amount in np.linspace(0, 1, 21)
        ]
        chosen = min(candidates, key=lambda item: abs(crest_factor_db(item) - 7.0))
    # A future peak window prevents one sample from overshooting a short attack.
    lookahead = max(1, round(sample_rate * 0.002))
    future_peak = maximum_filter1d(
        np.abs(chosen), size=lookahead * 2 + 1, mode="constant", origin=-lookahead
    )
    ceiling = 10 ** (-1 / 20)
    chosen = chosen * np.minimum(1, ceiling / np.maximum(future_peak, 1e-12))
    measured_peak = max(float(np.max(np.abs(resample_poly(chosen, 4, 1)))), 1e-12)
    return (chosen * (10 ** (peak / 20) / measured_peak)).astype(np.float32)
