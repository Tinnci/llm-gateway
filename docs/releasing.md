# Releasing LLM Gateway / 发布

## Version sources

The Phase 9 deployment uses **0.3.52**, including the four-panel redesign,
streaming previews and the satellite's 22050 Hz PCM preview format. Its
versioned asset path replaces the previously deployed browser modules.
A Git push and household deployment do not publish a
HACS release; use the automatic workflow below to publish an archive.

| File | Version field |
|---|---|
| `pyproject.toml` | `[project] version` |
| `custom_components/llm_gateway/manifest.json` | `"version"` |
| `uv.lock` | root `llm-gateway` package version |

`panel.py` reads the installed manifest for the browser cache version.

## Automatic release

1. Review and merge the change to `main`.
2. Run **Release** from `main`, choosing `minor` for 0.4.0.
3. The reusable Validate workflow runs backend, earcon-tool and Bun tests,
   Ruff, tsgo, frontend builds, Hassfest, HACS and stable/beta HA setup checks.
4. The release job checks version sync, bumps all three files, checks the new
   version and lockfile, and rebuilds frontend modules using Bun.
5. It builds `llm_gateway.zip`, then pushes the release commit and tag atomically
   and publishes the archive with generated notes.

A direct `vX.Y.Z` tag also runs verification before packaging. Failed verification
cannot publish a tag through the automatic bump path. The release job checks out
the same event commit that Validate tested, even if `main` moves during the run.

The ZIP contains the component contents directly, with `manifest.json` at its
root. `hacs.json` selects `llm_gateway.zip`. Bytecode and Finder metadata are
excluded, including at the component root. An archive test executes the actual
workflow command and verifies the extracted layout.

## Local checks

```sh
uv sync --locked --group dev
uv run python scripts/check_version_sync.py
uv run python scripts/bump_version.py --bump minor --dry-run
uv lock --check
uv run pytest
uv run ruff check custom_components tests tools/ha-earcon/src tools/ha-earcon/tests scripts
bun install --frozen-lockfile
bun test
bun run typecheck
bun run build:panel
```

The version verifier is also used by pre-commit and CI. It reads real TOML/JSON
values; changes to dependencies or metadata do not count as version changes.

## HACS and brands / HACS 与品牌

Hassfest is required again: the official image now discovers only integration
manifests, so the old workaround deleting earcon manifests is removed.
The release archive retains those audio-pack manifests.

Local PNG assets under `brand/` are rendered from the repository's own
`icon.svg`; they depict a conversation routed through a gateway and use no
Home Assistant or model-vendor trademark. The normal HACS brands check is enabled.

The existing PolyForm Noncommercial license remains in effect. GitHub reports it
as `NOASSERTION`; custom-repository HACS validation omits only the default-index
license eligibility check. Passing these checks does not claim eligibility for
the default HACS catalogue.

Phase 9 的源码、构建与家庭部署验证见
[实机验证记录](voice-harness-phase9-2026-09-13.md)。后续正式发版仍走 Release workflow。
发版不会把工具派发或语音合成结果当成物理设备确认或实际播报完成。
