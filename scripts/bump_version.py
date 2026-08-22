#!/usr/bin/env python3
"""Bump every llm-gateway version source to the next semver segment.

Canonical sources:
  - pyproject.toml
  - custom_components/llm_gateway/manifest.json
  - uv.lock

The script refuses to run unless all three sources already agree. After a bump
it rewrites all three and verifies them again. It never commits, tags, or
pushes; the release workflow owns Git operations.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

import check_version_sync as sync

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
MANIFEST_PATH = REPO_ROOT / "custom_components" / "llm_gateway" / "manifest.json"
LOCK_PATH = REPO_ROOT / "uv.lock"

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
LOCK_VERSION_RE = re.compile(
    r'(?m)(\[\[package\]\]\nname = "llm-gateway"\nversion = ")\d+\.\d+\.\d+(")'
)


def fail(message: str) -> NoReturn:
    """Print a CI-friendly error and exit non-zero."""
    if "GITHUB_ACTIONS" in os.environ:
        print(f"::error::{message}", file=sys.stderr)
    else:
        print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def current_version() -> str:
    versions = {
        str(PYPROJECT_PATH.relative_to(REPO_ROOT)): sync.read_pyproject_version(),
        str(MANIFEST_PATH.relative_to(REPO_ROOT)): sync.read_manifest_version(),
        str(LOCK_PATH.relative_to(REPO_ROOT)): sync.read_lock_version(),
    }
    unique = sorted(set(versions.values()))
    if len(unique) != 1:
        fail(
            "Version files are out of sync: "
            + ", ".join(f"{path}={versions[path]}" for path in sorted(versions))
            + ". Sync them before bumping."
        )
    return unique[0]


def bump_version(version: str, segment: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    if segment == "major":
        major, minor, patch = major + 1, 0, 0
    elif segment == "minor":
        minor, patch = minor + 1, 0
    elif segment == "patch":
        patch += 1
    else:
        fail(f"Unsupported bump type: {segment}")
    return f"{major}.{minor}.{patch}"


def write_version_file(path: Path, old_version: str, new_version: str) -> None:
    text = path.read_text(encoding="utf-8")

    if path == PYPROJECT_PATH:
        pattern = re.compile(r'(?m)^version = "\d+\.\d+\.\d+"$')
    elif path == MANIFEST_PATH:
        pattern = re.compile(r'"version": "\d+\.\d+\.\d+"')
    elif path == LOCK_PATH:
        pattern = LOCK_VERSION_RE
    else:
        fail(f"Unsupported version file: {path}")

    updated = pattern.sub(
        lambda match: match.group(0).replace(old_version, new_version),
        text,
        count=1,
    )
    if updated == text:
        fail(f"{path.name}: could not find {old_version} to replace")
    path.write_text(updated, encoding="utf-8")


def emit_github_output(version: str, tag: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"version={version}\n")
        handle.write(f"tag={tag}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bump", choices=["major", "minor", "patch"], default="patch")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the next version and tag without writing any files",
    )
    args = parser.parse_args()

    old_version = current_version()
    new_version = bump_version(old_version, args.bump)
    new_tag = f"v{new_version}"

    existing_tags = subprocess.check_output(
        ["git", "tag", "--list", new_tag],
        text=True,
    ).splitlines()
    if existing_tags:
        fail(f"Tag {new_tag} already exists")

    print(f"version: {old_version} -> {new_version}")
    print(f"tag: {new_tag}")

    if args.dry_run:
        return 0

    for path in (PYPROJECT_PATH, MANIFEST_PATH, LOCK_PATH):
        write_version_file(path, old_version, new_version)

    # Verify the rewritten sources before the release workflow commits them.
    versions = {
        str(PYPROJECT_PATH.relative_to(REPO_ROOT)): sync.read_pyproject_version(),
        str(MANIFEST_PATH.relative_to(REPO_ROOT)): sync.read_manifest_version(),
        str(LOCK_PATH.relative_to(REPO_ROOT)): sync.read_lock_version(),
    }
    if any(version != new_version for version in versions.values()):
        fail(f"Post-bump verification failed: {versions}")

    emit_github_output(new_version, new_tag)
    print(f"version-sync ok: {new_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
