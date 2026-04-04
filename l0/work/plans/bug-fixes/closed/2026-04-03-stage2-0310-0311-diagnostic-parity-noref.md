# Bug Fix Plan

## Stage 2 `TYP-0310`/`TYP-0311` parity

- Date: 2026-04-03
- Status: Closed (fixed)
- Title: Restore Stage 2 parity for `let` and assignment mismatch diagnostics
- Kind: Bug Fix
- Severity: Medium
- Stage: 2
- Subsystem: Type Checker
- Modules: `compiler/stage2_l0/src/expr_types.l0`, `compiler/stage2_l0/tests/expr_types_test.l0`,
  `compiler/stage2_l0/tests/fixtures/typing/typing_err.l0`,
  `compiler/stage2_l0/tests/fixtures/typing/typing_nullable_assignment.l0`
- Test modules: `compiler/stage2_l0/tests/expr_types_test.l0`
- Repro: `make DEA_BUILD_DIR=build/dev-dea test-stage2 TESTS="expr_types_test"`

## Summary

Stage 2 used the wrong diagnostic split for local initialization and reassignment mismatches.

- annotated `let` initializer mismatches emitted `TYP-0311`
- assignment-statement mismatches emitted `TYP-0312`

This diverged from Python Stage 1, where equivalent conditions use:

- `TYP-0310` for annotated `let` initializer mismatches
- `TYP-0311` for assignment-statement mismatches

## Root Cause

`compiler/stage2_l0/src/expr_types.l0` assigned Stage 2-local diagnostic codes in the statement checker instead of
reusing the Stage 1 mapping for the same user-visible conditions.

## Scope of This Fix

1. Change Stage 2 annotated `let` initializer mismatches to `TYP-0310`.
2. Change Stage 2 assignment-statement mismatches to `TYP-0311`.
3. Add fixture coverage that distinguishes initializer mismatch from reassignment mismatch.
4. Add explicit coverage that nullable-to-non-nullable plain initialization still reports the Stage 1 parity code.

## Approach

In `compiler/stage2_l0/src/expr_types.l0`:

- update the `ST_LET` mismatch diagnostic from `TYP-0311` to `TYP-0310`
- update the `ST_ASSIGN` mismatch diagnostic from `TYP-0312` to `TYP-0311`

In the Stage 2 typing fixtures and tests:

- update the existing initializer mismatch expectation in `typing_err.l0`
- add a reassignment mismatch case in `typing_err.l0`
- update `typing_nullable_assignment.l0` to expect `TYP-0310`
- assert the revised code split in `expr_types_test.l0`

## Tests

Verify with:

```bash
make DEA_BUILD_DIR=build/dev-dea test-stage2 TESTS="expr_types_test"
```

Covered scenarios:

1. binary mismatch still reports `TYP-0310`
2. annotated `let` initializer mismatch reports `TYP-0310`
3. assignment statement mismatch reports `TYP-0311`
4. nullable-to-non-nullable annotated `let` mismatch reports `TYP-0310`

## Follow-Up Note

This fix is intentionally limited to the `TYP-0310`/`TYP-0311` split for `let` and assignment statements. Other Stage 2
diagnostic-code parity gaps, such as function-call argument mismatch codes, are out of scope for this change.

## Assumptions

- Python Stage 1 remains the diagnostic-code oracle for equivalent statement-checker conditions.
- Reusing the Stage 1 codes exactly is more important than preserving the previous Stage 2-only numbering split.
