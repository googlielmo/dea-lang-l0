# Feature Plan

## Stage 2 Driver `--build` and `--run` Milestone

- Date: 2026-03-10
- Status: Implemented (2026-03-10)
- Title: Implement Stage 2 `l0c --build` and `--run` on top of the Stage 2 backend
- Kind: Feature
- Severity: High
- Stage: 2
- Subsystem: Driver / CLI build-run execution / host compiler invocation
- Modules:
  - `compiler/stage2_l0/src/build_driver.l0`
  - `compiler/stage2_l0/src/l0c_lib.l0`
  - `compiler/stage2_l0/src/l0c.l0`
  - `compiler/shared/l0/stdlib/sys/rt.l0`
  - `compiler/shared/runtime/l0_runtime.h`
- Test modules:
  - `compiler/stage2_l0/tests/build_driver_test.l0`
  - `compiler/stage2_l0/tests/l0c_lib_test.l0`
  - `compiler/stage2_l0/tests/l0c_build_run_test.sh`
  - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`
  - `compiler/stage1_py/tests/backend/test_system_runtime.py`
- Repro: `./build/stage2/bin/l0c-stage2 --run -P examples hello`

## Summary

Implement Stage 2 `--build` and `--run` by reusing the completed Stage 2 analysis plus `backend_generate()` path, then
invoking the host C compiler and built executable through `std.system.system()`.

Stage 1 is the oracle for CLI semantics, diagnostic-code reuse, compiler selection, `main` validation, `--keep-c`,
`--output`, `L0_CFLAGS` merge order, runtime include/lib resolution, and normal process exit behavior.

This milestone stays intentionally narrow. The broader shared-runtime process roadmap already exists in
`docs/plans/features/closed/2026-03-09-stdlib-runtime-fs-path-raw-io-bootstrap-noref.md`, which defers a general
subprocess API with explicit pipe control to its Phase 3. This feature must not invent a competing generic exec layer;
it should only use the existing `system()` path plus the minimum shared-runtime adjustments needed for Stage 2 CLI
parity.

## Non-Goals

1. Replacing the repository-root `./l0c` wrapper with Stage 2.
2. Introducing a general subprocess API, stdin/stdout/stderr pipe control, or process-handle abstractions.
3. Implementing the full `std.fs` / raw-byte stdio surface from the broader bootstrap-runtime plan.
4. Adding shell-quote-aware parsing for `--c-options` or `L0_CFLAGS`.
5. Guaranteeing Windows shell parity in this milestone.

## Public Interfaces And Runtime Changes

1. Add a new Stage 2 helper module `build_driver.l0` with two command entrypoints:
   - `bd_cmd_build(opts: CliOptions*, cfg: LogConfig*) -> int`
   - `bd_cmd_run(opts: CliOptions*, cfg: LogConfig*) -> int`
2. Move the current C-option merge helpers out of `l0c.l0` into `build_driver.l0` and rename them with the `bd_` prefix
   so all build/run plumbing lives in one module.
3. Pull forward only the low-level file-metadata slice needed from the broader
   `2026-03-09-stdlib-runtime-fs-path-raw-io-bootstrap-noref.md` plan:
   - `sys.rt` struct
     `RtFileInfo { exists: bool; is_file: bool; is_dir: bool; size: int?; mtime_sec: int?; mtime_nsec: int?; }`
   - `sys.rt` function `rt_file_info(path: string) -> RtFileInfo`
4. Keep `std.system.system(cmd: string) -> int` unchanged at the L0 API level, but update `rt_system` in `l0_runtime.h`
   to return normalized command status instead of the raw C `system()` wait-status word.
5. Reserve Stage 2-only diagnostic `L0C-9511` for output/temp-file write failures and migrate the current Stage 2
   `--gen` write-file path to that code before reusing the same path in `--build` / `--run`, because Stage 1 already
   uses `L0C-0041` for a different meaning.

## Implementation Changes

### 1. Build/run orchestration split

1. Keep `l0c.l0` responsible for CLI parsing, shared input normalization, and dispatch only.
2. Dispatch `CM_BUILD` and `CM_RUN` to `build_driver.l0` and remove `L0C-9510` from those two modes only.
3. Leave `CM_AST` on NYI in this milestone; `CM_GEN`, `CM_CHECK`, `CM_TOK`, `CM_SYM`, and `CM_TYPE` remain unchanged.

### 2. Analysis and entry `main` validation

1. Reuse the current Stage 2 analysis path and fail early on analysis diagnostics exactly as `--gen` already does.
2. Validate the entry module `main` function using Stage 2 name/symbol/signature tables with Stage 1-equivalent codes:
   - `L0C-0012` when the entry module does not define `main` as a function,
   - `L0C-0016` when the resolved function type for `main` is missing,
   - `L0C-0013` warning when `main` returns something other than `void`, `int`, or `bool`, while still proceeding.
3. Keep the existing generated C entry-wrapper behavior unchanged; this milestone is only about driver parity.

### 3. Output-path and temp-path policy

1. `--build` output executable path stays Stage 1-compatible:
   - `-o <path>` uses `<path>`,
   - otherwise default to `a.out`.
2. Kept C output path stays Stage 1-compatible:
   - `--build --keep-c -o <path>` writes `<path>.c`,
   - `--build --keep-c` without `-o` writes `a.c`,
   - `--run --keep-c -o <path>` writes `<path>.c`,
   - `--run --keep-c` without `-o` writes `a.c`.
3. `--run` always uses a throwaway executable path and ignores `-o` for the executable, matching Stage 1.
4. `--run` without `--keep-c` must emit Stage 1 warning `L0C-0017` when `-o/--output` is provided.
5. Temp root selection is locked to:
   - first existing directory among `TMPDIR`, `TEMP`, `TMP`,
   - else `/tmp` when it exists,
   - else `.`.
6. Temp stems are generated from wall-clock seconds/nanoseconds plus a local retry counter; each candidate must be
   probed with `file_exists` before use.
7. Temporary `.c`, compiler-capture `.stdout/.stderr`, and throwaway executable files are deleted on a best-effort basis
   after use.

### 4. Host compiler invocation

1. Compiler discovery order must exactly match Stage 1:
   - explicit `--c-compiler`,
   - `$L0_CC`,
   - `tcc`,
   - `gcc`,
   - `clang`,
   - `cc`,
   - `$CC`.
2. Compiler-family detection must mirror Stage 1 heuristics for `tcc`, `gcc|clang`, `cc`, `cl`, and unknown.
3. Effective C options remain:
   - `split($L0_CFLAGS) + split(--c-options)`.
4. Default optimization-flag policy must mirror Stage 1 exactly:
   - explicit `-O*` or `/O*` suppresses defaults,
   - debug flags select debug-friendly optimization,
   - otherwise default quick optimization is added for supported families.
5. Runtime include resolution must be:
   - explicit `--runtime-include`,
   - else `$L0_RUNTIME_INCLUDE`,
   - else `$L0_HOME/shared/runtime` when `L0_HOME` is set,
   - else no automatic include path.
6. Runtime library resolution must be:
   - explicit `--runtime-lib`,
   - else `$L0_RUNTIME_LIB`,
   - else none.
7. Runtime library validation must preserve Stage 1 diagnostics exactly:
   - `L0C-0014` when the configured path does not exist or is not a directory,
   - `L0C-0015` when the directory exists but contains none of `libl0runtime.a`, `libl0runtime.so`,
     `libl0runtime.dylib`, or `l0runtime.lib`.
8. Host compiler stdout/stderr must be captured via shell redirection into temp files, then replayed after the command
   finishes so Stage 2 can preserve Stage 1-style `L0C-0010` error reporting instead of dumping compiler output
   interleaved with driver diagnostics.
9. All shell-bound path/argument tokens must be built with one shared POSIX single-quote helper. The helper must quote
   spaces and embedded single quotes correctly.

### 5. `--run` execution

1. `--run` must call the same build helper used by `--build`, with a throwaway executable path and the Stage 1 keep-C
   path policy above.
2. Runtime program arguments after `--` must be forwarded unchanged and shell-quoted with the same POSIX helper used for
   compiler invocation.
3. Ordinary program exit codes must be returned unchanged from `--run`.
4. On POSIX, signal-terminated child processes are normalized to shell-style `128 + signal`; this explicitly preserves
   `130` for interrupt and is the locked runtime policy for this milestone.
5. `--run` must not capture or replay the executed program’s stdout/stderr; it should inherit the terminal like Stage 1.

### 6. Shared-runtime boundary

1. The only shared-runtime work allowed in this milestone is:
   - `rt_system` exit-status normalization,
   - `rt_file_info` metadata support required by runtime-lib validation and temp-root selection.
2. Do not implement raw byte stdio, directory traversal, subprocess pipes, or a second execution API here.
3. The plan must explicitly reference the broader runtime plan:
   `docs/plans/features/closed/2026-03-09-stdlib-runtime-fs-path-raw-io-bootstrap-noref.md` as the future home for a
   general subprocess interface with explicit pipe control.

## Test Cases And Scenarios

1. `build_driver_test.l0` covers pure helper behavior:
   - env-first + CLI-last C-option merge,
   - compiler-family detection,
   - optimization-flag selection,
   - POSIX shell quoting for spaces and embedded single quotes,
   - keep-C path derivation,
   - temp-root selection from env/fallbacks.
2. `l0c_lib_test.l0` covers direct Stage 2 command dispatch:
   - default `--build` success for a simple fixture,
   - `--run` success for a simple fixture,
   - `--run` exit-code pass-through for a non-zero-return fixture,
   - `--run --keep-c -o custom_name` writes `custom_name.c`.
3. `l0c_build_run_test.sh` covers real host-toolchain execution:
   - `--build` produces an executable,
   - built executable runs and returns expected status,
   - `--run` forwards argv with whitespace correctly,
   - `--run` forwards argv containing a single quote correctly,
   - no compiler available emits `L0C-0009`,
   - explicit compiler failure emits `L0C-0010`,
   - missing runtime-lib directory emits `L0C-0014`,
   - empty runtime-lib directory emits `L0C-0015`,
   - missing `main` emits `L0C-0012`,
   - non-preferred `main` return type emits `L0C-0013`,
   - `--run -o custom_name` without `--keep-c` emits `L0C-0017`.
4. `l0c_stage2_bootstrap_test.sh` is extended so the built repo-local artifact supports:
   - `--check`,
   - `--gen`,
   - `--build`,
   - `--run`.
5. `test_system_runtime.py` verifies shared-runtime `std.system.system()` returns normalized command status for ordinary
   non-zero exits and interrupt-style status on POSIX.
6. Final milestone verification commands are:

```bash
python3 compiler/stage2_l0/run_tests.py
python3 compiler/stage2_l0/run_trace_tests.py
```

## Documentation Updates

1. Update `docs/reference/project-status.md` to mark Stage 2 `--build` and `--run` as implemented.
2. Update `docs/reference/architecture.md` so the Stage 2 pipeline includes host C compiler invocation and executable
   launch for build/run modes.
3. Update `compiler/stage2_l0/README.md` and `CLAUDE.md` command examples to include Stage 2 `--build` and `--run`.
4. Update `docs/reference/standard-library.md` so the `std.system.system()` contract matches the normalized runtime
   behavior.
5. Mention in the new milestone plan and any touched docs that the broader process API remains deferred to
   `docs/plans/features/closed/2026-03-09-stdlib-runtime-fs-path-raw-io-bootstrap-noref.md` Phase 3.

## Assumptions And Defaults

1. Stage 1 remains the behavior oracle for this milestone.
2. The existing Stage 2 `--gen` path is stable enough to serve as the sole code-generation path for build/run.
3. Pulling forward `rt_file_info` is acceptable because exact `L0C-0014` vs `L0C-0015` parity requires directory
   detection that Stage 2 cannot express with the current runtime surface.
4. The broader subprocess design is already reserved by `2026-03-09-stdlib-runtime-fs-path-raw-io-bootstrap-noref.md`;
   this milestone must not preempt it with a new general exec abstraction.
5. POSIX shell execution is the accepted command-construction target for this milestone; Windows-specific shell behavior
   is not an acceptance gate here.
