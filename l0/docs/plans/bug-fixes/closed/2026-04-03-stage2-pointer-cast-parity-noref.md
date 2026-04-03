# Bug Fix Plan

## Stage 2 pointer cast parity

- Date: 2026-04-03
- Status: Draft
- Title: Restore Stage 2 parity for invalid explicit pointer casts
- Kind: Bug Fix
- Severity: High
- Stage: 2
- Subsystem: Type Checker
- Modules: `compiler/stage2_l0/src/expr_types.l0`, `compiler/stage2_l0/tests/expr_types_test.l0`
- Test modules: `compiler/stage2_l0/tests/expr_types_test.l0`
- Repro: `make test-stage2 TESTS="expr_types_test"`

## Summary

Stage 2 currently accepts invalid explicit pointer casts that Python Stage 1 rejects during semantic analysis.

Examples:

- `1 as int*`
- `1 as void*`
- `null as int*`
- `null as void*`

This is a parity drift. The invalid casts should fail in analysis with `TYP-0230`, matching Python Stage 1, instead of
surviving into later phases.

## Root Cause

`compiler/stage2_l0/src/expr_types.l0` resolves the cast target for `EX_CAST` but does not validate whether the source
type is actually castable to that target.

As a result:

- integer-to-pointer casts are accepted even though Stage 1 rejects them
- `null as T*` is also accepted by analysis
- backend/codegen can then see invalid cast shapes that should have been blocked earlier

## Scope of This Fix

1. Make Stage 2 cast checking match Python Stage 1 for explicit casts.
2. Reuse Stage 1 diagnostic codes:
   - `TYP-0230` for invalid explicit casts
   - preserve existing `TYP-0700` and `TYP-0701` special cases
3. Ensure invalid pointer casts are rejected before backend lowering.
4. Add focused regressions for invalid pointer-cast cases.

## Approach

In `compiler/stage2_l0/src/expr_types.l0`:

- port the Python Stage 1 `EX_CAST` validation logic rather than inventing new Stage 2-only rules
- resolve the target type
- infer the source expression type
- allow the cast only when the source type is assignable to the target using the same assignability-based rule as Stage
  1
- preserve the compile-time constant overflow check for `int -> byte` (`TYP-0700`)
- preserve the explicit null optional-pointer unwrap rejection (`TYP-0701`)
- otherwise emit `TYP-0230`

The backend should not gain compensating logic for invalid pointer casts. The checker must reject them before codegen.

## Tests

Add regressions in `compiler/stage2_l0/tests/expr_types_test.l0` and matching fixtures for:

1. `1 as int*` -> `TYP-0230`
2. `1 as void*` -> `TYP-0230`
3. `null as int*` -> `TYP-0230`
4. `null as void*` -> `TYP-0230`
5. existing valid-cast behavior remains accepted
6. existing `TYP-0700` and `TYP-0701` coverage remains green

## Verification

```bash
make test-stage2 TESTS="expr_types_test"
make test-stage2
```

## Follow-Up Note

After the Stage 2 fix lands, apply the same checker-side cast-validation patch to
`l1/compiler/stage1_l0/src/expr_types.l0` so L1 Stage 1 no longer accepts `1 as T*` and no longer lets `null as T*`
reach backend ICEs.

## Assumptions

- Python Stage 1 remains the behavioral oracle for explicit cast legality.
- Rejecting `1 as T*` and `null as T*` is intended language behavior, not merely an implementation detail.
- This plan only covers checker-side parity. It does not introduce new backend behavior for invalid casts.
