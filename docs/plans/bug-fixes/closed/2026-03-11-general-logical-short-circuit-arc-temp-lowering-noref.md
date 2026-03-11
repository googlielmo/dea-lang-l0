# Bug Fix Plan

## General `&&` / `||` expression lowering still hoists ARC temps ahead of short-circuit evaluation

- Date: 2026-03-11
- Status: Closed (fixed)
- Title: Fix general non-control-flow `&&` / `||` lowering that evaluates ARC-producing operands eagerly
- Kind: Bug Fix
- Severity: Critical (valid programs compile with incorrect boolean semantics)
- Stage: 1 and 2
- Subsystem: Backend Codegen
- Modules:
  - `compiler/stage1_py/l0_backend.py`
  - `compiler/stage2_l0/src/backend.l0`
  - `compiler/stage1_py/tests/backend/test_codegen_semantics.py`
  - `compiler/stage1_py/tests/backend/test_trace_arc.py`
  - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`
- Repro:
  - `./l0c --run -P <tmpdir> main` for a module containing:

```l0
let a: bool = false && len_s(tick(7)) > 0;
let b: bool = true || len_s(tick(8)) > 0;
```

## Summary

Control-flow condition lowering was fixed on 2026-03-11, but ordinary value expressions still use the old raw
binary-op path. That path evaluates both operands through `_emit_expr()` / `be_emit_expr()` before emitting the final
`&&` / `||` C expression. When either side materializes ARC temps, those declarations are emitted ahead of the boolean
operator, which breaks short-circuit semantics.

Observed current behavior in both Stage 1 and a built Stage 2 artifact:

1. `false && len_s(tick(7)) > 0` still calls `tick(7)`
2. `true || len_s(tick(8)) > 0` still calls `tick(8)`
3. the program prints `7`, `8`, `2` instead of only `2`

Observed generated C shape from Stage 1:

```c
l0_string l0_arc_1 = l0_main_tick();
l0_bool a = (0 && (l0_std_string_len_s(l0_arc_1) > 0));
l0_string l0_arc_2 = l0_main_tick();
l0_bool b = (1 || (l0_std_string_len_s(l0_arc_2) > 0));
```

This is the same defect class as the already-fixed control-flow issue, but in general expression contexts.

## Scope of the fix

1. Fix Stage 1 lowering for value-context `&&` / `||`.
2. Mirror the same fix into Stage 2.
3. Reuse the structured short-circuit lowering approach already introduced for control-flow conditions instead of
   inventing a separate boolean-lowering path.
4. Add direct regressions for runtime semantics and ARC cleanup.

## Fix implemented

### A. Add value-producing short-circuit lowering for logical binary ops

Files:

- `compiler/stage1_py/l0_backend.py`
- `compiler/stage2_l0/src/backend.l0`

Special-case `&&` and `||` in the normal binary-op emitter. Instead of calling the generic binary-expression path,
lower them by:

1. creating a fresh `l0_bool` temp for the result,
2. evaluating the logical expression through structured branching,
3. scoping any ARC temps emitted by leaf expressions inside a dedicated evaluation block,
4. returning the result temp as the value of the overall expression.

The intended implementation direction is to generalize the existing condition helper so the same mechanism can serve:

1. control-flow headers (`if`, `while`, `for`),
2. value-producing `&&` / `||` expressions in lets, assignments, returns, call args, and similar contexts.

### B. Keep the fix narrowly targeted

Only `&&` and `||` should move to the new path in this bug fix. Other binary operators should remain on the existing
lowering path unless a separate concrete repro proves they need the same treatment.

### C. Add regressions that lock down both semantics and cleanup

Files:

- `compiler/stage1_py/tests/backend/test_codegen_semantics.py`
- `compiler/stage1_py/tests/backend/test_trace_arc.py`
- `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`

Added coverage:

1. Stage 1 runtime regression for:
   - `let a = false && len_s(tick(7)) > 0`
   - `let b = true || len_s(tick(8)) > 0`
   - expected stdout proves neither RHS call runs
2. One additional Stage 1 regression where the logical expression is used outside a plain let initializer:
   - preferred shape: `return false && ...` and `return true || ...`
   - acceptable alternative: use the logical result as a call argument
3. Stage 1 ARC trace regression with dynamic-string RHS to confirm:
   - no leaks
   - no corrupted refcount transitions
4. Built Stage 2 bootstrap regression using the same runtime repro through `l0c-stage2`

## Verification

Run:

```bash
pytest -q compiler/stage1_py/tests/backend/test_codegen_semantics.py -k "logical_value_short_circuits_arc_rhs or logical_return_short_circuits_arc_rhs or if_condition_short_circuits_arc_rhs or while_condition_re_evaluates_arc_rhs"
pytest -q compiler/stage1_py/tests/backend/test_trace_arc.py -k "logical_expression_temp_cleanup or control_flow_condition_temp_cleanup"
bash compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh
```

Observed:

1. skipped `&&` / `||` RHS branches no longer execute side-effecting ARC-producing calls,
2. value-context logical expressions now use the same structured short-circuit lowering as control-flow conditions,
3. per-leaf condition cleanup avoids the uninitialized ARC cleanup issue seen in the first helper revision,
4. the built Stage 2 artifact shows the same corrected short-circuit behavior as Stage 1.

## Assumptions

1. This fix should land in both Stage 1 and Stage 2 in one change set.
2. Reusing the existing structured boolean-lowering machinery is preferable to adding a second parallel mechanism.
3. The plan intentionally focuses on general non-control-flow `&&` / `||` semantics only; no broader expression-lowering
   cleanup is included unless a new concrete repro appears.
