"""Verify version consistency and the actual release archive layout."""

import json
import os
import shutil
import subprocess
import tomllib
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_release_versions_are_synchronized() -> None:
    manifest = json.loads(
        (ROOT / "custom_components/llm_gateway/manifest.json").read_text()
    )
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    package = next(item for item in lock["package"] if item["name"] == "llm-gateway")

    assert manifest["version"] == project["project"]["version"] == package["version"]


def test_release_zip_installs_component_and_omits_bytecode(tmp_path: Path) -> None:
    component = tmp_path / "custom_components/llm_gateway"
    shutil.copytree(ROOT / "custom_components/llm_gateway", component)
    cache = component / "__pycache__"
    cache.mkdir(exist_ok=True)
    (cache / "release_probe.pyc").write_bytes(b"local bytecode")
    (component / ".DS_Store").write_bytes(b"local metadata")
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yaml").read_text())
    step = next(
        step
        for step in workflow["jobs"]["release-zip"]["steps"]
        if step.get("name") == "Build HACS component zip"
    )

    # Run the repository-owned archive step in an isolated installation tree.
    subprocess.run(  # noqa: S603
        ["/bin/bash", "-e", "-c", step["run"]],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_WORKSPACE": str(tmp_path)},
        check=True,
        capture_output=True,
        text=True,
    )

    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert hacs["zip_release"] is True
    with zipfile.ZipFile(tmp_path / hacs["filename"]) as archive:
        names = archive.namelist()
        assert json.loads(archive.read("manifest.json"))["domain"] == "llm_gateway"
        assert {
            "__init__.py",
            "translations/en.json",
            "translations/zh-Hans.json",
            "brand/icon.png",
        } <= set(names)
        assert all(not name.startswith("custom_components/") for name in names)
        assert all(
            "__pycache__" not in name and not name.endswith((".pyc", ".DS_Store"))
            for name in names
        )
