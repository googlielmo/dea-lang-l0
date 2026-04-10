# Bug Fix Plan

## Shared let-diagnostic tail parity

- Date: 2026-04-10
- Status: Closed
- Title: Restore shared `let` diagnostic-tail parity in self-hosted statement checking
- Kind: Bug Fix
- Scope: Shared
- Severity: Medium
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
- Repro: direct `--check` smoke tests on unresolved `let` annotations and failed unannotated initializer inference

## Summary

The self-hosted compilers still miss two Python Stage 1 follow-on `let` diagnostics:

- `TYP-0040` when a `let` annotation cannot be resolved
- `TYP-0051` when an unannotated `let` initializer fails type inference after its primary expression error

These do not change compile success, but they remain the concrete statement-level diagnostic tail for `let`.

## Scope of This Fix

1. Emit `TYP-0040` after failed `let` annotation resolution.
2. Emit `TYP-0051` after failed unannotated initializer inference.
3. Keep the already-landed `TYP-0050` / `TYP-0052` / `TYP-0053` acceptance parity intact.

## Approach

- Mirror Python Stage 1’s supplemental `ST_LET` diagnostics after existing primary failures.
- Add one focused fixture per target covering unresolved annotations and failed inferred initializers.

## Tests

Minimum coverage to add in both trees:

1. unresolved `let` annotation reports `TYP-0040`,
2. unannotated `let` with an unknown initializer reports `TYP-0051`,
3. existing `let` parity fixtures continue to pass.

## Verification

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_let_diag_tail_err
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_let_diag_tail_err
```

## Outcome

- Implemented Stage 1-equivalent follow-on `let` diagnostics `TYP-0040` and `TYP-0051` in both self-hosted checkers.
- Added focused `typing_let_diag_tail_err` fixtures plus explicit assertions in both `expr_types_test.l0` suites.
- Verified both self-hosted CLIs now report the focused fixture with the expected supplemental diagnostics.

## Related Work

- `work/plans/bug-fixes/2026-04-10-shared-self-hosted-stage1-statement-parity-audit-noref.md`

## Assumptions

- Python Stage 1 remains the behavioral oracle for these follow-on `let` diagnostics.
