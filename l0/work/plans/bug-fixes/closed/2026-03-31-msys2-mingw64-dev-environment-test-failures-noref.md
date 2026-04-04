# Bug Fix Plan

## MSYS2 MINGW64 dev environment test failures

- Date: 2026-03-31
- Status: Closed
- Title: Fix Stage 2 test failures under MSYS2 MINGW64 with MinGW Python
- Kind: Bug Fix
- Severity: Medium (dev workflow broken on MSYS2 MINGW64; CI unaffected)
- Stage: Shared
- Subsystem: Test infrastructure / Stage 1 backend / CI
- Modules:
  - `compiler/stage1_py/l0_c_emitter.py`
  - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`
  - `compiler/stage2_l0/tests/l0c_stage2_verbose_output_test.sh`
  - `compiler/stage2_l0/tests/l0c_stage2_install_prefix_test.sh`
  - `compiler/stage2_l0/tests/l0c_stage2_help_output_test.sh`
  - `compiler/stage2_l0/tests/l0c_stage2_default_dea_build_test.sh`
  - `compiler/stage2_l0/tests/l0c_ast_test.sh`
  - `compiler/stage2_l0/src/c_emitter.l0`
  - `compiler/shared/runtime/l0_runtime.h`
- Test modules:
  - `compiler/stage1_py/tests/backend/test_codegen_semantics.py`
- Repro: On MSYS2 MINGW64 with MinGW Python: `make test-stage2`

## Summary

All Stage 2 tests pass on Windows CI (native Windows Python via `actions/setup-python@v6` + MSYS2 for C toolchain only)
but 8 tests fail when developing locally with MSYS2 MINGW64 and MinGW Python (`mingw-w64-x86_64-python`). The failures
fall into four categories:

1. `clean_env_run()` strips `TEMP`/`TMP` from child environments, causing GCC to fail with "Cannot create temporary file
   in `C:\WINDOWS\`: Permission denied".
2. `diff` and `cmp` (from the `diffutils` MSYS2 package) are absent on minimal MSYS2 installs; CI gets them from the
   GitHub Actions runner base image.
3. Stage 1 Python emits backslash paths (`C:\\msys64\\...`) in `#line` directives while Stage 2 L0's `std.path.join()`
   always uses forward slashes (`C:/msys64/...`), breaking triple bootstrap determinism.
4. Some test scripts use bare `env -i PATH="$PATH"` without preserving Windows-essential variables.

### Affected tests

| Test                                | Root Cause                                            |
| ----------------------------------- | ----------------------------------------------------- |
| `l0c_stage2_bootstrap_test.sh`      | Missing TEMP/TMP in `clean_env_run()`                 |
| `l0c_stage2_verbose_output_test.sh` | Missing TEMP/TMP in `clean_env_run()`                 |
| `l0c_stage2_help_output_test.sh`    | Bare `env -i`; missing `cmp`                          |
| `l0c_stage2_install_prefix_test.sh` | Missing TEMP/TMP; bare `env -i`; missing `cmp`        |
| `l0c_build_run_test.sh`             | Missing `diff`                                        |
| `l0c_codegen_test.sh`               | Missing `diff`                                        |
| `l0c_triple_bootstrap_test.py`      | `#line` path separator mismatch                       |
| `time_test`                         | Timezone/locale issue (separate investigation needed) |

## Root Cause

CI uses native Windows Python from `actions/setup-python@v6` and MSYS2 only for the C toolchain. Native Windows Python
resolves paths with backslashes and the CI runner image includes `diff`/`cmp`. MSYS2 MinGW Python
(`mingw-w64-x86_64- python`) creates POSIX-style venvs (`bin/python.exe`), and a minimal MSYS2 install may not include
`diffutils`.

## Fix

### A. Preserve TEMP/TMP in `clean_env_run()` and standardize bare `env -i` calls

Add `TEMP="${TEMP:-}" TMP="${TMP:-}"` to every `clean_env_run()` Windows branch. Add `is_windows_host()` and
`clean_env_run()` to tests that previously used bare `env -i PATH="$PATH"` (`l0c_stage2_help_output_test.sh`,
`l0c_stage2_default_dea_build_test.sh`). Also add missing `OS="${OS:-}"` to `l0c_stage2_install_prefix_test.sh`.

### B. Require `diffutils` in MSYS2 environment

- Add `diffutils` to CI workflow MSYS2 install lists (`l0-ci.yml`, `l0-release.yml`, `l0-snapshot.yml`).
- Add `diffutils` to `pacman` commands in `README-WINDOWS.md` and `l0/docs/user/README-WINDOWS.md`.

### C. Normalize `#line` paths to forward slashes in both stages

The `.cmd` wrapper sets `L0_HOME` with Windows backslashes (via CMD `%~fI`), while MinGW Python's `str(Path(...))`
produces forward slashes. This causes the triple bootstrap to fail: compiler 1 (invoked via `.cmd` wrapper) and compiler
2 (invoked directly) see different `L0_HOME` formats, producing different `#line` paths.

Fix: normalize paths to forward slashes in both emitters.

- Stage 1: in `l0_c_emitter.py:emit_line_directive()`, replace backslashes before encoding:
  `encode_c_string_bytes(str(filename).replace("\\", "/").encode("utf-8"))`
- Stage 2: in `c_emitter.l0:cem_module_filename()`, normalize the stored path:
  `replace_s((unit as DriverUnit*).path, "\\", "/")`

Forward slashes work in C `#line` directives on all platforms (GCC, Clang, MSVC).

Update `test_codegen_line_directives_normalize_backslashes` (renamed from
`test_codegen_line_directives_escape_ backslashes`) to expect forward-slash output.

### D. `time_test`: avoid `mktime` in `rt_time_local_offset_sec`

`rt_time_local_offset_sec` in `l0_runtime.h` computed the UTC offset by passing a `gmtime` breakdown to `mktime`,
interpreting it as local time. On some platforms, `mktime` rejects pre-epoch `time_t` values (`errno=EINVAL`). For
`TZ=Europe/Rome`, epoch 0 as local time maps to `time_t -3600`, which `mktime` refuses.

Fix: replace the `mktime`-based approach with a direct comparison of `gmtime` and `localtime` breakdowns. Both work on
all tested platforms for all timestamps. Compute the day difference (handling year boundaries), then derive the offset
in seconds.

File: `compiler/shared/runtime/l0_runtime.h` (`rt_time_local_offset_sec`).

## Verification

- On MSYS2 MINGW64 with MinGW Python (after `pacman -S diffutils`): `make test-stage2` passes previously failing tests.
- On CI or locally: `make test-stage1` passes with updated `#line` test expectation.
- `make triple-test` passes on both CI and MSYS2 dev environments.
