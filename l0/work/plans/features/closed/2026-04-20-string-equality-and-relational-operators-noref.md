# Feature Plan

## Backport string equality and relational operators from L1

- Date: 2026-04-20
- Status: Completed
- Title: Backport string equality and relational operators from L1
- Kind: Feature
- Severity: Medium
- Stage: L0 (Stage 1 Python + Stage 2 self-hosted)
- Subsystem: Typing / backend / C emission / tests / docs
- Modules:
  - `l0/compiler/stage1_py/l0_expr_types.py`
  - `l0/compiler/stage1_py/l0_backend.py`
  - `l0/compiler/stage1_py/l0_c_emitter.py`
  - `l0/compiler/stage2_l0/src/expr_types.l0`
  - `l0/compiler/stage2_l0/src/backend.l0`
  - `l0/compiler/stage2_l0/src/c_emitter.l0`
  - `l0/compiler/stage2_l0/tests/expr_types_test.l0`
  - `l0/compiler/stage2_l0/tests/backend_test.l0`
  - `l0/compiler/stage2_l0/tests/c_emitter_test.l0`
  - `l0/compiler/stage2_l0/tests/l0c_lib_test.l0`
  - `l0/compiler/stage2_l0/tests/fixtures/typing/typing_equality_unsupported.l0`
  - `l0/compiler/stage2_l0/tests/fixtures/typing/typing_string_equality_ok.l0` (new)
  - `l0/compiler/stage2_l0/tests/fixtures/typing/typing_string_relational_ok.l0` (new)
  - `l0/compiler/stage2_l0/tests/fixtures/typing/typing_string_relational_err.l0` (new)
  - `l0/compiler/stage2_l0/tests/fixtures/driver/string_equality_main.l0` (new)
  - `l0/compiler/stage2_l0/tests/fixtures/driver/string_relational_main.l0` (new)
  - `l0/compiler/stage1_py/tests/type_checker/test_expr_typechecker_ops.py`
  - `l0/compiler/stage1_py/tests/integration/test_string_operators.py` (new)
  - `l0/docs/reference/design-decisions.md`
- Test modules:
  - `l0/compiler/stage2_l0/tests/expr_types_test.l0`
  - `l0/compiler/stage2_l0/tests/backend_test.l0`
  - `l0/compiler/stage2_l0/tests/c_emitter_test.l0`
  - `l0/compiler/stage2_l0/tests/l0c_lib_test.l0`
  - `l0/compiler/stage1_py/tests/type_checker/test_expr_typechecker_ops.py`
  - `l0/compiler/stage1_py/tests/integration/test_string_operators.py`
- Related:
  - `l1/work/plans/features/closed/2026-04-18-string-equality-operators-noref.md`
  - `l1/work/plans/features/closed/2026-04-18-string-relational-operators-noref.md`
- Repro: `make -C l0 test-stage1 && make -C l0 test-stage2 && make -C l0 check-examples`

## Summary

L1 Stage 1 recently wired `string ==`, `!=`, `<`, `<=`, `>`, `>=` through `rt_string_equals` and `rt_string_compare`.
The shared runtime, the shared diagnostic catalog, and `std.string::eq_s` / `cmp_s` were already in place on the L0
side, so the only missing pieces in L0 were the typing and lowering paths in both Stage 1 (Python) and Stage 2
(self-hosted). This plan brings L0 to parity with L1 on the string-operator surface in a single change, keeping
diagnostic codes and wording aligned across levels.

## Completion Notes

1. Stage 1 Python `_binary_equality` accepts `string` operands; `_infer_binary` accepts `string < string` (and siblings)
   before delegating to the int-path helper.
2. Stage 1 Python `_emit_binary_op` routes string `==` / `!=` through `emit_string_equals_call` (with unary negation for
   `!=`) and string relational operators through the new `emit_string_compare_call` helper.
3. Stage 2 `etc_infer_binary` permits `string == string`, `string != string`, and string relational operators while
   preserving `TYP-0172` for mixed-type comparisons and narrowing `TYP-0173` to non-string types.
4. Stage 2 `be_emit_binary_op` looks up operand types via `be_expr_type` and routes through the new
   `cem_emit_string_compare_call` helper or the existing `cem_emit_string_equals_call`.
5. Stage 1 and Stage 2 tests cover positive typing, backend lowering, emitter helper output, and end-to-end execution;
   the `typing_equality_unsupported` fixture was retargeted to struct equality plus mixed-type checks so `TYP-0173`
   keeps minimal coverage without relying on strings.
6. `l0/docs/reference/design-decisions.md` now documents string equality and ordering semantics. The shared
   diagnostic-code catalog already carried the narrowed generic `TYP-0173` wording, so no catalog edit was required.

## Defaults Chosen

1. `string == string` / `string != string` return `bool`, computed by `rt_string_equals` (with unary negation for `!=`).
2. `string <`, `<=`, `>`, `>=` return `bool`, computed by `(rt_string_compare(lhs, rhs) <op> 0)`.
3. Typing requires both operands to be `string`; mixed `string` / other-type still yields `TYP-0172` for equality and
   `TYP-0170` for relational.
4. `TYP-0173` narrows its wording to "equality not supported for this type", aligning with L1 and the existing shared
   catalog text.
5. No new runtime helpers, no ARC changes: both `rt_string_equals` and `rt_string_compare` are already in place and are
   read-only on their operands.

## Non-Goals

1. String concatenation via `+` — deferred; ARC result-ownership rules remain out of scope.
2. Changes to `case`-over-string lowering — it already uses the correct helper.
3. New diagnostic codes.

## Verification

1. `make -C l0 test-stage1` — Stage 1 Python tests including the new typing and integration coverage.
2. `make -C l0 test-stage2` — Stage 2 self-hosted tests including mirrored typing, backend, and emitter assertions.
3. `make -C l0 check-examples` — ensures existing examples still pass under the new operator surface.
4. `make -C l0 triple-test` — strict triple-bootstrap regression; must remain green.
5. `make -C l0 test-all` — full parallel validation.
