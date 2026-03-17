# Feature Plan

## GitHub release workflow

- Date: 2026-03-16
- Status: Implemented
- Title: Add tag-triggered GitHub Release workflow with multi-platform binary archives
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: CI / distribution / release management
- Modules:
  - `.github/workflows/release.yml`
  - `.github/workflows/snapshot.yml`
  - `Makefile`
  - `scripts/dist_tools_lib.py`
  - `scripts/gen_dist_tools.py`
- Test modules:
  - `tests/test_make_dist_workflow.py`
  - `compiler/stage2_l0/tests/l0c_stage2_install_prefix_test.sh`

## Summary

`make install` and `make dist` now produce a relocatable self-hosted Stage 2 compiler archive. This plan adds the CI
infrastructure to publish those archives as GitHub Releases, covering tag-triggered releases, manual-dispatch snapshots,
multi-platform binary matrix, auto-generated release notes, `VERSION` file injection into binary archives, SHA-256
checksums, and bundling of `README.md`, `examples/`, and `docs/reference/` so users have orientation material and a
language reference without going online.

## Goals

1. Pushing a tag matching `v*` triggers a CI workflow that builds `make dist` archives on Linux x86_64, macOS arm64,
   macOS x86_64, and Windows x86_64, then publishes them as a GitHub Release with checksums.
2. A separate manual-dispatch workflow produces the same artifacts but marks the release as a pre-release snapshot.
3. Release notes are auto-generated from the git log since the previous tag.
4. A `VERSION` file is injected into the source tree before `make dist` so each binary distribution archive contains a
   machine-readable version string.
5. Each binary archive embeds CI provenance in `--version` via `DEA_BUILD_ID`.

## Non-Goals

- GPG or sigstore signing (deferred; SHA-256 checksums are the initial integrity mechanism).
- A custom source archive beyond GitHub's auto-generated one.
- Homebrew, APT, or any downstream package-manager integration.
- Changelog maintenance policy beyond the git log.
- Nightly or cron-triggered builds.

## Versioning Scheme

Date-based tags: `v2026-03-16` for daily-granularity releases, `v2026-03-16-1457` (24-hour UTC HH:MM) when multiple
releases occur on the same date. The tag is the single source of truth for the version string.

The `VERSION` file written into the tree before archive creation contains the tag name without the `v` prefix (for
example `2026-03-16` or `2026-03-16-1457`). This file is not committed; it is injected by the workflow and consumed by
`make dist`.

Snapshot builds from the manual-dispatch workflow use the tag `snapshot-<short-hash>-<YYYYMMDD-HHMM>` as the version
string and are marked as pre-release on the GitHub Release.

## Binary Matrix

| Runner           | OS label | Arch   | Archive format | C compiler | Notes                                   |
| ---------------- | -------- | ------ | -------------- | ---------- | --------------------------------------- |
| `ubuntu-latest`  | linux    | x86_64 | tar.gz         | gcc        | Primary Linux target                    |
| `macos-15-intel` | darwin   | x86_64 | tar.gz         | clang      | Intel macOS                             |
| `macos-latest`   | darwin   | arm64  | tar.gz         | clang      | Apple Silicon                           |
| `windows-latest` | windows  | x86_64 | zip            | gcc        | MSYS2/MinGW-w64 via `msys2/setup-msys2` |

`make dist` already encodes `<os>-<arch>` in the archive filename. The workflow collects all four archives plus one
`SHA256SUMS` file and attaches them to the release.

Release archives are built with the platform's system compiler (gcc on Linux/Windows, clang on macOS). The `dist` target
defaults to `L0_CFLAGS=-O2`, so the `l0c-stage2.native` binary is optimized in both local and CI builds. This compiler
and optimization level are used only to produce the compiler binary itself. End users independently choose their own C
compiler (tcc, gcc, clang, etc.) and flags for compiling L0 programs via `--build` and `--run`.

## Archive Contents

Each binary distribution archive unpacks to a `dea-l0/` root with the following layout:

```
dea-l0/
  bin/              l0c launcher, l0c-stage2.native, l0-env.sh
  shared/           stdlib and runtime shared assets
  VERSION           machine-readable version string (injected by CI)
  README.md         top-level project README
  examples/         all bundled .l0 example programs
  docs/
    reference/      normative user-facing language documentation
      architecture.md
      c-backend-design.md
      design-decisions.md
      grammar/
        l0.md
      ownership.md
      project-status.md
      standard-library.md
```

Development plans (`docs/plans/`), specs, proposals, attic docs, and contributor docs are not included.

## Phases

### Phase 1: VERSION file injection and dist optimization default

Add a small pre-dist step that writes a `VERSION` file to the repository root. The file contains a single line: the
version string derived from the tag (or snapshot ID for manual dispatches).

Additionally, make `make dist` default to `L0_CFLAGS=-O2` when the variable is not already set. `dist` is a
release-oriented target; the resulting `l0c-stage2.native` binary should always be optimized. The default is overridable
via explicit `L0_CFLAGS=...` on the command line.

Required changes:

1. The release workflow extracts the version from `GITHUB_REF_NAME` (stripping the `v` prefix) and writes it to
   `VERSION` before calling `make dist`.
2. `make dist` (or `scripts/dist_tools_lib.py`) copies `VERSION` into the distribution tree root if the file exists. No
   change if absent — local `make dist` continues to work without it.
3. The `dist` Makefile target sets `L0_CFLAGS ?= -O2` so that both local and CI dist builds produce optimized binaries
   by default.
4. Document the `VERSION` file convention in `compiler/stage2_l0/README.md`.
5. Extend `tests/test_make_dist_workflow.py` to assert that unpacked distribution archives contain `VERSION` when the
   source tree provides one, and keep `compiler/stage2_l0/tests/l0c_stage2_install_prefix_test.sh` focused on installed
   prefix behavior rather than release packaging.

### Phase 2: Release workflow (`.github/workflows/release.yml`)

Trigger: `on: push: tags: 'v*'`.

```
jobs:
  build-dist:
    strategy:
      fail-fast: false
      matrix:
        include:
          - runner: ubuntu-latest
            os: linux
            arch: x86_64
          - runner: macos-15-intel
            os: darwin
            arch: x86_64
          - runner: macos-latest
            os: darwin
            arch: arm64
          - runner: windows-latest
            os: windows
            arch: x86_64
    runs-on: ${{ matrix.runner }}
    steps:
      - checkout (fetch-depth: 0, for git log)
      - setup MSYS2 via msys2/setup-msys2 (Windows only; align with existing ci.yml)
      - setup Python + make venv
      - inject VERSION from tag
      - make dist with DEA_BUILD_ID=gha-${{ github.run_id }}.${{ github.run_attempt }}-release-${{ matrix.os }}-${{ matrix.arch }}
        (L0_CFLAGS defaults to -O2 via the dist target; CI need not set it explicitly)
      - smoke-test: extract archive, run l0c --version, verify VERSION file present
      - upload-artifact (per-platform archive)

  publish-release:
    needs: build-dist
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - checkout (for git log)
      - download all build artifacts
      - generate SHA256SUMS from all archives
      - generate release notes from git log since previous tag
      - create GitHub Release from tag, attach archives + SHA256SUMS + release notes
```

Key details:

- `DEA_BUILD_ID` follows the existing convention: `gha-<run_id>.<run_attempt>-release-<os>-<arch>`.
- `L0_CFLAGS` defaults to `-O2` in the `dist` target itself, so both local and CI release builds are optimized.
- `fail-fast: false` so a single platform failure doesn't kill the other builds.
- The `publish-release` job uses `gh release create` or `softprops/action-gh-release` to create the release and upload
  assets.
- The release body contains the auto-generated notes (see Phase 4).

### Phase 3: Snapshot workflow (`.github/workflows/snapshot.yml`)

Trigger: `on: workflow_dispatch` with an optional `ref` input (defaults to the default branch HEAD).

Same matrix and steps as the release workflow, except:

- The version string is `snapshot-<short-hash>-<YYYYMMDD-HHMM>` instead of a tag-derived date.
- The GitHub Release is created with `--prerelease`.
- The tag is created by the workflow itself as `snapshot/<version-string>` so the release has a stable ref.

### Phase 4: Release notes generation

The `publish-release` job generates release notes from the git log:

```bash
PREV_TAG=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
if [ -n "$PREV_TAG" ]; then
    git log --pretty=format:"- %s (%h)" "$PREV_TAG"..HEAD > release-notes.md
else
    git log --pretty=format:"- %s (%h)" HEAD > release-notes.md
fi
```

The notes are passed as the release body. For the first release (no previous tag), all history is included — truncated
to a reasonable length if necessary.

A future refinement can add a header with the version, date, and platform matrix summary above the raw log.

### Phase 5: Checksums

After downloading all platform archives, the `publish-release` job generates:

```bash
sha256sum *.tar.gz *.zip > SHA256SUMS
```

`SHA256SUMS` is uploaded as a release asset alongside the archives. The release body includes a note pointing users to
the checksums file.

### Phase 6: Smoke tests

Each matrix job, after `make dist`, extracts the archive into a temporary directory and runs:

```bash
./dea-l0/bin/l0c --version
test -f ./dea-l0/VERSION
```

The smoke test also asserts presence of the bundled extras:

```python
for expected in ["README.md", "examples", "docs/reference"]:
    if not (dist_root / expected).exists():
        raise SystemExit(f"missing expected path in dist: {dist_root / expected}")
```

This catches packaging regressions before the archive reaches the release. On Windows, the smoke test uses `l0c.cmd`.

## Verification

### Tag-triggered release

```bash
git tag v2026-03-16
git push origin v2026-03-16
```

Expected:

1. CI builds archives for all four platforms.
2. Each archive contains `VERSION` with content `2026-03-16`.
3. `l0c --version` inside each archive shows provenance with `build: gha-...-release-<os>-<arch>`.
4. A GitHub Release named `v2026-03-16` appears with four archives, `SHA256SUMS`, and git-log release notes.
5. GitHub's auto-generated source archives remain unchanged; the machine-readable `VERSION` file is only required in the
   binary distribution archives.

### Manual-dispatch snapshot

1. Trigger the snapshot workflow from the Actions tab.
2. Expected: a pre-release GitHub Release with `snapshot-<hash>-<timestamp>` tag, four archives, and `SHA256SUMS`.

### Local dry run

```bash
echo "2026-03-16" > VERSION
make dist
# make dist prints the archive path; extract it into a smoke-test directory:
ARCHIVE="$(ls build/stage2_dist.*/dea-l0-lang_*.tar.gz)"
mkdir -p /tmp/smoke
tar xzf "$ARCHIVE" -C /tmp/smoke
/tmp/smoke/dea-l0/bin/l0c --version
cat /tmp/smoke/dea-l0/VERSION
```

## Open Questions

1. **Intel macOS contingency**: If GitHub removes the hosted Intel macOS runner in the future, the darwin-x86_64 row can
   be dropped or moved to a self-hosted runner.

## Related Documents

- [Windows dev install workflow](2026-03-13-windows-dev-install-and-prefix-workflow.md)
- [Bootstrap plan](closed/2026-03-09-stage2-bootstrap-compiler-artifact-noref.md)
- [Stage 2 contract](../../specs/compiler/stage2-contract.md)
- [CLI contract](../../specs/compiler/cli-contract.md)
- [Project status](../../reference/project-status.md)
