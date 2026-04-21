# Bug Fix Plan

## Shared ARC borrowed-param reassignment defensive entry retain

- Date: 2026-04-21
- Status: Closed
- Title: Fix ARC double-free and leak when a borrowed string/container parameter is reassigned by inserting a defensive
  retain at function entry
- Kind: Bug Fix
- Scope: Shared
- Severity: Critical
- Stage: Shared
- Targets:
  - L0 Stage 1 (Python)
  - L0 Stage 2 (self-hosted `.l0`)
  - L1 Stage 1 (seeded from L0 Stage 2)
- Origin: L0 Stage 2, using the fixed Stage 1 as the behavioral oracle
- Porting rule: Fix L0 Stage 1 first (the current oracle), port mechanically to L0 Stage 2, then port mechanically to L1
  Stage 1 while the backends remain aligned
- Target status:
  - L0 Stage 1: Implemented
  - L0 Stage 2: Implemented
  - L1 Stage 1: Implemented
- Subsystem: Backend codegen / ARC lowering
- Modules:
  - `l0/compiler/stage1_py/l0_backend.py`
  - `l0/compiler/stage2_l0/src/backend.l0`
  - `l1/compiler/stage1_l0/src/backend.l0`
  - `l0/docs/reference/ownership.md`
- Test modules:
  - `l0/compiler/stage1_py/tests/backend/test_trace_arc.py`
  - `l0/compiler/stage2_l0/tests/l0c_stage2_arc_trace_regression_test.py`
  - `l1/compiler/stage1_l0/tests/l1c_stage1_arc_trace_regression_test.py`
- Related:
  - `l0/docs/reference/ownership.md`
- Repro:
  ```l0
  func f(s: string) {
      s = "new"; // Prematurely releases caller's string under current Stage 2.
  }
  ```
  Or: `make test-stage2` → `l0c_stage2_arc_trace_regression_test.py` on Windows UCRT64.

## Summary

When a borrowed ARC-managed parameter (`string`, containers) is reassigned inside a function, the current lowering
double-frees the caller's reference and leaks the newly assigned value. This is masked on most platforms by
deterministic `malloc` pointer reuse but exposed on Windows UCRT due to its non-deterministic heap allocation strategy.

The fix is a compile-time static pre-pass: for each ARC-typed parameter, if the function body contains any assignment to
that parameter, emit a single retain at the function prologue and mark the parameter as owned for scope-exit cleanup.
The existing release-before-assign and scope-exit release paths then produce correct refcount behavior for every
control-flow shape (unconditional, conditional, loop-carried, multi-reassign).

## Current State

| Target     | Assignment lowering today                                                                                                                                                                                                                                                                                   |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| L0 Stage 1 | Promote-to-owned on first reassign at `l0/compiler/stage1_py/l0_backend.py:1590-1659` (`_is_borrowed_arc_param` + `_emit_reassignment`). Unsound on conditional reassignment: on a non-reassigning branch, the scope exits with `owned_vars` containing the param and releases the caller's borrowed value. |
| L0 Stage 2 | Unconditional release-before-assign at `l0/compiler/stage2_l0/src/backend.l0:2659-2676`. Matches the original bug exactly.                                                                                                                                                                                  |
| L1 Stage 1 | Mirrors L0 Stage 2's shape (seeded port).                                                                                                                                                                                                                                                                   |

A frequency audit across L0 stdlib, L0 Stage 2 compiler, L0 examples, L1 Stage 1 compiler (`.l0`), and L1 stdlib (`.l1`)
found **0 reassignments of ARC-typed parameters** in production code out of 2,299 functions scanned (315 with ARC
params). The only occurrence in the tree is the handcrafted repro `l0/param.l0`. This makes the runtime cost of the
always-on defensive fix effectively zero in practice.

## Root Cause

The ARC lowering does not distinguish between an owned local variable and a borrowed parameter when generating
assignment code. It emits `release(lhs); lhs = rhs;` for all ARC-managed destinations. The Stage 1 workaround
(promote-to-owned on first reassignment) introduces a new unsoundness on conditional reassignment rather than removing
the original one.

## Approach

### Defensive entry retain (Option E)

For each function, compute the set of ARC-typed parameters that are syntactically reassigned anywhere in the body — a
pure AST walk collecting `AssignStmt` nodes whose target is a plain `VarRef` matching a param name.

For each parameter in that set, at the function prologue:

1. Emit a retain on the parameter using the same runtime primitive the backend already uses for owned-expression
   retains.
2. Register the parameter in the scope's `owned_vars` rather than `declared`.

Thereafter the existing machinery is correct:

- Each reassignment releases the current value (the caller's original on the first reassignment; a prior owned value on
  subsequent ones) and assigns the new owned RHS.
- Scope exit releases the current value once.
- The entry retain's +1 is balanced by exactly one scope-exit release on every path.

For functions that never reassign the param, emit nothing extra — current borrowed semantics are kept.

### Cost

One retain + one release per call, only for functions whose body syntactically reassigns an ARC param. Empty set across
L0/L1 production code today per the audit.

## Scope of This Fix

In scope:

- L0 Stage 1 backend: replace the unsound promote-on-first-reassign path with the entry-retain path.
- L0 Stage 2 backend: add the entry-retain path (no existing special case to remove).
- L1 Stage 1 backend: mirror L0 Stage 2's change.
- Spec update in `l0/docs/reference/ownership.md` documenting the entry-retain rule.
- ARC trace tests exercising unconditional, conditional, loop-carried, `for`-update, and `with` header/cleanup ARC param
  reassignment in each stage.

Not in scope:

- New diagnostic codes (the fix is codegen-only).
- `owned` parameter annotations or grammar changes.
- Flow-sensitive reassignment analysis beyond the simple "any assignment in body" syntactic check.
- Container semantics changes beyond what `analysis_has_arc_data` already covers.

## Implementation

### Phase 1 — L0 Stage 1 (oracle)

File: `l0/compiler/stage1_py/l0_backend.py`.

1. Add helper `_collect_reassigned_arc_params(func: FuncDecl) -> list[tuple[str, Type]]` that walks `func.body` and
   returns `(param_name, param_type)` for each ARC-typed param whose name appears as a bare `VarRef` target of any
   `AssignStmt`.
2. In the function-body emitter (where params are registered via `add_declared`, around line 973), after param
   declaration, for each hit: emit the same retain call the backend already uses for same-type owned-expression copies,
   and call `scope.add_owned(mangled, ty)` instead of `add_declared`.
3. Delete `_is_borrowed_arc_param` at 1590-1616 and the `is_borrowed` branch of `_emit_reassignment` at 1644-1650.
   `_emit_reassignment` for ARC types collapses to the existing "temp, release old, assign temp" path.

### Phase 2 — L0 Stage 2

File: `l0/compiler/stage2_l0/src/backend.l0`.

1. Add `be_collect_reassigned_arc_params` paralleling the Stage 1 helper, walking the AST arena via the existing
   statement visitors.
2. In `be_emit_func_definition` around line 2650, for each reassigned ARC param, emit the retain primitive and call
   `sc_add_owned` instead of `sc_add_declared`.
3. `ST_ASSIGN` at 2659-2676 stays unchanged — it already does release-before-assign, which is correct once the param is
   marked owned.

### Phase 3 — L1 Stage 1

File: `l1/compiler/stage1_l0/src/backend.l0` (and any sibling that owns param registration).

1. Apply the mechanical port of Phase 2.

### Phase 4 — Spec update

File: `l0/docs/reference/ownership.md`, Section 4 (ARC Semantics).

Add a paragraph stating that borrowed ARC parameters are reassignable, that the compiler inserts a single retain at
function entry whenever the body reassigns such a parameter, and that the cost is one retain/release pair per call in
that case. Bump the `Version:` header to the implementation date.

### Phase 5 — Tests

- `l0/compiler/stage1_py/tests/backend/test_trace_arc.py` — add focused ARC trace cases covering unconditional,
  conditional (branch-asymmetric), loop-carried, `for`-update, and `with` header/cleanup reassignment of a `string`
  parameter.
- `l0/compiler/stage2_l0/tests/l0c_stage2_arc_trace_regression_test.py` — add the analogous Stage 2 regression set.
- `l1/compiler/stage1_l0/tests/l1c_stage1_arc_trace_regression_test.py` — add the analogous L1 Stage 1 regression set.

## Non-Goals

- Introducing a diagnostic for reassignment of borrowed ARC parameters; the chosen approach keeps the pattern valid.
- Extending the fix to `.field` or `[index]` lvalue targets (those are already handled correctly by the owned-lvalue
  path).
- Runtime behavior changes to the retain/release primitives themselves.

## Verification

```bash
cd l0 && ../.venv/bin/python -m pytest compiler/stage1_py/tests/backend/test_trace_arc.py
cd l0 && ../.venv/bin/python compiler/stage2_l0/tests/l0c_stage2_arc_trace_regression_test.py
cd l1 && ../.venv/bin/python compiler/stage1_l0/tests/l1c_stage1_arc_trace_regression_test.py
cd l0 && make -j test-all
cd l1 && make test-all
```

## Outcome

- Replaced the unsound Stage 1 borrowed-param promote-on-first-reassign path with a function-entry retain plus owned
  scope registration.
- Ported the same entry-retain ARC parameter ownership rule into the L0 Stage 2 and L1 Stage 1 backends.
- Updated `l0/docs/reference/ownership.md` to document borrowed ARC parameter reassignment and the entry-retain rule.
- Added ARC regression coverage in all three trees for unconditional, conditional, loop-carried, `for`-update, and
  `with` header/cleanup reassignment shapes.

## Verification Criteria

- `make -j test-all` passes on Linux, macOS, and Windows UCRT64.
- `make triple-test` passes.
- `l0c_stage2_arc_trace_regression_test.py` passes on Windows UCRT64.
- New Stage 1, Stage 2, and L1 ARC trace tests assert balanced refcounts on unconditional, conditional, and loop-carried
  repros.
- `make refresh-goldens` shows no change to emitted C for functions that do not reassign ARC params; only new
  entry-retain emissions in the handful of functions that do.
- Manual `--trace-arc` run on `l0/param.l0` shows zero leaks and no negative release.
