#!/usr/bin/env python3
"""Check that every llm-gateway version source is synchronized.

Version sources:
  - pyproject.toml:            [project] version
  - custom_components/llm_gateway/manifest.json: version
  - uv.lock:                   [[package]] name = "llm-gateway" version

Exit 0 when all sources agree. Exit 1 with a readable repair hint otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import NoReturn

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
MANIFEST_PATH = REPO_ROOT / "custom_components" / "llm_gateway" / "manifest.json"
LOCK_PATH = REPO_ROOT / "uv.lock"
LOCK_PACKAGE_NAME = "llm-gateway"

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _github_actions() -> bool:
    return "GITHUB_ACTIONS" in os.environ


def fail(message: str) -> NoReturn:
    """Print an error and exit non-zero."""
    if _github_actions():
        print(f"::error::{message}", file=sys.stderr)
    else:
        print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def read_pyproject_version(path: Path = PYPROJECT_PATH) -> str:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        fail(f"{path.name}: [project] version must be a string like X.Y.Z")
    return version


def read_manifest_version(path: Path = MANIFEST_PATH) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        fail(f"{path.name}: version must be a string like X.Y.Z")
    return version


def read_lock_version(path: Path = LOCK_PATH) -> str:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    packages = data.get("package")
    if not isinstance(packages, list):
        fail(f"{path.name}: [[package]] table is missing")
    for package in packages:
        if package.get("name") == LOCK_PACKAGE_NAME:
            version = package.get("version")
            if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
                fail(f"{path.name}: {LOCK_PACKAGE_NAME} version must be X.Y.Z")
            return version
    fail(f"{path.name}: {LOCK_PACKAGE_NAME} package not found in lockfile")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-tag",
        metavar="TAG",
        help="also require every source to match this tag after stripping a leading v",
    )
    args = parser.parse_args()

    versions = {
        str(PYPROJECT_PATH.relative_to(REPO_ROOT)): read_pyproject_version(),
        str(MANIFEST_PATH.relative_to(REPO_ROOT)): read_manifest_version(),
        str(LOCK_PATH.relative_to(REPO_ROOT)): read_lock_version(),
    }

    unique = sorted(set(versions.values()))
    if len(unique) != 1:
        fail(
            "Version files are out of sync: "
            + ", ".join(f"{path}={versions[path]}" for path in sorted(versions))
            + ". Run the release workflow or scripts/bump_version.py to fix them."
        )

    current = unique[0]
    if args.with_tag:
        tag = args.with_tag.removeprefix("v")
        if tag != current:
            fail(f"Tag {args.with_tag} does not match synchronized version {current}")

    print(f"version-sync ok: {current}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
