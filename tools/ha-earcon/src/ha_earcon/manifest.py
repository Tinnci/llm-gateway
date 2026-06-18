"""Manifest helpers for rendered earcon packs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_manifest(path: Path, data: dict[str, Any]) -> None:
    """Write a deterministic JSON manifest."""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
