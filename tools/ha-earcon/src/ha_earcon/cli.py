"""Command line interface for HA Earcon."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import typer
import yaml
from rich.console import Console
from rich.table import Table

from .loudness import limit_peak, measure_lufs, normalize_lufs, peak_dbfs
from .manifest import write_manifest
from .synth import render_earcon

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def render(
    pack: Path = typer.Argument(..., exists=True, dir_okay=False),
    out: Path = typer.Option(..., "--out", "-o"),
) -> None:
    """Render all earcons from a YAML pack."""
    data = _load_pack(pack)
    sample_rate = int(data.get("sample_rate", 16000))
    target_lufs = float(data.get("target_lufs", -24.0))
    true_peak_dbfs = float(data.get("true_peak_dbfs", -3.0))
    out.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "pack": data.get("name") or pack.stem,
        "sample_rate": sample_rate,
        "target_lufs": target_lufs,
        "true_peak_dbfs": true_peak_dbfs,
        "files": {},
    }

    for name, spec in data["earcons"].items():
        audio = render_earcon(spec, sample_rate)
        audio = normalize_lufs(audio, sample_rate, target_lufs)
        audio = limit_peak(audio, true_peak_dbfs)

        path = out / f"{name}.wav"
        sf.write(path, audio, sample_rate, subtype="PCM_16")

        duration_ms = round(len(audio) / sample_rate * 1000, 1)
        loudness = round(measure_lufs(audio, sample_rate), 1)
        peak = round(peak_dbfs(audio), 1)
        manifest["files"][name] = {
            "path": path.name,
            "purpose": spec.get("purpose", ""),
            "duration_ms": duration_ms,
            "lufs": loudness,
            "peak_dbfs": peak,
        }
        console.print(
            f"[green]rendered[/green] {path} "
            f"({duration_ms:.1f} ms, {loudness:.1f} LUFS, {peak:.1f} dBFS)"
        )

    write_manifest(out / "manifest.json", manifest)


@app.command()
def lint(
    files: list[Path] = typer.Argument(..., exists=True, dir_okay=False),
    max_duration_ms: float = typer.Option(420.0, "--max-duration-ms"),
    target_lufs: float = typer.Option(-24.0, "--target-lufs"),
    lufs_tolerance: float = typer.Option(3.0, "--lufs-tolerance"),
    max_peak_dbfs: float = typer.Option(-3.0, "--max-peak-dbfs"),
) -> None:
    """Check duration, peak, and short-clip loudness."""
    failed = False
    table = Table("file", "duration", "lufs", "peak", "status")
    for path in files:
        audio, sample_rate = sf.read(path, dtype="float32")
        mono = _mono(audio)
        duration_ms = len(mono) / sample_rate * 1000
        loudness = measure_lufs(mono, sample_rate)
        peak = peak_dbfs(mono)
        problems: list[str] = []

        if duration_ms > max_duration_ms:
            problems.append("too long")
        if peak > max_peak_dbfs:
            problems.append("peak high")
        if abs(loudness - target_lufs) > lufs_tolerance:
            problems.append("loudness off")

        status = "OK" if not problems else ", ".join(problems)
        failed = failed or bool(problems)
        table.add_row(
            path.name,
            f"{duration_ms:.1f} ms",
            f"{loudness:.1f}",
            f"{peak:.1f}",
            status,
        )

    console.print(table)
    if failed:
        raise typer.Exit(1)


@app.command()
def inspect(path: Path = typer.Argument(..., exists=True, dir_okay=False)) -> None:
    """Print audio metadata and loudness for one file."""
    info = sf.info(path)
    audio, sample_rate = sf.read(path, dtype="float32")
    table = Table("field", "value")
    table.add_row("path", str(path))
    table.add_row("sample_rate", str(info.samplerate))
    table.add_row("channels", str(info.channels))
    table.add_row("duration_ms", f"{info.duration * 1000:.1f}")
    table.add_row("format", info.format)
    table.add_row("subtype", info.subtype)
    table.add_row("lufs", f"{measure_lufs(_mono(audio), sample_rate):.1f}")
    table.add_row("peak_dbfs", f"{peak_dbfs(_mono(audio)):.1f}")
    console.print(table)


@app.command()
def play(path: Path = typer.Argument(..., exists=True, dir_okay=False)) -> None:
    """Play one WAV file on the local audio device."""
    try:
        import sounddevice as sd
    except ImportError as err:
        raise typer.BadParameter(
            "Install the play extra first: uv sync --extra play"
        ) from err

    audio, sample_rate = sf.read(path, dtype="float32")
    sd.play(audio, sample_rate)
    sd.wait()


def _load_pack(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise typer.BadParameter("Pack YAML must be an object")
    if not isinstance(data.get("earcons"), dict):
        raise typer.BadParameter("Pack YAML must define an earcons object")
    return data


def _mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio.astype(np.float32)
    return audio.mean(axis=1).astype(np.float32)
