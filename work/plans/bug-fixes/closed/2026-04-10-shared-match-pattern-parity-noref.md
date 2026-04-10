# Bug Fix Plan

## Shared match-pattern parity

- Date: 2026-04-10
- Status: Closed
- Title: Restore shared `match` scrutinee and arm-pattern typing parity in self-hosted statement checking
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
- Subsystem: Statement analysis / Match typing
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l0/compiler/stage2_l0/tests/fixtures/typing/*.l0`, `l1/compiler/stage1_l0/src/expr_types.l0`,
  `l1/compiler/stage1_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/fixtures/typing/*.l1`,
  `l0/compiler/stage1_py/l0_expr_types.py`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: direct `--check` smoke tests on non-enum `match`, unknown enum variant patterns, and pattern arity mismatch

## Summary

Python Stage 1 rejects three `match` typing cases that the self-hosted compilers still accept silently:

- non-enum scrutinees (`TYP-0100`)
- unknown enum variants in arm patterns (`TYP-0102`)
- pattern payload arity mismatch (`TYP-0101`)

This fix restores the Stage 1 arm-validation layer ahead of the existing self-hosted exhaustiveness logic.

## Root Cause

The self-hosted `ST_MATCH` path currently binds payload variables and checks arm bodies, but it never validates that the
scrutinee is an enum or that each arm pattern names a real variant with the correct payload arity.

## Scope of This Fix

1. Reject non-enum `match` scrutinees with `TYP-0100`.
2. Reject unknown enum variants in patterns with `TYP-0102`.
3. Reject payload arity mismatch in variant patterns with `TYP-0101`.
4. Keep the existing `TYP-0103` / `TYP-0104` / `TYP-0105` exhaustiveness tranche intact.
5. Do not widen this tranche into module-qualified pattern-name parity unless it is required by the confirmed cases.

## Approach

- Add a small helper to resolve enum variant metadata for one arm pattern.
- Validate each arm pattern before binding payload-variable types.
- Skip payload binding when the pattern is invalid, but still type-check the arm body.
- Add one focused fixture per target covering `TYP-0100`, `TYP-0101`, and `TYP-0102`.

## Tests

Minimum coverage to add in both trees:

1. non-enum `match` reports `TYP-0100`,
2. unknown variant pattern reports `TYP-0102`,
3. variant payload arity mismatch reports `TYP-0101`,
4. existing `match` tests continue to pass.

## Verification

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_match_diag_err
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_match_diag_err
```

## Outcome

- Implemented Stage 1-equivalent `match` arm validation for non-enum scrutinees (`TYP-0100`), unknown variants
  (`TYP-0102`), and payload arity mismatch (`TYP-0101`) in both self-hosted checkers.
- Added focused `typing_match_diag_err` fixtures plus explicit assertions in both `expr_types_test.l0` suites.
- Verified both self-hosted CLIs now reject the focused fixture with the expected diagnostic codes.

## Related Work

- `work/plans/bug-fixes/2026-04-10-shared-self-hosted-stage1-statement-parity-audit-noref.md`

## Assumptions

- Python Stage 1 remains the behavioral oracle for these `match` typing diagnostics.
- Module-qualified pattern-name edge cases can remain outside this tranche unless they surface while implementing the
  three confirmed behavior-changing gaps above.
