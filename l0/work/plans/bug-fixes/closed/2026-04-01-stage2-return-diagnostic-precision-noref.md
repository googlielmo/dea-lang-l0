# Bug Fix Plan

## Stage 2 return diagnostic precision

- Date: 2026-04-01
- Status: Closed (fixed)
- Title: Distinguish bare `return;` from failed return-expression inference in the Stage 2 type checker
- Kind: Bug Fix
- Severity: High
- Stage: 2
- Subsystem: Type Checker
- Modules: `compiler/stage2_l0/src/expr_types.l0`, `compiler/stage2_l0/tests/expr_types_test.l0`,
  `compiler/stage2_l0/tests/fixtures/typing/typing_return_void_in_non_void.l0`,
  `compiler/stage2_l0/tests/fixtures/typing/typing_return_invalid_expr.l0`, `compiler/stage1_py/l0_expr_types.py`,
  `compiler/stage1_py/tests/type_checker/test_expr_typechecker_basic.py`
- Test modules: `compiler/stage2_l0/tests/expr_types_test.l0`,
  `compiler/stage1_py/tests/type_checker/test_expr_typechecker_basic.py`
- Repro: `make DEA_BUILD_DIR=build/dev-dea test-stage2 TESTS="expr_types_test"`

## Summary

Stage 2 treated any `null` result from `etc_infer_expr()` inside `ST_RETURN` as if it meant a bare `return;`.

That conflated two different situations:

1. `return;` in a non-`void` function, which should report `TYP-0315`.
2. `return expr;` where `expr` already failed to type-check, which should report the underlying expression diagnostic
   without adding a secondary return-type mismatch.

Stage 1 already behaved correctly because its `_check_return()` delegates expected-type checking to `_infer_expr()`
through `widening_type=expected` while still distinguishing `stmt.value is None` from expression failure.

## Root Cause

In `compiler/stage2_l0/src/expr_types.l0`, `ST_RETURN` called `etc_infer_expr(self, stmt.expr_a)` unconditionally and
then interpreted `ret_ty == null` as "no return value".

However:

- the parser represents bare `return;` with `expr_a = -1`
- `etc_infer_expr()` returns `null` both for `expr_id < 0` and for inference failure

As a result, invalid return expressions incorrectly triggered `TYP-0315` in addition to their real error.

## Scope of This Fix

1. Make `ST_RETURN` branch on expression presence before calling `etc_infer_expr()`.
2. Preserve the existing bare-return mismatch behavior for non-`void` functions.
3. Add regressions for:
   - bare `return;` in a non-`void` function
   - invalid return expressions that must not emit a secondary mismatch
4. Clean up the Stage 1 `_check_return()` implementation so it matches its real delegated contract more clearly.

## Approach

### A. Split `ST_RETURN` by AST presence

In `compiler/stage2_l0/src/expr_types.l0`:

- if `stmt.expr_a < 0`, treat the statement as bare `return;` and compare against `void`
- otherwise, infer the expression type
- if inference fails, stop without adding `TYP-0315`
- if inference succeeds, compare actual vs expected and emit `TYP-0315` only on a real mismatch

### B. Align Stage 1 source clarity with existing behavior

In `compiler/stage1_py/l0_expr_types.py`:

- remove the misleading local `actual`/`TODO` shape from `_check_return()`
- keep the delegated compatibility check through `_infer_expr(..., widening_type=expected, context_code="TYP-0315")`

## Tests

Added regressions:

1. `compiler/stage1_py/tests/type_checker/test_expr_typechecker_basic.py`
   - `test_return_void_in_non_void_function`
   - `test_invalid_return_expr_does_not_add_return_type_mismatch`
2. `compiler/stage2_l0/tests/expr_types_test.l0`
   - `test_return_void_in_non_void`
   - `test_return_invalid_expr`

Added fixtures:

- `compiler/stage2_l0/tests/fixtures/typing/typing_return_void_in_non_void.l0`
- `compiler/stage2_l0/tests/fixtures/typing/typing_return_invalid_expr.l0`

## Verification

```bash
../.venv/bin/python -m pytest compiler/stage1_py/tests/type_checker/test_expr_typechecker_basic.py -q
make DEA_BUILD_DIR=build/dev-dea test-stage2 TESTS="expr_types_test"
```

Both targeted suites passed after the fix.

## Assumptions

- Stage 1 remains the oracle when Stage 1 and Stage 2 wording or behavior diverge.
- Failed expression inference should not be reclassified as a bare `return;` case in Stage 2.
