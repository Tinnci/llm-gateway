"""Loudness helpers for short earcons."""

from __future__ import annotations

import math

import numpy as np
import pyloudnorm as pyln

Array = np.ndarray

_EPS = 1e-12


def peak_dbfs(audio: Array) -> float:
    """Return sample peak in dBFS."""
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak <= 0:
        return -math.inf
    return 20 * math.log10(peak)


def measure_lufs(audio: Array, sample_rate: int) -> float:
    """Return integrated loudness, padding short clips for stable measurement."""
    mono = _mono(audio)
    if len(mono) == 0:
        return -math.inf

    minimum = int(sample_rate * 0.4)
    if len(mono) < minimum:
        mono = np.pad(mono, (0, minimum - len(mono)))

    meter = pyln.Meter(sample_rate, block_size=0.100)
    value = float(meter.integrated_loudness(mono))
    if math.isinf(value) or math.isnan(value):
        return rms_dbfs(audio)
    return value


def rms_dbfs(audio: Array) -> float:
    """Return RMS in dBFS as a fallback for very short or silent clips."""
    mono = _mono(audio)
    if len(mono) == 0:
        return -math.inf
    rms = float(np.sqrt(np.mean(np.square(mono), dtype=np.float64)))
    if rms <= 0:
        return -math.inf
    return 20 * math.log10(max(rms, _EPS))


def normalize_lufs(audio: Array, sample_rate: int, target_lufs: float) -> Array:
    """Scale audio to a target short-clip loudness."""
    current = measure_lufs(audio, sample_rate)
    if math.isinf(current) or math.isnan(current):
        return audio.astype(np.float32)
    gain = 10 ** ((target_lufs - current) / 20)
    return (audio * gain).astype(np.float32)


def limit_peak(audio: Array, true_peak_dbfs: float) -> Array:
    """Scale down audio if sample peak exceeds the configured ceiling."""
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    ceiling = 10 ** (true_peak_dbfs / 20)
    if peak <= ceiling or peak <= 0:
        return audio.astype(np.float32)
    return (audio / peak * ceiling).astype(np.float32)


def _mono(audio: Array) -> Array:
    if audio.ndim == 1:
        return audio.astype(np.float32)
    return audio.mean(axis=1).astype(np.float32)
