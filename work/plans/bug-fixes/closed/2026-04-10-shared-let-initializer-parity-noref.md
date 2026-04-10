# Bug Fix Plan

## Shared let-initializer parity

- Date: 2026-04-10
- Status: Closed
- Title: Restore shared `let` initializer and annotation parity in self-hosted statement checking
- Kind: Bug Fix
- Scope: Shared
- Severity: High
- Stage: Shared
- Targets:
  - L0 Stage 2
  - L1 Stage 1
- Origin: L0 Stage 2, using Python Stage 1 as the behavioral oracle
- Porting rule: Fix the homologous Stage 2 path first, then port the settled logic mechanically into L1 Stage 1 while
  the code paths remain aligned
- Target status:
  - L0 Stage 2: Implemented
  - L1 Stage 1: Implemented
- Subsystem: Statement analysis / Local declarations
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l0/compiler/stage2_l0/tests/fixtures/typing/*.l0`, `l1/compiler/stage1_l0/src/expr_types.l0`,
  `l1/compiler/stage1_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/fixtures/typing/*.l1`,
  `l0/compiler/stage1_py/l0_expr_types.py`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: direct `--check` smoke tests on minimal `let x: void = noop();`, `let x = null;`, and `let x = noop();`

## Summary

Python Stage 1 rejects three `let` forms that the self-hosted compilers still accept silently:

- explicit `void` variable annotations (`TYP-0050`)
- inferred `null` initializers (`TYP-0052`)
- inferred `void` initializers (`TYP-0053`)

This fix restores those Stage 1-equivalent declaration checks in the self-hosted `ST_LET` path.

## Root Cause

The self-hosted `ST_LET` implementation currently checks only annotation-vs-initializer assignability. It does not
enforce the Stage 1 declaration rules for `void` locals or inferred initializers whose type is `null` or `void`.

## Scope of This Fix

1. Reject `let name: void = ...` with `TYP-0050`.
2. Reject `let name = null;` with `TYP-0052`.
3. Reject `let name = expr_of_type_void;` with `TYP-0053`.
4. Keep existing annotation mismatch behavior intact.
5. Do not widen this tranche into broader local-shadow or declaration-diagnostic parity.

## Approach

- Mirror the Python Stage 1 `ST_LET` decision order in the self-hosted checker.
- Resolve explicit annotations early and reject `void` annotations before normal assignability checks.
- For unannotated `let`, inspect the inferred initializer type and reject `null` and `void` before declaring the local.
- Add focused fixture-backed regressions in both self-hosted trees.

## Tests

Minimum coverage to add in both trees:

1. `let x: void = noop();` reports `TYP-0050`,
2. `let x = null;` reports `TYP-0052`,
3. `let x = noop();` reports `TYP-0053`,
4. existing `let` typing tests continue to pass.

## Verification

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check path/to/typing_let_diag_err
./l1/build/dea/bin/l1c-stage1 --check path/to/typing_let_diag_err
```

## Outcome

- Implemented Stage 1-equivalent `ST_LET` rejection for explicit `void` locals (`TYP-0050`), inferred `null`
  initializers (`TYP-0052`), and inferred `void` initializers (`TYP-0053`) in both self-hosted checkers.
- Added focused `typing_let_diag_err` fixtures plus explicit assertions in both `expr_types_test.l0` suites.
- Verified both self-hosted CLIs now reject the focused fixture with the expected diagnostic codes.

## Related Work

- `work/plans/bug-fixes/2026-04-10-shared-self-hosted-stage1-statement-parity-audit-noref.md`

## Assumptions

- Python Stage 1 remains the behavioral oracle for `let` declaration diagnostics.
- `TYP-0051` does not need to be pulled into this tranche unless a concrete self-hosted acceptance gap appears while
  implementing the three confirmed cases above.
