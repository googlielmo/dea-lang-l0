# Bug Fix Plan

## Missing cleanup when `?` fails in `with` header initializers

- Date: 2026-02-17
- Status: Closed (fixed)
- Title: Fix missing cleanup when `?` fails in `with` header initializers
- Kind: Bug Fix
- Severity: High (resource leak on early return)
- Stage: 1
- Subsystem: Backend Codegen
- Modules: `compiler/stage1_py/l0_backend.py`, `compiler/stage1_py/l0_expr_types.py`
- Repro: integration regression tests in `compiler/stage1_py/tests/integration/test_with_statement.py`

## Summary

Two related issues existed around header `expr?` short-circuits in `with` headers:

1. Inline `=>` form: prior successful header cleanups were not registered yet, so resources leaked.
2. Cleanup-block form: cleanup could run before some header lets were declared, producing invalid C and unsafe
   references.

## Root cause

In `compiler/stage1_py/l0_backend.py`, `_emit_with()` originally emitted all header initializers before registering
cleanup.

`TryExpr` lowering (`expr?`) calls `_emit_cleanup_for_return()` for null short-circuit paths; without prior registration
this skipped expected cleanup.

For cleanup-block form, this also allowed cleanup emission that referenced header lets not yet declared on failure
paths.

In `compiler/stage1_py/l0_expr_types.py`, there was no rule preventing cleanup-block references to maybe-uninitialized
non-nullable header lets.

## Scope of this fix

1. Inline `=>`: register cleanups incrementally as header items succeed.
2. Cleanup-block: predeclare nullable header lets (`T?`, including `T*?`) to `null` before initializer evaluation.
3. Type checker restriction: reject cleanup references to maybe-uninitialized non-nullable header lets (`T*`, `int`,
   etc.).
4. Preserve non-null pointer guarantees: no synthetic null initialization for non-nullable `T*`.

## Approach

### A. Incremental inline cleanup registration

In `_emit_with()`:

1. Initialize `with_scope.with_cleanup_inline = []` before header emission (inline form only).
2. Emit header items in order.
3. After each successful item, prepend its cleanup statement into `with_scope.with_cleanup_inline`.

This preserves LIFO order and ensures a short-circuit in item `N` can clean items `0..N-1`.

### B. Cleanup-block header failure support

In `_emit_with()` cleanup-block path:

1. Keep cleanup block registered before header emission.
2. For header `let` with nullable type, emit:
    - declaration initialized to `null`,
    - then assignment from original initializer expression.
3. For non-nullable header lets, keep existing declaration+initializer lowering.

### C. Type safety guard for cleanup-block references

In the type checker:

1. Detect if any header initializer can short-circuit via `?`.
2. Mark subsequent/current header lets as maybe-uninitialized on header-failure paths.
3. Reject cleanup-block references to maybe-uninitialized **non-nullable** header lets with `[TYP-0156]`.

## Tests

Add regression in `compiler/stage1_py/tests/integration/test_with_statement.py`:

- `test_with_header_try_failure_runs_prior_inline_cleanup`
    - Header item 1 succeeds with inline cleanup.
    - Header item 2 fails via `?`.
    - Assert prior cleanup runs, failed-item cleanup does not run, and body is skipped.
- `test_with_cleanup_block_header_try_failure_nullable_vars`
    - Nullable header lets, later `?` failure.
    - Assert cleanup runs safely, body is skipped, and nullable lets are predeclared.
- `test_typecheck_with_cleanup_block_header_try_failure_nonnullable_ref_rejected`
    - Assert cleanup reference to maybe-uninitialized non-nullable header let raises `[TYP-0156]`.
- `test_typecheck_with_cleanup_block_header_try_failure_nonnullable_not_referenced_passes`
    - Assert non-referenced non-nullable maybe-uninitialized lets are allowed.

## Verification

`pytest` is the intended verifier; also `./l0c` generation/build smoke checks can be used to validate behavior.

## Assumptions

- `TryExpr` remains valid only for nullable operands.
- Non-nullable pointer locals should not be auto-initialized to C `NULL` in lowered code.
