# Bug Fix Plan

## Stage 1 backend ICE-1014 on mixed `int`/`byte` binary comparisons and equality

- Date: 2026-02-27
- Status: Closed (fixed)
- Title: Align Stage 1 backend binary-op lowering with typechecker mixed numeric semantics
- Kind: Bug Fix
- Severity: Critical (valid user programs abort with internal compiler error)
- Stage: 1
- Subsystem: Backend Codegen
- Modules:
  - `compiler/stage1_py/l0_backend.py`
  - `compiler/stage1_py/tests/integration/test_byte_type.py`
- Repro:
  - `./l0c -P compiler/stage2_l0/tests --run util_text_test`
  - Minimal repro:
    - `let c: byte = '5';`
    - `if (c < ('0' + base)) { ... }`

## Summary

Stage 1 accepted mixed `int`/`byte` binary expressions during typing, but backend lowering rejected non-arithmetic
mixed-type ops with an internal consistency check and raised:

- `[ICE-1014] type mismatch in binary operation`

This surfaced during normal program execution paths and blocked valid code generation.

## Root Cause

`_infer_binary` in the typechecker accepts mixed numeric operands for:

1. arithmetic (`+`, `-`, `*`, `/`, `%`)
2. comparison (`<`, `<=`, `>`, `>=`)
3. equality (`==`, `!=`) when compatible

In backend `_emit_binary_op`:

1. arithmetic already used the numeric path (`_rt_iadd`, etc.) with int-assignable checks.
2. non-arithmetic ops then enforced strict `left_ty == right_ty` and raised ICE otherwise.

This frontend/backend contract mismatch caused ICE for valid mixed numeric comparisons/equality.

## Scope of This Fix

1. Keep language/typechecker semantics unchanged (mixed `int`/`byte` remains valid where already accepted).
2. Update backend lowering to handle mixed numeric comparison/equality without ICE.
3. Add regression tests that previously triggered ICE-1014.
4. Leave stdlib behavior and APIs unchanged.

## Approach

### A. Backend lowering alignment

File: `compiler/stage1_py/l0_backend.py`

In `_emit_binary_op(...)`, before strict same-type ICE guard:

1. detect ops in `("<", "<=", ">", ">=", "==", "!=")`.
2. allow path when both operands are `_is_int_assignable(...)` (`int` or `byte`).
3. lower via `emit_binary_op(...)` directly.

Existing strict ICE guard remains for unsupported true mismatches.

### B. Regression coverage

File: `compiler/stage1_py/tests/integration/test_byte_type.py`

Add build/runtime regressions:

1. `test_build_mixed_byte_int_comparison_lt`
2. `test_build_mixed_byte_int_equality_eq`
3. `test_build_mixed_int_byte_comparison_ge`
4. `test_build_mixed_byte_int_equality_ne`

Each test asserts successful codegen/build/run (no ICE) and expected control-flow result.

## Verification

Executed:

```bash
cd compiler/stage1_py
uv run pytest -n auto tests/integration/test_byte_type.py -k "mixed_byte_int or mixed_int_byte"

./l0c -P compiler/stage2_l0/tests --run util_text_test
```

Expected and observed:

1. all new mixed numeric regression tests pass.
2. Stage 2 `util_text_test` runs successfully with no `[ICE-1014]`.

## Assumptions

1. Current language policy intentionally allows mixed `int`/`byte` numeric operations where typechecker already permits.
2. C integer promotion behavior is acceptable for backend lowering of mixed numeric comparison/equality.
3. No external tracker item exists yet (`noref`).
