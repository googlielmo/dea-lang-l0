# Bug Fix Plan

## False `use of dropped variable` error for `drop` in `with` cleanup

- Date: 2026-02-27
- Status: Closed (fixed)
- Title: Fix false use-after-drop error for variables dropped in `with` cleanup clause
- Kind: Bug Fix
- Severity: High (blocks valid resource management patterns)
- Stage: 1
- Subsystem: Type Checker
- Modules: `compiler/stage1_py/l0_expr_types.py`, `compiler/stage1_py/tests/integration/test_with_statement.py`
- Repro: `with(let s = new S() => drop s) { printl_s(s.field); }`

## Summary

The Stage 1 type checker incorrectly flagged valid uses of a variable within a `with` body as `[TYP-0150] use of dropped variable` if that variable was explicitly dropped in the `with` statement's inline cleanup clause (`=> drop s`).

Example of failing code:
```l0
with(let s = new S("hello") => drop s) {
    printl_s(s.field); // Error: use of dropped variable 's'
}
```

## Root Cause

In `compiler/stage1_py/l0_expr_types.py`, the `WithStmt` visitor was analyzing each header item's `init` and `cleanup` expressions sequentially before visiting the statement body. 

Because `drop s` in the cleanup clause marks `s` as dead in the flow-sensitive liveness analysis, the subsequent analysis of the `with` body saw the variable as already dropped, even though the cleanup code only executes *after* the body at runtime.

## Scope of This Fix

1. Adjust the order of analysis in the type checker for `WithStmt`.
2. Ensure the `with` body is analyzed while header variables are still considered "alive".
3. Ensure cleanup expressions are analyzed after the body, in reverse (LIFO) order, to correctly catch actual use-after-drop errors within cleanup clauses themselves.

## Approach

### A. Reorder `WithStmt` analysis

In `compiler/stage1_py/l0_expr_types.py`:
- Modify `_check_stmt` for `WithStmt` to:
    1. Loop through `stmt.items` and analyze only `item.init`.
    2. Analyze `stmt.body`.
    3. Loop through `stmt.items` in `reversed()` order and analyze `item.cleanup` (if present).
    4. Analyze `stmt.cleanup_body` (the `cleanup { ... }` block) as before.

This alignment ensures that liveness state transitions caused by `drop` in a cleanup clause only affect the analysis of subsequent cleanups and the outer scope, not the `with` body.

## Tests

Added regressions to `compiler/stage1_py/tests/integration/test_with_statement.py`:

1. `test_typecheck_with_drop_in_cleanup_allowed`:
    - Verifies that `with(let s = ... => drop s)` allows using `s` in the body.
2. `test_typecheck_with_drop_in_cleanup_use_after_drop_rejected`:
    - Verifies that liveness analysis still correctly catches a `drop s1` in cleanup item N followed by a use of `s1` in cleanup item N-1 (since cleanups run LIFO).

## Verification

```bash
cd compiler/stage1_py
pytest tests/integration/test_with_statement.py
```

All 45 tests passed, including the new regressions.

## Assumptions

- Inline cleanup (`=>`) always executes in reverse order of registration (LIFO).
- Variables declared in the `with` header remain in scope for the duration of all cleanup clauses (both inline and block-based).
