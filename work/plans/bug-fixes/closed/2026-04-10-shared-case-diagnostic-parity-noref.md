# Bug Fix Plan

## Shared case diagnostic parity

- Date: 2026-04-10
- Status: Closed
- Title: Restore shared `case` diagnostic parity in self-hosted statement checking
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
- Subsystem: Statement analysis / Diagnostics
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l0/compiler/stage2_l0/tests/fixtures/typing/*.l0`, `l1/compiler/stage1_l0/src/expr_types.l0`,
  `l1/compiler/stage1_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/fixtures/typing/*.l1`,
  `l0/compiler/stage1_py/l0_expr_types.py`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: `make -C l0 test-stage2 TESTS="expr_types_test"` and `make -C l1 test-stage1 TESTS="expr_types_test"`

## Summary

Python Stage 1 validates `case` scrutinees and arm literals, but the self-hosted compilers previously used `case` only
for return-flow analysis and accepted invalid programs silently.

Implemented outcome:

- both self-hosted compilers now emit `TYP-0106` for invalid `case` scrutinee types,
- both self-hosted compilers now emit `TYP-0107` for arm literal type mismatches,
- both self-hosted compilers now emit `TYP-0108` for duplicate literal values,
- focused typing fixtures and `expr_types_test` coverage now lock the regression in both trees.

## Root Cause

The self-hosted `ST_CASE` path checked arm bodies for return-flow purposes, but it did not:

- validate the scrutinee type,
- validate arm literal types against the scrutinee,
- detect duplicate literal values.

## Scope of This Fix

1. Add Stage 1-equivalent `case` scrutinee validation.
2. Add Stage 1-equivalent arm literal type checking.
3. Add duplicate literal detection for self-hosted `case` statements.
4. Keep the fix limited to the confirmed self-hosted acceptance gaps `TYP-0106` / `TYP-0107` / `TYP-0108`.

## Approach

- Reuse the existing literal AST forms produced by the parser for `int`, `byte`, `bool`, and `string` case arms.
- Validate the scrutinee against the allowed `case` type set before walking arm bodies.
- Infer each arm literal type, compare it against the scrutinee when valid, and record a stable duplicate-detection key
  per literal value.
- Preserve the settled self-hosted return-flow behavior for `case ... else`.

## Tests

Added focused fixtures and `expr_types_test` coverage in both trees for:

1. invalid `case` scrutinee type (`TYP-0106`),
2. arm literal type mismatch (`TYP-0107`),
3. duplicate literal value (`TYP-0108`).

## Verification

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_case_diag_err
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_case_diag_err
```

Verification completed for this fix:

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_case_diag_err
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_case_diag_err
```

## Related Work

- `work/plans/bug-fixes/2026-04-10-shared-self-hosted-stage1-statement-parity-audit-noref.md`

## Assumptions

- The self-hosted lexer/parser already rule out the Python-only `TYP-0109` case-literal escape path, so this tranche
  stays scoped to the confirmed reachable self-hosted gaps.
