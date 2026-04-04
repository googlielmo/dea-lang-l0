# Feature Plan

## Windows developer activation and install-prefix workflow

- Date: 2026-03-13
- Status: Closed
- Title: Add a usable Windows workflow for `install-dev-*`, `use-dev-*`, and `install`
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: Build workflow / launchers / developer UX
- Modules:
  - `Makefile`
  - `scripts/dist_tools_lib.py`
  - `scripts/gen_dist_tools.py`
  - `docs/reference/project-status.md`
  - `CLAUDE.md`
  - `.github/workflows/ci.yml`
- Test modules:
  - `compiler/stage2_l0/tests/l0c_stage2_runner_env_test.py`
  - `compiler/stage2_l0/tests/l0c_stage2_shell_runner_test.py`
  - `compiler/stage2_l0/tests/l0c_stage2_install_prefix_test.sh`

## Summary

This plan is implemented.

Windows developer activation and install-prefix workflows now generate `l0-env.cmd` for native `cmd.exe` activation,
repo-local Stage 1 now generates `l0c-stage1.cmd` and participates in the selected `l0c.cmd` alias flow, and the
existing GitHub Actions Windows matrix path exercises the workflow through `make test-all` by running the workflow
regression suite.

## Goals

1. Repo-local and install-prefix workflows expose a Windows-native activation helper instead of requiring manual `PATH`
   edits outside MSYS2/bash.
2. Repo-local Stage 1 gains a native-shell path with parity closer to the Stage 2 `l0c.cmd` alias flow.
3. `make install PREFIX=...` keeps its working installed `l0c.cmd` entrypoint while gaining the same activation helper
   story.
4. Windows users keep a documented activation story for both MSYS2 bash and native shells.
5. Windows CI exercises at least one workflow path that consumes the generated native-shell activation artifacts.

## Non-Goals

- Full native MSVC Tier 1 support.
- Replacing the existing POSIX launchers or `l0-env.sh` on Linux/macOS.
- Rewriting shell-based Stage 2 regressions into Python.
- A global Windows installer package.

## Current State

- Repo-local Stage 2 wrapper generation already writes `l0c-stage2.cmd` on Windows.
- Install-prefix Stage 2 wrapper generation already writes `l0c-stage2.cmd` on Windows.
- Repo-local Stage 1 now writes `l0c-stage1.cmd` on Windows.
- Repo-local and install-prefix activation now write both `l0-env.sh` and `l0-env.cmd`.
- `make use-dev-stage1` and `make use-dev-stage2` now both select a working `l0c.cmd` alias on Windows.
- `make install PREFIX=...` installs `l0-env.cmd` alongside the selected Stage 2 launcher pair.
- The existing Windows GitHub Actions matrix path validates the workflow through `make test-all`; no separate workflow
  file was required.

## Implementation

### Phase 1: Define the Windows activation contract

Document the intended Windows behavior before changing the generators:

1. Repo-local build roots under `DEA_BUILD_DIR/bin/` should expose:
   - stage-specific wrappers (`l0c-stage1`, `l0c-stage2`, plus `.cmd` companions on Windows)
   - one selected `l0c` command that works on Windows
   - one Windows-native activation path for `cmd.exe`
   - optionally one Windows-native activation path for PowerShell
2. Installed prefixes under `PREFIX/bin/` should expose the same shape for the selected Stage 2 compiler.
3. The Windows-native workflow should not require `source .../l0-env.sh` outside MSYS2/bash.

### Phase 2: Replace symlink-only alias selection on Windows

Update `scripts/dist_tools_lib.py` so the selected `l0c` command has a Windows-native implementation.

Candidate approach:

1. Keep the existing symlink implementation on POSIX.
2. On Windows, generate `l0c.cmd` as a tiny forwarding wrapper to `l0c-stage1.native` / `l0c-stage2.native` or to the
   stage wrapper command as appropriate.
3. If a plain `l0c` file is still needed for MSYS2/bash symmetry, generate it deliberately instead of relying on a
   symlink.

The key requirement is that `make use-dev-stage1` and `make use-dev-stage2` must select a working `l0c` command on
Windows with no manual relinking.

### Phase 3: Generate Windows-native activation scripts

Extend `scripts/dist_tools_lib.py` and `scripts/gen_dist_tools.py` to emit Windows-native activation helpers.

Expected outputs:

1. Repo-local build:
   - `bin/l0-env.cmd`
   - optionally `bin/l0-env.ps1`
2. Install prefix:
   - `bin/l0-env.cmd`
   - optionally `bin/l0-env.ps1`

Expected behavior:

1. Add the corresponding `bin/` directory to `PATH`.
2. Set `L0_HOME` correctly for repo-local and install-prefix layouts.
3. Preserve the existing `l0-env.sh` behavior for MSYS2/bash users.
4. Avoid mutating `L0_SYSTEM` and `L0_RUNTIME_INCLUDE` unless the workflow explicitly needs it.

### Phase 4: Makefile and messaging updates

Update `Makefile` so help text and post-target guidance match the host workflow.

Required changes:

1. `install`, `use-dev-stage1`, and `use-dev-stage2` should keep printing Windows instructions when the host is Windows.
2. The Windows guidance should prefer:
   - `call <path>\\l0-env.cmd` for `cmd.exe`
   - a PowerShell equivalent if `l0-env.ps1` is implemented
   - `source .../l0-env.sh` only for MSYS2/bash users
3. `install-dev-stage2` and `install` should print the Windows companion launchers they create when useful, so the
   generated `.cmd` surface is visible in CI logs.

### Phase 5: Validation in CI

Validate the workflow through the existing `.github/workflows/ci.yml` Windows matrix entry by extending `make test-all`
to include the workflow regression suite.

Minimum acceptance:

1. `make install-dev-stage2` on `windows-latest` produces a working repo-local Stage 2 launcher plus the new
   Windows-native activation artifacts.
2. `make use-dev-stage2` keeps selecting a working `l0c` command on Windows.
3. `make install PREFIX=...` keeps producing a working installed `l0c` command on Windows, now with matching activation
   artifacts for the supported shell environment.

The implementation path chosen here keeps CI in the existing matrix instead of adding a separate workflow file.

## Verification

Execute on Windows, ideally in both MSYS2 bash and one native shell:

```bash
make DEA_BUILD_DIR=build/dea install-dev-stage1
make DEA_BUILD_DIR=build/dea install-dev-stage2
make DEA_BUILD_DIR=build/dea use-dev-stage2
build/dea/bin/l0c-stage2.cmd --version
build/dea/bin/l0c.cmd --version
make PREFIX="$PWD/build/prefix-win" install
build/prefix-win/bin/l0c.cmd --version
```

Also validate CI with a Windows manual dispatch target such as:

```bash
make install-dev-stage2
make use-dev-stage2
make PREFIX=build/prefix-win install
```

Expected:

1. The generated repo-local and install-prefix layouts include Windows-native launchers for the selected compiler.
2. The selected Stage 2 `l0c` command continues to work on Windows without relying on POSIX symlink semantics.
3. Native-shell activation no longer depends on manual `PATH` edits alone.
4. MSYS2/bash workflows continue to work unchanged.

## Related Documents

- [Windows build support](closed/2026-03-11-windows-build-support.md)
- [Bootstrap plan](closed/2026-03-09-stage2-bootstrap-compiler-artifact-noref.md)
- [Project status](../../reference/project-status.md)
