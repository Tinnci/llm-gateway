# Releasing LLM Gateway

## Version sources

Every release version lives in exactly three files and must always agree:

| File | Version field |
|---|---|
| `pyproject.toml` | `[project] version` |
| `custom_components/llm_gateway/manifest.json` | `"version"` |
| `uv.lock` | `[[package]] name = "llm-gateway"` / `version` |

`panel.py` reads `manifest.json` at runtime, so the browser cache key
(`voice-harness-panel.js?v=...`) follows the integration version
automatically.

## Automatic release flow

1. Merge the code change to `main` and let the `Validate` workflow pass.
2. Go to **Actions → Release → Run workflow**.
3. Choose the branch `main` and the bump segment:
   - `patch`: `0.3.31` → `0.3.32`
   - `minor`: `0.3.31` → `0.4.0`
   - `major`: `0.3.31` → `1.0.0`
4. GitHub Actions:
   - verifies all three version sources are synchronized;
   - runs `scripts/bump_version.py` to bump all three files;
   - verifies the bumped files again;
   - commits `Release vX.Y.Z` and pushes the tag `vX.Y.Z` to `main`;
   - builds `llm_gateway.zip` and publishes the GitHub release.

Pushing a `vX.Y.Z` tag directly also triggers the release zip build after the
same version/tag consistency check.

## How version mistakes are prevented

- `scripts/check_version_sync.py` is the single verifier. It reads the three
  sources with real parsers (`tomllib`/`json`) and fails when they differ or
  are not `X.Y.Z`.
- `scripts/bump_version.py` refuses to bump unless all three sources already
  agree, rewrites all three together, and verifies them again. It never
  commits by itself; the release workflow owns Git operations.
- `.pre-commit-config.yaml` runs the verifier whenever `pyproject.toml`,
  `manifest.json`, or `uv.lock` is staged.
- The `Validate` workflow has:
  - `version-source-guard`: when version files changed on push/pull_request,
    runs the verifier and rejects the change if they are not synchronized;
  - `version-sync-check`: runs the verifier on every push, PR, and tag;
  - `uv lock --check`: ensures `uv.lock` matches `pyproject.toml`.
- The `Release` workflow verifies version sync before bumping, after bumping,
  and again against the release tag before publishing.

## Recovering from a mismatch

```sh
python3 scripts/check_version_sync.py
python3 scripts/bump_version.py --bump patch --dry-run
```

Then either run the Release workflow, or if you are intentionally doing local
development, make the three files match before pushing.
