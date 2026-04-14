# Tool Plan

## Expand Windows CI and documentation for MSYS2 UCRT64 and MINGW64 developer environments

- Date: 2026-03-31
- Status: Closed (implemented)
- Title: Expand Windows CI and documentation for MSYS2 UCRT64 and MINGW64 developer environments
- Kind: Tooling
- Severity: Medium
- Stage: Shared
- Subsystem: CI / Build workflow / Windows documentation
- Modules:
  - `.github/workflows/l0-ci.yml`
  - `.github/workflows/l0-release.yml`
  - `.github/workflows/l0-snapshot.yml`
  - `README.md`
  - `README-WINDOWS.md`
  - `l0/CLAUDE.md`
  - `l0/docs/user/README.md`
  - `l0/docs/user/README-WINDOWS.md`
  - `l0/docs/reference/project-status.md`
  - `scripts/dea_tooling/launchers.py`
- Test modules:
  - `tests/test_make_dist_workflow.py`
  - `tests/test_make_dea_build_workflow.py`
  - `tests/test_dist_tools_lib_fallback.py`
  - `tests/test_release_tag_policy.py`
- Related:
  - `work/plans/tools/closed/2026-03-11-windows-build-support.md`
  - `work/plans/bug-fixes/closed/2026-03-31-msys2-mingw64-dev-environment-test-failures-noref.md`

## Summary

This plan is closed. Windows CI now validates the recommended MSYS2 `UCRT64` Python path by default, keeps manual
coverage for the alternate `MINGW64` MSYS2 Python path and native Windows Python path, and the related release/snapshot
and Windows documentation updates have landed.

Manual GitHub validation of the implemented workflow changes passed before closure.

Windows CI previously used native Windows Python (installed by `actions/setup-python`) running inside an MSYS2 bash
shell (`shell: msys2 {0}`). A developer working in an MSYS2 `MINGW64` or `UCRT64` shell uses MinGW/UCRT Python instead.
The two Python families differ in observable ways:

| Behavior                         | Native Windows Python        | MinGW Python (MSYS2)          |
| -------------------------------- | ---------------------------- | ----------------------------- |
| `Path.__str__()` separator       | `\` (backslash)              | `/` (forward slash)           |
| `os.name`                        | `"nt"`                       | `"nt"`                        |
| `subprocess.run` of `.cmd` files | Delegates to `cmd.exe`       | Delegates to `cmd.exe`        |
| `platform._syscmd_ver()`         | Calls `ver` via `subprocess` | Calls `ver` via `subprocess`  |
| `uname` availability             | Not available                | Available (MSYS2 provides it) |
| `shutil.which` path style        | Backslash                    | Forward slash                 |
| `TEMP`/`TMP` env presence        | Always set by runner         | Depends on shell inheritance  |

These differences caused a series of test failures on a developer MSYS2 `MINGW64` machine that CI did not catch. The
same behavioral class also applies to `UCRT64`, which has now been validated locally and should become the preferred
Windows developer and CI environment because it tracks the newer MSYS2-recommended UCRT toolchain.

1. `test_dist_tools_lib_fallback`: patching `subprocess.run` intercepted `platform._syscmd_ver()` calling `ver` — only
   observable when `os.name == "nt"` and `uname` is also available.
2. `test_make_dea_build_workflow`: `.cmd` wrapper outputs backslash paths, but MinGW `Path.__str__()` produces forward
   slashes — assertion mismatches on `L0_HOME` and `PATH` dedup checks.
3. `test_make_dist_workflow`: `clean_env()` stripped `TEMP`/`TMP`, causing GCC to fall back to `C:\WINDOWS\` for temp
   files — only fails when these variables are not implicitly inherited.
4. Stage 2 `#line` directive path normalization and `--run` temp exe cleanup — both Windows-specific.

All four were fixed locally but none would have been caught by the current CI configuration. The current docs also
overstate `MINGW64` as the only validated MSYS2 option even though `UCRT64` now works as a first-class developer
environment.

## Goal

1. Document both MSYS2 `UCRT64` and `MINGW64` as supported Windows developer environments.
2. Make `UCRT64` the default and recommended MSYS2 environment for future-facing Windows validation.
3. Expand the Windows CI matrix to cover:
   - automatic `UCRT64` + MSYS2 Python validation on push / pull_request,
   - manual `MINGW64` + MSYS2 Python validation via `workflow_dispatch`,
   - manual native Windows Python validation via `workflow_dispatch`.
4. Update all user-facing and developer-facing Windows documentation when implementing this plan so the documented
   support story matches the validated workflows.

## Non-Goals

- Dropping native Windows Python support — it remains valid for `cmd.exe`-based workflows.
- Adding MSVC (cl.exe) as a CI compiler — tracked separately.
- Changing the Linux or macOS CI configurations.
- Removing `MINGW64` support. It is supported as an MSYS2 option alongside `UCRT64`.

## Approach Options

### Option A: Use `UCRT64` MSYS2 Python by default and keep `MINGW64` plus native Python for manual runs (recommended)

Install `mingw-w64-ucrt-x86_64-python` and `mingw-w64-ucrt-x86_64-python-pip` for the default automatic Windows entry,
add a manual `MINGW64` entry with `mingw-w64-x86_64-python*`, and retain the native `actions/setup-python` entry for
manual dispatches. All MSYS2-based test execution stays within the selected MSYS2 environment.

**Pros:**

- Makes the recommended MSYS2 environment (`UCRT64`) the default on every push / PR.
- Preserves explicit coverage for both supported MSYS2 developer environments.
- Retains native Windows Python validation for `cmd.exe`-style workflows without paying that cost on every run.
- `uv` can be installed inside each MSYS2 environment through the matching package family or `pip`.

**Cons:**

- `actions/setup-python` caching and `astral-sh/setup-uv` cache integration may not work out of the box; MSYS2 Python
  lives outside the runner tool cache.
- MSYS2 Python package availability may lag behind CPython releases.
- Manual dispatch matrix logic becomes slightly more complex because Windows now has three variants.

### Option B: Keep the current native Windows default and add both MSYS2 environments only for manual runs

Keep the current automatic native-Python entry, then add manual `UCRT64` and `MINGW64` matrix rows for ad hoc runs.

**Pros:**

- Lowest-risk rollout because the current automatic path stays unchanged.
- Still allows targeted validation of both MSYS2 developer environments.

**Cons:**

- The default CI path still would not match the recommended Windows developer environment.
- MSYS2-specific regressions remain easier to miss on routine push / PR validation.

### Option C: Use `CLANG64` as the default MSYS2 environment

Switch the default MSYS2 subsystem to `CLANG64`, installing the clang-flavored Python and toolchain packages instead of
the GCC-based `UCRT64` / `MINGW64` families.

**Pros:**

- Uses the newer UCRT runtime and an LLVM-first toolchain.
- Aligns with MSYS2's forward-looking environment strategy.

**Cons:**

- It changes both runtime family and compiler family at once.
- The current documented developer path is GCC/MinGW-oriented, so this adds unnecessary migration pressure.

### Recommendation

Use **Option A**. Make `UCRT64` + MSYS2 Python the default automatic Windows entry, keep `MINGW64` + MSYS2 Python as a
manual `workflow_dispatch` target, and keep native Windows Python as another manual target. This matches the current
state of local validation, moves the default toward the newer MSYS2-recommended environment, and preserves direct
coverage for the alternate `MINGW64` and `cmd.exe`-oriented native Python paths.

## Implementation Phases

### Phase 1: Validate `UCRT64` and `MINGW64` Python availability

Before modifying workflows, confirm:

- [x] `mingw-w64-ucrt-x86_64-python` and `mingw-w64-x86_64-python` are both available in MSYS2 repos.
- [x] Matching `python-pip` packages are available in both environments; dependency installation continues through the
  repo's `make venv` / `uv sync` path.
- [x] `uv` is installable inside both `UCRT64` and `MINGW64`.
- [x] `make venv` works with both MSYS2 Python variants.

### Phase 2: Update `l0-ci.yml`

Expand the Windows matrix to three entries, with only the `UCRT64` entry enabled by default:

1. Change the default Windows matrix entry to use `UCRT64` MSYS2 Python:
   - Set `msystem: UCRT64`.
   - Add `mingw-w64-ucrt-x86_64-python` and `mingw-w64-ucrt-x86_64-python-pip` to the `msys2/setup-msys2` install list.
   - Gate `actions/setup-python` with `if: matrix.os != 'windows'`.
   - Gate `astral-sh/setup-uv` with `if: matrix.os != 'windows'`, or install `uv` via `pip` inside the MSYS2 shell.
   - Verify `make venv` creates the venv using `UCRT64` Python, not native Python.
   - Confirm `make test-all` passes.
2. Add a manual `windows-mingw64-python` matrix entry:
   - Set `msystem: MINGW64`.
   - Add `mingw-w64-x86_64-python` and `mingw-w64-x86_64-python-pip` to the `msys2/setup-msys2` install list.
   - Include it in the `select-matrix` output only when `event_name == 'workflow_dispatch'` and `platform` is `all` or
     `windows-mingw64-python`.
   - Add `"windows-mingw64-python"` to the `workflow_dispatch` platform choice list.
3. Add a manual `windows-native-python` matrix entry that uses `actions/setup-python` (native Windows Python):
   - Include it in the `select-matrix` output only when `event_name == 'workflow_dispatch'` and `platform` is `all` or
     `windows-native-python`.
   - Add `"windows-native-python"` to the `workflow_dispatch` platform choice list.
   - This entry keeps the current behavior: native Python, MSYS2 shell, same Make target.
4. Update the workflow `name:` display to distinguish all three Windows entries.

### Phase 3: Update release and snapshot workflows

Apply the default `UCRT64` MSYS2 Python changes to:

- `.github/workflows/l0-release.yml`
- `.github/workflows/l0-snapshot.yml`

These run `make dist` and a smoke test, both of which exercise the same path-sensitive code. Only the default `UCRT64`
configuration is needed here unless later evidence shows a release-only difference for `MINGW64` or native Python.

### Phase 4: Update Windows-facing documentation

When implementing the workflow changes, update every user-facing and developer-facing document that currently presents
Windows support so they all say the same thing:

- `UCRT64` and `MINGW64` are both supported MSYS2 environments.
- `UCRT64` is the recommended default for new Windows setups.
- `MINGW64` is supported and tested as an alternate developer environment.
- Native Windows Python remains valid for `cmd.exe`-oriented validation, but it is not the primary developer-parity
  path.
- User-facing setup examples must either be generic across both supported MSYS2 environments or explicitly rooted in the
  recommended `UCRT64` environment.
- `MINGW64`-specific package names, shell names, and path examples should appear only when a document is intentionally
  describing the alternate supported path.
- Hard-coded examples such as `pacman -S mingw-w64-x86_64-*`, `MSYS2 MINGW64`, or `mingw64\\bin` should be rewritten as
  either:
  - dual-form guidance covering both `UCRT64` and `MINGW64`, or
  - a single recommended `UCRT64` example with the `MINGW64` equivalent called out separately.

The expected document set includes at least:

- `l0/CLAUDE.md`
- `l0/docs/user/README.md`
- `l0/docs/user/README-WINDOWS.md`
- `l0/docs/reference/project-status.md`
- Any release-facing Windows README or packaging docs that still refer to `MINGW64` as the only supported MSYS2
  environment.

### Phase 5: Optional `CLANG64` matrix entry

If desired later, add a `workflow_dispatch`-only `CLANG64` matrix entry as a separate follow-on change.

## Verification Criteria

1. `make test-all` passes on the Windows CI runner using `UCRT64` MSYS2 Python on automatic push / PR runs.
2. `make test-all` passes on manual `workflow_dispatch` runs for `windows-mingw64-python`.
3. `make test-all` passes on manual `workflow_dispatch` runs for `windows-native-python`.
4. `make dist` succeeds and the smoke test passes with `UCRT64` MSYS2 Python in release/snapshot workflows.
5. The four MSYS2-specific regressions listed in the Summary would have been caught by the automatic `UCRT64` run and by
   the manual `MINGW64` run.
6. CI logs clearly show which Windows environment is active (`UCRT64`, `MINGW64`, or native Python).
7. The `workflow_dispatch` platform selector includes both `windows-mingw64-python` and `windows-native-python`.
8. The Windows-facing docs consistently describe `UCRT64` as recommended and `MINGW64` as additionally supported.

## Risks

- **MSYS2 Python version lag:** If `UCRT64` or `MINGW64` Python lags 3.14, the Windows entry may run a different Python
  version than other platforms. Mitigate by pinning and documenting.
- **MSYS2 package instability:** MSYS2 rolling-release packages occasionally break. Mitigate by pinning
  `msys2/setup-msys2` action version and optionally caching the MSYS2 installation.
- **`uv` compatibility:** `uv` may not fully support one or both MSYS2 Python variants. Mitigate by falling back to
  `pip install` if needed.
- **Documentation drift:** If workflow changes land without the Windows doc sweep, users will see conflicting guidance.
  Mitigate by treating the doc updates as part of the same implementation change set.
- **Matrix-selection complexity:** More Windows variants increase the chance of mistakes in manual dispatch filtering.
  Mitigate by explicitly naming and testing each platform selector.
