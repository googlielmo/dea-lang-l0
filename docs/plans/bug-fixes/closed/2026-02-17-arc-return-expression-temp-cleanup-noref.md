# Bug Fix Plan

## ARC temp in return expression skips cleanup

- Date: 2026-02-17
- Status: Closed
- Title: Fix leaked ARC temporaries materialized while emitting return expressions
- Kind: Bug Fix
- Severity: High (heap string leak on valid code path)
- Stage: 1
- Subsystem: Backend Codegen
- Modules: `compiler/stage1_py/l0_backend.py`
- Repro: `test_codegen_concat3_nested_arg_temp_materialized`, `test_trace_arc_concat3_nested_argument_freed` in
  `compiler/stage1_py/tests/backend/test_codegen_semantics.py` and `compiler/stage1_py/tests/backend/test_trace_arc.py`

## Summary

The Stage 1 backend leaked ARC-managed temporaries when they were materialized during return-expression emission.

Representative case:

```l0
func concat3_s(a: string, b: string, c: string) -> string {
    return concat_s(concat_s(a, b), c);
}
```

The inner `concat_s(a, b)` is lowered to an ARC temp. That temp was not released on function return in some paths.

## Root cause

In `compiler/stage1_py/l0_backend.py`, `_emit_return()` previously decided `needs_cleanup` before emitting the return
expression. ARC temp materialization for nested call arguments happens during expression emission, so the scope could
gain owned vars only after `needs_cleanup` had been computed.

Effect:

1. `needs_cleanup` was false.
2. Return expression emitted and created ARC temp(s).
3. Backend returned directly without cleanup for those new temps.

## Scope of this fix

1. Emit/evaluate return expression before deciding whether cleanup is needed.
2. Keep existing return-value safety behavior by storing the return value in a dedicated return temp when cleanup runs.
3. Add explicit regressions for the `concat3_s` nested-call return shape in both codegen and ARC-trace suites.

## Approach

### A. Reorder `_emit_return()` sequencing

In `_emit_return()`:

1. Compute `c_value = emit_return_value(...)` first.
2. Recompute `needs_cleanup` after expression emission.
3. If cleanup is needed:
    - materialize `ret_tmp`,
    - run `_emit_cleanup_for_return(...)`,
    - return `ret_tmp`.
4. Otherwise, return `c_value` directly.

This ensures ARC temps introduced by expression lowering participate in normal scope-chain cleanup.

### B. Add codegen regression for concat3 pattern

In `compiler/stage1_py/tests/backend/test_codegen_semantics.py`:

- Add `test_codegen_concat3_nested_arg_temp_materialized`.
- Assert generated `concat3_s` function body contains ARC temp materialization (`_arc_`) and release path
  (`rt_string_release(...)`).
- Compile+run and assert output is `one-two`.

### C. Add runtime ARC trace regression

In `compiler/stage1_py/tests/backend/test_trace_arc.py`:

- Add `test_trace_arc_concat3_nested_argument_freed`.
- Execute two `concat3_s` calls and assert expected output.
- Assert heap free events include at least one intermediary + one final free per call (>=4 total), each with rc
  `1 -> 0`.

## Verification

```bash
source ./.venv/bin/activate
pytest -q compiler/stage1_py/tests/backend/test_codegen_semantics.py -k "concat3_nested_arg_temp_materialized or nested_arc_call_temps_released"
pytest -q compiler/stage1_py/tests/backend/test_trace_arc.py -k "concat3_nested_argument_freed or nested_concat_intermediary_freed"
pytest -q compiler/stage1_py/tests/backend/test_codegen_semantics.py
pytest -q compiler/stage1_py/tests/backend/test_trace_arc.py
```

Observed on this fix branch: all commands above pass.

## Assumptions

- ARC temp materialization for nested call arguments remains the backend strategy for non-place ARC rvalues.
- Static string literals still require no retain/release cleanup.
- No language/runtime API changes are required; this is backend-lowering and test hardening only.
