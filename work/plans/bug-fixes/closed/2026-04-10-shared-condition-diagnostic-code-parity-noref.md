# Bug Fix Plan

## Shared condition-diagnostic code parity

- Date: 2026-04-10
- Status: Closed
- Title: Restore shared condition-diagnostic code parity for self-hosted statement checking
- Kind: Bug Fix
- Scope: Shared
- Severity: Medium
- Stage: Shared
- Targets:
  - L0 Stage 2
  - L1 Stage 1
- Origin: L0 Stage 2, using Python Stage 1 as the behavioral oracle
- Porting rule: Align L0 Stage 2 to the already-settled Stage 1/L1 diagnostic codes and verify L1 remains unchanged
- Target status:
  - L0 Stage 2: Implemented
  - L1 Stage 1: Implemented
- Subsystem: Statement analysis / Diagnostic codes
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l0/compiler/stage2_l0/tests/fixtures/typing/*.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`,
  `l1/compiler/stage1_l0/tests/fixtures/typing/*.l1`, `l0/compiler/stage1_py/l0_expr_types.py`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: direct `--check` smoke tests on invalid `if`, `while`, and `for` conditions

## Summary

`L0 Stage 2` still emits legacy condition diagnostic codes:

- `TYP-0313` for invalid `if` conditions
- `TYP-0314` for invalid `while` and `for` conditions

Python Stage 1 and `L1 Stage 1` already use the statement-specific codes `TYP-0070`, `TYP-0080`, and `TYP-0090`.

## Scope of This Fix

1. Switch `L0 Stage 2` `if` condition diagnostics to `TYP-0070`.
2. Switch `L0 Stage 2` `while` condition diagnostics to `TYP-0080`.
3. Switch `L0 Stage 2` `for` condition diagnostics to `TYP-0090`.
4. Add focused while/for fixture coverage in both self-hosted trees.

## Approach

- Update only the affected diagnostic codes in `L0 Stage 2`.
- Reuse the existing L1 behavior as the target reference for this tranche.
- Extend tests so future regressions are caught explicitly by code.

## Verification

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_loop_cond_err
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_loop_cond_err
```

## Outcome

- Updated `L0 Stage 2` to use the Stage 1/L1 condition codes `TYP-0070`, `TYP-0080`, and `TYP-0090`.
- Added focused `typing_loop_cond_err` fixtures plus explicit assertions in both `expr_types_test.l0` suites.
- Verified both self-hosted CLIs now report the loop-condition fixture with the expected codes.

## Related Work

- `work/plans/bug-fixes/2026-04-10-shared-self-hosted-stage1-statement-parity-audit-noref.md`
