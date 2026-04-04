# Bug Fix Plan

## Remove Windows trace-runner serialization by capturing through pipes

- Date: 2026-04-01
- Status: Closed (implemented)
- Title: Remove the Windows-only Stage 2 trace-runner serialization fallback
- Kind: Bug Fix
- Severity: Medium
- Stage: Shared
- Subsystem: Stage 2 test infrastructure / Windows trace capture
- Modules:
  - `compiler/stage2_l0/scripts/test_runner_common.py`
  - `compiler/stage2_l0/scripts/run_trace_tests.py`
  - `compiler/stage2_l0/scripts/run_test_trace.py`
  - `compiler/stage2_l0/tests/demo_trace_test.py`
- Test modules:
  - `compiler/stage2_l0/tests/l0c_stage2_trace_runner_common_test.py`
- Repro: `make DEA_BUILD_DIR=build/dev-dea test-stage2-trace` on MSYS2 `MINGW64` with MinGW Python and `L0_TEST_JOBS>1`

## Summary

The current Stage 2 trace harness defaults to one worker on Windows-like hosts even though the logical model should
support parallel runs. That fallback was added after false `TRACE_FAIL` reports under MSYS2 `MINGW64` with MinGW Python,
where trace artifacts could be analyzed before the final bytes were visible.

The existing workaround captures child stdout/stderr directly into files and then polls those files until they appear to
settle. This reduces the failure rate, but it does not establish a strong completion boundary and it leaves Windows
parallelism artificially disabled by default.

## Root Cause Hypothesis

The fragile part is the inherited file-handle capture path itself, not Stage 2 trace analysis. Redirecting child output
straight into files under MinGW Python appears to permit timing-dependent visibility gaps for the final trace bytes.
Serial execution only narrows the race window; it does not address the synchronization model.

Capturing through `subprocess.PIPE` is stronger:

1. `subprocess.run(..., stdout=PIPE, stderr=PIPE)` does not return usable output until the child communication phase is
   complete.
2. If a descendant process inherits the pipe handles and writes slightly later, the pipe stays open and the parent still
   waits for EOF.
3. The harness can then write fully materialized artifacts to disk after process completion, which removes the need for
   settle polling.

## Plan

1. Add one shared helper that captures binary stdout/stderr through pipes and writes artifact files only after the
   subprocess completes.
2. Switch `run_trace_tests.py`, `run_test_trace.py`, and the demo trace regression to the new helper or equivalent local
   pipe capture.
3. Remove the Windows-only `jobs=1` trace default so Stage 2 trace runs use the normal bounded auto-detected worker
   count unless `L0_TEST_JOBS` overrides it.
4. Add regression coverage that spawns a delayed grandchild writer and verifies the helper still captures late stdout
   and stderr bytes, including parallel helper calls.

## Verification

1. `python3 compiler/stage2_l0/tests/l0c_stage2_trace_runner_common_test.py`
2. `python3 compiler/stage2_l0/tests/l0c_stage2_run_trace_tests_selection_test.py`
3. `python3 compiler/stage2_l0/tests/l0c_stage2_run_tests_selection_test.py`
4. On MSYS2 `MINGW64` with MinGW Python, `make DEA_BUILD_DIR=build/dev-dea test-stage2-trace L0_TEST_JOBS=4`

## Risks

- Pipe capture keeps each test's trace output in memory until the process completes. The Stage 2 trace logs are expected
  to be small enough for this to remain acceptable.
- If the real issue is not file-handle visibility but something deeper in the Windows `.cmd` or process tree launch
  path, additional Windows-specific investigation may still be needed.
