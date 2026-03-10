# Bug Fix Plan

## `opt as string` from `string?` can produce dangling ARC ownership

- Date: 2026-02-25
- Status: Closed (fixed)
- Title: Stabilize Stage 1 ownership lowering for `string?` unwrap (`opt as string`)
- Kind: Bug Fix
- Severity: Critical (use-after-free, double-release, and silent data corruption)
- Stage: 1
- Subsystem: Backend Codegen
- Modules: `compiler/stage1_py/l0_backend.py`, `compiler/stage1_py/tests/backend/test_trace_arc.py`
- Repro:
  - Manual repros: `/tmp/opt_unwrap_repro.l0`, `/tmp/opt_unwrap_vector_repro.l0`
  - Automated regressions:
    - `test_trace_arc_optional_unwrap_return_stabilized`
    - `test_trace_arc_optional_unwrap_into_vector_stabilized`

## Summary

Stage 1 backend lowering treated `opt as string` (where `opt` is a place-owned `string?`) as a fresh rvalue in key ownership paths.
This allowed cleanup of the optional source to free the same heap string still used by the unwrapped result.

Observed failure modes:
1. Return boundary: returning `opt as string` could return already-freed storage.
2. Container boundary: `vs_push(v, opt as string)` could store a value that became dangling after source cleanup.
3. Follow-on ARC operations could touch corrupted refcounts, leading to invalid state panics or corrupted output.

## Root Cause

Two lowering decisions interacted incorrectly:

1. `_emit_owned_expr_with_expected_type(...)` only applied retain-on-copy for place expressions.
   `CastExpr` is non-place by default, so unwrap-casts from place optionals skipped ownership stabilization.

2. Call argument ARC temp materialization treated unwrap-casts like fresh ARC rvalues, introducing cleanup releases on aliases that were never retained as independent owners.

Net effect: unwrap results crossed cleanup/lifetime boundaries without a retain boundary.

## Scope of This Fix

1. Detect unwrap-cast-from-place (`T? as T` with place operand) explicitly.
2. Treat unwrap-cast-from-place as place-like in ownership-taking contexts (`let`, assignment, return conversion path).
3. Exclude unwrap-cast-from-place from ARC temp materialization in expression/call-argument paths.
4. Add trace-level regressions for return and container boundaries.
5. Keep all existing language/runtime APIs unchanged.

## Approach

### A. Add unwrap-from-place detector

In `compiler/stage1_py/l0_backend.py`:

- Add `_is_unwrap_cast_from_place(expr: Expr) -> bool`:
  - `expr` is `CastExpr`
  - source type is `NullableType`
  - destination type equals nullable inner type
  - cast operand is a place expression

### B. Centralize ARC temp materialization gating

In `compiler/stage1_py/l0_backend.py`:

- Add `_should_materialize_arc_temp(expr, expr_type) -> bool` and use it in:
  - `ExprStmt` ARC temp path
  - all `CallExpr` argument lowering paths (typed and fallback, including complex callee path)

Rule:
- Do materialize for ARC non-place rvalues when needed.
- Do **not** materialize for unwrap-cast-from-place.

### C. Stabilize ownership in owned-expression conversion

In `compiler/stage1_py/l0_backend.py`:

- In `_emit_owned_expr_with_expected_type(...)`, classify unwrap-cast-from-place as place-like.
- This routes same-type copy into `_emit_copy_expr_with_retains(...)`, creating an independent owner before source optional cleanup.

### D. Add regressions in ARC trace suite

In `compiler/stage1_py/tests/backend/test_trace_arc.py`:

1. `test_trace_arc_optional_unwrap_return_stabilized`
   - Program shape: local `opt: string?`, `return opt as string`
   - Assert:
     - output is exact expected string
     - retain `1 -> 2` exists before cleanup
     - no panic actions
     - reasonable non-negative RC range on heap events

2. `test_trace_arc_optional_unwrap_into_vector_stabilized`
   - Program shape: `vs_push(v, opt as string)` in helper, consume in caller
   - Assert:
     - output is exact expected string
     - no panic actions
     - reasonable RC range
     - at least one heap free event

Also add a small helper to collect integer heap RC values for robust assertions.

## Test Cases and Scenarios

1. Return boundary:
   - `let opt: string? = ...; return opt as string;`
2. Let/return via local:
   - `let s: string = opt as string; return s;`
3. Container boundary:
   - `vs_push(v, opt as string);` then `vs_get` and `vs_free`
4. Existing optional cleanup behavior:
   - null optional cleanup remains no-op on heap releases
   - existing ARC trace tests remain green

## Verification

```bash
cd compiler/stage1_py
../../.venv/bin/pytest -q tests/backend/test_trace_arc.py -k "optional_unwrap_return_stabilized or optional_unwrap_into_vector_stabilized"
../../.venv/bin/pytest -q tests/backend/test_trace_arc.py
```

Optional manual sanity repros (non-gating):

```bash
./l0c -P /tmp --run --trace-arc --trace-memory opt_unwrap_repro
./l0c -P /tmp --run --trace-arc --trace-memory opt_unwrap_vector_repro
```

Expected:
- clean output (`ab`, `cd`)
- no ARC panic markers
- balanced retain/release progression

## Assumptions and Defaults

- `string` remains ARC-managed with retain/release semantics.
- `opt as string` is not move-out; it does not consume/invalidate the optional binding.
- Ownership stabilization should happen only at real ownership boundaries, not via blanket retains.
- Tracker default is `noref` (no external issue ID assigned yet).
