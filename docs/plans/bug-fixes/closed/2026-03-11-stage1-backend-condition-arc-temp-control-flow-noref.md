# Bug Fix Plan

## Stage 1 backend hoists ARC condition temps out of control-flow headers

- Date: 2026-03-11
- Status: Closed (fixed)
- Title: Fix Stage 1 control-flow condition lowering that hoists ARC temps out of `if` / `while` / `for` headers
- Kind: Bug Fix
- Severity: Critical (valid programs compile with incorrect control-flow semantics)
- Stage: 1 and 2
- Subsystem: Backend Codegen
- Modules:
  - `compiler/stage1_py/l0_backend.py`
  - `compiler/stage2_l0/src/backend.l0`
  - `compiler/stage2_l0/src/parser/shared.l0`
  - `compiler/stage1_py/tests/backend/test_codegen_semantics.py`
  - `compiler/stage1_py/tests/backend/test_trace_arc.py`
  - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`

## Summary

Stage 1 incorrectly lowered control-flow conditions whenever expression emission produced statement-side effects,
especially ARC temp declarations. The concrete repro was in
`compiler/stage2_l0/src/parser/shared.l0`:

```l0
while (look < n && tok_is(tv_get(self.tokens, look), ord(TT_DOT))) {
```

When Stage 1 built the Stage 2 compiler, the generated C materialized `tv_get(self.tokens, look)` once before the
loop and reused that stale temp across iterations. That broke parser lookahead and more generally meant control-flow
conditions could lose short-circuiting or per-iteration re-evaluation whenever condition lowering emitted temps.

## Root cause

`_emit_expr()` / `be_emit_expr()` can emit declarations as a side effect, notably via ARC temp materialization in call
arguments. `if`, `while`, and `for` headers previously embedded `_emit_expr(cond)` directly into emitted C headers:

```python
c_cond = self._emit_expr(stmt.cond)
self.emitter.emit_while_header(c_cond)
```

That is unsafe because emitted declarations land before the header, not inside the logical evaluation point of the
condition. For `&&` and `||`, it also means right-hand ARC-producing leaves can be lowered outside correct short-circuit
control flow.

## Scope of the fix

1. Add dedicated control-flow condition lowering in Stage 1.
2. Mirror the same lowering in Stage 2 so the self-hosted backend does not retain the same defect class.
3. Remove the temporary Stage 2 parser workaround and return `parser/shared.l0` to the compact source form.
4. Add regressions for:
   - `if (false && ...)` with an ARC-producing RHS
   - `while (i < n && ...)` with an ARC-producing RHS that must be re-evaluated every iteration
   - ARC trace cleanup through control-flow condition evaluation
   - built Stage 2 artifact use of dotted qualified expressions and the original loop-condition shape

## Fix implemented

### A. Lower statement conditions through dedicated branching helpers

Files:

- `compiler/stage1_py/l0_backend.py`
- `compiler/stage2_l0/src/backend.l0`

Both backends now route `if`, `while`, and `for` conditions through dedicated helpers that:

1. evaluate the condition into a fresh boolean temp,
2. emit a scoped condition block for any ARC temps created during expression lowering,
3. lower `&&` and `||` with explicit short-circuit control flow,
4. clean condition-scope ARC temps before branching into the body or exiting the loop iteration.

`while` and `for` now lower their headers as `while (1)` and perform the real condition evaluation at the top of each
iteration, which restores correct re-evaluation semantics for temp-producing condition leaves.

### B. Remove the temporary parser workaround

File: `compiler/stage2_l0/src/parser/shared.l0`

The qualified-name lookahead is back to the compact form using `tv_get(..., look)` directly in the loop condition and
`::` check. That source shape is now valid again because the backend no longer hoists the temp out of the loop header.

### C. Add targeted regressions

Files:

- `compiler/stage1_py/tests/backend/test_codegen_semantics.py`
- `compiler/stage1_py/tests/backend/test_trace_arc.py`
- `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`

Added coverage for:

1. `if (false && len_s(tick()) > 0)` not evaluating the ARC-producing RHS,
2. `while (i < 3 && len_s(next_value(i)) > 0)` stopping after the first iteration where the RHS becomes false,
3. ARC trace cleanup staying leak-free through control-flow condition temps,
4. built `l0c-stage2` successfully checking a dotted qualified expression (`std.unit::present()`) and running the
   loop-condition repro without freezing the RHS result from the first iteration.

## Verification

Executed:

```bash
pytest -q compiler/stage1_py/tests/backend/test_codegen_semantics.py -k "if_condition_short_circuits_arc_rhs or while_condition_re_evaluates_arc_rhs"
pytest -q compiler/stage1_py/tests/backend/test_trace_arc.py -k "control_flow_condition_temp_cleanup"
bash compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh
```

Observed:

1. Stage 1 no longer evaluates the ARC-producing RHS of `false && ...` in control-flow conditions.
2. Stage 1 re-evaluates ARC-producing loop-condition leaves on every iteration.
3. ARC traces from control-flow condition temps remain leak-free and show sane heap refcount transitions.
4. The built Stage 2 artifact now handles dotted module-path qualified expressions and the original condition shape
   without relying on the parser-source workaround.

## Remaining scope boundary

This fix is intentionally limited to control-flow conditions. General expression lowering for non-control-flow `&&` /
`||` contexts still relies on normal expression emission and is not broadened here unless a separate bug requires it.
