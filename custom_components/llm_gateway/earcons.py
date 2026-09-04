"""Canonical access to the bundled voice feedback pack."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

EARCON_PACK = "ha_voice_minimal_v0"
EARCON_MANIFEST = (
    Path(__file__).parent / "frontend" / "earcons" / EARCON_PACK / "manifest.json"
)


@cache
def earcon_manifest() -> dict[str, Any]:
    """Load and validate the generated earcon manifest once."""
    try:
        data = json.loads(EARCON_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"pack": EARCON_PACK, "files": {}}
    if not isinstance(data, dict):
        return {"pack": EARCON_PACK, "files": {}}
    files = data.get("files")
    return {
        **data,
        "pack": str(data.get("pack") or EARCON_PACK),
        "files": files if isinstance(files, dict) else {},
    }


def earcon_library() -> dict[str, dict[str, Any]]:
    """Return valid named earcon specifications from the bundled manifest."""
    return {
        str(name): dict(spec)
        for name, spec in earcon_manifest()["files"].items()
        if isinstance(spec, dict)
    }
