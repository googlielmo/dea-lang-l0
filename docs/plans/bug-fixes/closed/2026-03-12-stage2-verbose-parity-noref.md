# Bug Fix Plan

## Stage 2 verbose logging parity for `-v` / `-vvv`

- Date: 2026-03-12
- Status: Closed (fixed)
- Title: Restore Stage 2 verbose stderr parity for analysis, codegen, build, and run flows
- Kind: Bug Fix
- Severity: Medium
- Stage: 2
- Subsystem: CLI / driver / analysis / backend / build driver
- Modules:
  - `compiler/stage2_l0/src/analysis.l0`
  - `compiler/stage2_l0/src/backend.l0`
  - `compiler/stage2_l0/src/build_driver.l0`
  - `compiler/stage2_l0/src/driver.l0`
  - `compiler/stage2_l0/src/l0c_lib.l0`
  - `compiler/stage2_l0/src/parser.l0`
  - `compiler/stage2_l0/src/source_paths.l0`
- Test modules:
  - `compiler/stage2_l0/tests/build_driver_test.l0`
  - `compiler/stage2_l0/tests/source_paths_test.l0`
  - `compiler/stage2_l0/tests/l0c_stage2_verbose_output_test.sh`
- Repro:
  - `build/dea/bin/l0c-stage2 -v --build -P compiler/stage2_l0/tests/fixtures/driver ok_main`
  - `build/dea/bin/l0c-stage2 -vvv --build -P compiler/stage2_l0/tests/fixtures/driver ok_main`

## Summary

Stage 2 had two distinct verbose-parity regressions relative to Stage 1.

1. It was missing large parts of the normal `-v` and `-vvv` stderr contract: effective roots, compilation-unit
   progress, pass summaries, backend/codegen milestones, build-driver compiler details, and `--run` execution tracing.
2. It was also emitting the wrong messages at the wrong level: module loads were shown at info level, cache hits used
   Stage 2-only wording, and backend generation logged `Generating module ...` instead of Stage 1’s
   `Generating C code...`.

The fix restores the Stage 1 wording, ordering, and log-level split for equivalent Stage 2 code paths while keeping
the Stage 2 identity text unchanged.

## Fix Implemented

### A. Restore effective-root and analysis progress logging

1. Added Stage 1-compatible root formatting in `source_paths.l0`.
2. Logged effective system/project roots from both the general CLI input path and the build/run input path.
3. Restored `Building compilation unit ...`, per-pass stage banners, per-pass debug summaries, and the final
   `Analysis complete ...` line from the shared analysis pipeline.

### B. Restore module-load debug parity

1. Moved Stage 2 module-load tracing to debug level.
2. Reworked driver-side lex/parse sequencing so Stage 2 can emit:
   `Resolved ...`, `Lexing ...`, `Lexed N token(s) ...`, `Parsing ...`, and `Parsed module ...`
   in the same order as Stage 1.
3. Restored the exact cache-hit wording and added the Stage 1-style closure revisit so import edges produce the same
   cached-module debug lines.

### C. Restore backend/build/run verbose parity

1. Replaced `Generating module ...` with `Generating C code...`.
2. Added backend debug checkpoints for optional-wrapper preparation and header/forward-declaration emission.
3. Restored build-driver info/warning logs for generated C path, compiler choice, flag family, C option sources,
   optimization flag selection, visible compile command, built executable path, and `--run` execution command.
4. Split shell-execution formatting from visible log formatting so logged commands match Stage 1 even though Stage 2
   still uses shell-quoted command lines internally for `system()`.

## Verification

Executed:

```bash
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/source_paths_test.l0
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/build_driver_test.l0
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/driver_test.l0
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/l0c_lib_test.l0
bash compiler/stage2_l0/tests/l0c_stage2_verbose_output_test.sh
make DEA_BUILD_DIR=build/dev-dea test-stage2
```

Observed:

1. The new helper-level tests for root formatting and visible build-driver formatting pass.
2. The built-artifact verbose regression passes for both `-v` and `-vvv`, including cache-hit wording and `--run`
   tracing.
3. The full Stage 2 suite passes, including bootstrap, installed-prefix, trace, and triple-bootstrap coverage.
