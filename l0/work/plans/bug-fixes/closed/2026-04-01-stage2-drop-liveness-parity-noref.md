# Bug Fix Plan

## Stage 2 drop and liveness parity

- Date: 2026-04-01
- Status: Closed (fixed)
- Title: Restore Stage 2 parity for `drop` diagnostics and dropped-local liveness
- Kind: Bug Fix
- Severity: High
- Stage: 2
- Subsystem: Type Checker
- Modules: `compiler/stage2_l0/src/expr_types.l0`, `compiler/stage2_l0/tests/expr_types_test.l0`,
  `compiler/stage2_l0/tests/fixtures/typing/typing_drop_err.l0`,
  `compiler/stage2_l0/tests/fixtures/typing/typing_drop_flow_err.l0`
- Test modules: `compiler/stage2_l0/tests/expr_types_test.l0`
- Repro: `make test-stage2`

## Summary

Stage 2 had drifted away from Stage 1 in two related areas:

1. `drop` statements were not actually type-checked correctly.
2. Stage 2 had no flow-sensitive liveness tracking for dropped locals, so it could not enforce the Stage 1 diagnostics:
   - `TYP-0060` unknown variable in `drop`
   - `TYP-0061` dropping a non-pointer
   - `TYP-0062` second `drop`
   - `TYP-0150` later use of a dropped local

The initial liveness implementation also surfaced a Stage 2-specific ordering bug in `with` handling, where inline
cleanups were analyzed before the body and falsely marked header locals as dropped.

## Root Cause

### A. Broken `drop` checker wiring

`ps_parse_drop_stmt()` stores the dropped variable in `stmt.name`, but `ST_DROP` in
`compiler/stage2_l0/src/expr_types.l0` was reading `stmt.expr_a`, which is unset for `drop`.

That meant Stage 2 effectively skipped meaningful `drop` validation.

### B. Missing liveness model

Unlike Stage 1, Stage 2 did not track whether a visible local had already been dropped, so repeated `drop` and later
variable references could not be diagnosed precisely.

### C. Wrong `with` analysis order

Stage 2 analyzed inline `=>` cleanups before the `with` body. Once dropped-local liveness became active, valid patterns
such as:

```l0
with (let cfg = log_config_create(...) => drop cfg) {
    log_info(cfg, ...);
}
```

started to fail with false `TYP-0150` diagnostics because the cleanup `drop cfg` had already been simulated before the
body was checked.

## Scope of This Fix

1. Rewire `ST_DROP` to validate `stmt.name`.
2. Match Stage 1 error codes for `drop` diagnostics where Stage 2 had none.
3. Add flow-sensitive dropped-local liveness to Stage 2 analysis.
4. Ensure simple assignment to a local revives it, matching Stage 1 behavior.
5. Reorder Stage 2 `with` analysis so the body is checked before inline cleanups, in reverse cleanup order.
6. Add regressions for:
   - invalid `drop` targets
   - second `drop`
   - later use of a dropped local

## Approach

### A. Implement direct `drop` validation

In `compiler/stage2_l0/src/expr_types.l0`:

- look up the dropped local using `stmt.name`
- emit `TYP-0060` when the name is not a visible local
- emit `TYP-0061` when the visible local is neither `T*` nor `T*?`

### B. Add Stage 2 liveness tracking

Add a checker-owned stack of `StringIntMap*` values parallel to statement-scope entry:

- parameters and pattern vars start alive
- `let` declarations become alive when reached
- `drop` marks a local dead
- variable references consult liveness and emit `TYP-0150` on use-after-drop
- repeated `drop` emits `TYP-0062`
- simple local assignment revives the target

### C. Match Stage 1 `with` ordering

For `ST_WITH`:

1. check header item initializers
2. check the body
3. check inline cleanups in reverse (LIFO) order
4. check the cleanup block when present

This prevents valid body uses from being poisoned by cleanup-only `drop` statements while still preserving correct
cleanup-path liveness behavior.

## Tests

Added regressions to `compiler/stage2_l0/tests/expr_types_test.l0`:

1. `test_typing_drop_err`
   - validates `TYP-0060` and `TYP-0061`
2. `test_typing_drop_flow_err`
   - validates `TYP-0062` and `TYP-0150`

Added fixtures:

- `compiler/stage2_l0/tests/fixtures/typing/typing_drop_err.l0`
- `compiler/stage2_l0/tests/fixtures/typing/typing_drop_flow_err.l0`

## Verification

```bash
make DEA_BUILD_DIR=build/dev-dea test-stage2 TESTS="expr_types_test"
make test-stage2
```

The focused `expr_types_test` suite passed, and the full Stage 2 test suite finished green:

- Passed: 46
- Failed: 0

The full-suite verification was important because the `with` cleanup ordering bug only surfaced in self-hosted and
bootstrap-oriented tests such as `l0c_triple_bootstrap_test.py`, `l0c_build_run_test.sh`, and
`l0c_stage2_install_prefix_test.sh`.

## Assumptions

- Stage 1 remains the behavioral oracle for dropped-local diagnostics.
- `with` inline cleanups run after the body in reverse registration order.
- This fix intentionally covers checker-side liveness only; it does not change runtime `drop` semantics.
