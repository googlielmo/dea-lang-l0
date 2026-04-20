# Tool Plan

## Port Shell Scripts to Python

- Date: 2026-03-23
- Status: Closed (implemented)
- Title: Port build and test shell scripts to Python; keep thin launcher/env pairs
- Kind: Tooling
- Severity: Medium
- Stage: Shared
- Subsystem: Build workflow / test harness
- Modules:
  - `scripts/build_stage2_l0c.py`
  - `scripts/gen_docs.py`
  - `compiler/stage2_l0/tests/l0c_stage2_help_output_test.py`
  - `compiler/stage2_l0/tests/l0c_stage2_test_env_isolation_test.py`
  - `compiler/stage2_l0/tests/l0c_codegen_test.py`
  - `compiler/stage2_l0/tests/l0c_stage2_verbose_output_test.py`
  - `compiler/stage2_l0/tests/l0c_ast_test.py`
  - `compiler/stage2_l0/tests/l0c_build_run_test.py`
  - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.py`
  - `compiler/stage2_l0/tests/l0c_stage2_default_dea_build_test.py`
  - `compiler/stage2_l0/tests/l0c_stage2_install_prefix_test.py`
- Test modules:
  - `compiler/stage2_l0/tests/` (all shell-based tests become Python runner cases)

## Summary

Python is already the project's cross-platform tooling language (pytest, Stage 1, build orchestration). Shell scripts
remain for build automation and Stage 2 integration tests, creating a dual-maintenance burden across supported host
workflows. This plan ports all non-trivial shell scripts to Python, leaving only the thin launcher and environment-setup
scripts as shell+cmd pairs.

Supersedes the "Rewriting `.sh` test scripts in Python (deferred)" non-goal from the
[Windows Build Support plan](closed/2026-03-11-windows-build-support.md).

## Motivation

1. **Eliminate dual maintenance.** Every behavioral change to a `.sh` script should not require a parallel `.cmd` update
   (or risk silent divergence).
2. **Test infrastructure consolidation.** The Stage 2 `.sh` test scripts are thin wrappers around "invoke l0c, check
   output." As pytest cases they gain parallel execution, structured reporting, and platform independence.
3. **Single tooling language.** Reduces the contributor setup surface: Python + C compiler + Make, no POSIX shell
   required for non-launcher tasks.

## Design Decision

**Rule of thumb:** if a script does more than set environment variables or `exec` a binary, it becomes Python.

### Keep as shell + cmd pairs

These are inherently shell-native (sourceable env setup, `exec`-into-compiler) and small enough that dual maintenance is
acceptable:

| Script                                 | Role                                |
| -------------------------------------- | ----------------------------------- |
| `scripts/l0c` + `scripts/l0c.cmd`      | Source-tree Stage 1 launcher        |
| `build/*/bin/l0-env.sh` + `l0-env.cmd` | Environment activation (sourceable) |

### Port to Python

| Current script                  | Target                                                                      |
| ------------------------------- | --------------------------------------------------------------------------- |
| `scripts/build-stage2-l0c.sh`   | `scripts/build_stage2_l0c.py` (or integrated into Makefile via Python call) |
| `scripts/gen-docs.sh`           | `scripts/gen_docs.py`                                                       |
| `compiler/stage2_l0/tests/*.sh` | pytest cases in `compiler/stage2_l0/tests/` (`.py` files)                   |

### Long-term aspiration

As the Dea stdlib matures (subprocess, path, string, glob), new simple tools may be written in Dea itself. Python
remains the tooling language until Dea can self-serve. This is a medium-term horizon, not a near-term action.

## Execution Plan

### Phase 1: Stage 2 test scripts (lowest risk, highest value)

1. For each `.sh` test script under `compiler/stage2_l0/tests/`, create an equivalent Python `.py` runner case using
   `subprocess.run` to invoke `l0c` and assert on output/exit codes.
2. Validate that the new pytest tests pass on all CI platforms (Linux, macOS, Windows/MSYS2).
3. Remove the `.sh` originals once the pytest replacements are green.
4. Update `Makefile` targets (`test-stage2`, etc.) if they invoke `.sh` tests directly.

### Phase 2: `build-stage2-l0c.sh`

1. Port the build logic to a Python script with `subprocess`, `pathlib`, and `shutil`.
2. Handle compiler detection for the currently supported C compilers (GCC, Clang, TCC, and `cc`) in a shared Python
   utility.
3. Update `Makefile` and `scripts/` references.
4. Remove the `.sh` original.

### Phase 3: `gen-docs.sh`

1. Port Doxygen/m.css invocation, PDF build, and preview-tree mirroring to Python.
2. Preserve all existing flags (`--strict`, `--pdf`, `--pdf-fast`, `--latex-only`, `-v`).
3. Update `Makefile`, CI workflows, and `CLAUDE.md` references.
4. Remove the `.sh` original.

## Non-Goals

- Porting `scripts/l0c`, `scripts/l0c.cmd`, or `l0-env.sh`/`l0-env.cmd`; these stay as shell pairs.
- Rewriting the `Makefile` itself; Make remains the top-level orchestrator.
- Adding MSVC support, including `cl.exe` detection, MSVC flag translation, or MSVC-specific validation. MSVC support is
  not on the roadmap for this tooling port.
- Porting any third-party vendored scripts (e.g., `tools/m.css/`).

## Risks

- **Behavioral drift during port.** Mitigation: each ported script must produce identical outputs for the same inputs
  before the original is removed. Compare old and new locally during each phase; if repeated comparisons become useful,
  add a provisional parity script and remove it before closing the plan.
- **Makefile coupling.** Some Make targets shell out to `.sh` scripts with assumptions about bash semantics. Mitigation:
  audit Make targets in each phase and update call sites.

## Success Criteria

1. Zero `.sh` files remain under `scripts/` or `compiler/stage2_l0/tests/` (excluding vendored `tools/`).
2. All CI platforms (Linux, macOS, Windows) pass with the Python replacements.
3. `make test-stage2`, `make triple-test`, and docs generation work unchanged from the user's perspective.
4. Compiler-detection logic for supported C compilers is consolidated in one Python module.

## Closure Notes

- Ported the Stage 2 shell regression scripts to Python runner cases and removed shell-test discovery.
- Replaced `scripts/gen-docs.sh` with `scripts/gen_docs.py`.
- Replaced direct `build-stage2-l0c.sh` call sites with `scripts/build_stage2_l0c.py`.
- Updated L0 workflow docs and dry-run workflow assertions to reference the Python tools.
