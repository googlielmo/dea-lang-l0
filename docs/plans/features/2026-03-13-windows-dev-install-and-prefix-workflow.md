# Feature Plan

## Windows developer activation and install-prefix workflow

- Date: 2026-03-13
- Status: Draft
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

Windows build and test support is now far enough along that `make install-dev-stage2` and `make install` can produce
usable Stage 2 binaries under MSYS2/MinGW-w64. That is not yet the same as a complete Windows developer workflow.

The current gaps are all around activation and selected-command UX:

1. Repo-local and install-prefix environment activation still assumes `source .../l0-env.sh`.
2. The selected `l0c` command is still modeled as a POSIX-style symlink, which is not a reliable Windows-native
   workflow.
3. `install-dev-*` and `install` produce Windows-capable stage wrappers, but the Makefile help text, activation
   guidance, and validation flow still describe only the POSIX shell path.

This follow-up plan makes the generated tool layout and Makefile workflow usable on Windows as a development and
installation surface, not just as a CI/bootstrap substrate.

## Goals

1. `make install-dev-stage1` and `make install-dev-stage2` produce a repo-local tool layout that is directly usable on
   Windows.
2. `make use-dev-stage1` and `make use-dev-stage2` select the active `l0c` command on Windows without relying on POSIX
   symlink behavior.
3. `make install PREFIX=...` produces an installed prefix with a Windows-native `l0c` entrypoint and activation path.
4. Windows users have a documented activation story for both MSYS2 bash and native shells.
5. Windows CI can exercise at least one dev-install or install-prefix workflow target directly.

## Non-Goals

- Full native MSVC Tier 1 support.
- Replacing the existing POSIX launchers or `l0-env.sh` on Linux/macOS.
- Rewriting shell-based Stage 2 regressions into Python.
- A global Windows installer package.

## Current State

- Repo-local Stage 2 wrapper generation already writes `l0c-stage2.cmd` on Windows.
- Install-prefix Stage 2 wrapper generation already writes `l0c-stage2.cmd` on Windows.
- Repo-local and install-prefix activation still only generate `l0-env.sh`.
- Alias selection still uses sibling-relative symlinks for `l0c`.
- The Makefile still tells users to `source .../l0-env.sh` after `use-dev-stage1`, `use-dev-stage2`, and `install`.

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

1. `install`, `use-dev-stage1`, and `use-dev-stage2` should print Windows instructions when the host is Windows.
2. The Windows guidance should prefer:
   - `call <path>\\l0-env.cmd` for `cmd.exe`
   - a PowerShell equivalent if `l0-env.ps1` is implemented
   - `source .../l0-env.sh` only for MSYS2/bash users
3. `install-dev-stage2` and `install` should print the Windows companion launchers they create when useful, so the
   generated `.cmd` surface is visible in CI logs.

### Phase 5: Validation in CI

Extend `.github/workflows/ci.yml` with one Windows job path that exercises developer installation or prefix
installation directly.

Minimum acceptance:

1. `make install-dev-stage2` on `windows-latest` produces a working repo-local Stage 2 launcher plus Windows-native
   activation artifacts.
2. `make use-dev-stage2` selects a working `l0c` command on Windows.
3. `make install PREFIX=...` produces a working installed `l0c` command on Windows, at least under the supported shell
   environment.

The exact workflow target can be staged if `test-all` remains too broad while the activation surface is still moving.

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
2. The selected `l0c` command works on Windows without relying on POSIX symlink semantics.
3. Native-shell activation no longer depends on `l0-env.sh`.
4. MSYS2/bash workflows continue to work unchanged.

## Related Documents

- [Windows build support](2026-03-11-windows-build-support.md)
- [Bootstrap plan](closed/2026-03-09-stage2-bootstrap-compiler-artifact-noref.md)
- [Project status](../../reference/project-status.md)
