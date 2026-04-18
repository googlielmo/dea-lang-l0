# Feature Plan

## Land string equality and inequality operators

- Date: 2026-04-18
- Status: Completed
- Title: Land string equality and inequality operators
- Kind: Feature
- Severity: Medium
- Stage: L1
- Subsystem: Typing / backend / C emission / tests / docs
- Modules:
  - `l1/compiler/stage1_l0/src/expr_types.l0`
  - `l1/compiler/stage1_l0/src/backend.l0`
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/c_emitter_test.l0`
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`
  - `l1/compiler/stage1_l0/tests/fixtures/typing/typing_equality_unsupported.l1`
  - `l1/compiler/stage1_l0/tests/fixtures/typing/typing_string_equality_ok.l1` (new)
  - `l1/compiler/stage1_l0/tests/fixtures/driver/string_equality_main.l1` (new)
  - `l1/docs/reference/design-decisions.md`
  - `l1/docs/roadmap.md`
- Test modules:
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/c_emitter_test.l0`
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`
- Related:
  - `l1/work/plans/features/2026-04-18-string-relational-operators-noref.md`
  - `l1/work/plans/docs/2026-04-18-l1-string-value-semantics-decision-noref.md` (this meta-plan)
- Repro:
  `make -C l1 test-stage1 TESTS="expr_types_test backend_test c_emitter_test l0c_lib_test" && make -C l1 test-all`

## Summary

`==` and `!=` over `string` operands are currently rejected by the L1 Stage 1 compiler with `TYP-0173`, even though the
runtime helper `rt_string_equals` and the emitter helper `cem_emit_string_equals_call` are already in place and already
used by the `case`-over-string lowering. This plan wires the equality path through typing and backend so that `s1 == s2`
and `s1 != s2` compile and execute with value-equality semantics, matching the behavior of `case` arms and
`std.string::eq_s`.

## Completion Notes

1. `etc_infer_binary` now accepts `string == string` and `string != string`, while mixed `string` / non-`string`
   equality still reports `TYP-0172`.
2. `be_emit_binary_op` now lowers string equality through `rt_string_equals(...)` and string inequality through
   `!rt_string_equals(...)`.
3. Regression coverage now includes a positive typing fixture, backend and emitter assertions, and a kept-C CLI/runtime
   fixture that exercises both literal and heap-built strings.
4. `l1/docs/reference/design-decisions.md` and `l1/docs/roadmap.md` now describe string equality as shipped behavior.
5. `docs/specs/compiler/diagnostic-code-catalog.md` already carried the narrowed generic `TYP-0173` wording, so no
   shared-doc edit was required in this change.

## Current State

1. `compiler/stage1_l0/src/expr_types.l0::etc_infer_binary` rejects `string == string` and `string != string` with
   `TYP-0173` ("equality not supported for type 'string' in this stage"). The rejection sits in the equality branch that
   today only allows `int`-family, `bool`, and real operands.
2. `compiler/stage1_l0/src/backend.l0` lowers `==` / `!=` via `cem_emit_binary_op("==", ...)` /
   `cem_emit_binary_op("!=", ...)`, which emits raw C `==` / `!=`. There is no string-aware dispatch on the equality
   path.
3. `compiler/stage1_l0/src/c_emitter.l0::cem_emit_string_equals_call` already exists and is exercised by
   `be_emit_case_stmt`.
4. `compiler/shared/runtime/l1_runtime.h::rt_string_equals` returns `dea_bool`, 1 on byte-equal content, 0 otherwise.
5. Fixture `tests/fixtures/typing/typing_equality_unsupported.l1` asserts that `a == b` and `a != b` for string operands
   produce two `TYP-0173` errors. Test `test_typing_equality_unsupported` in `expr_types_test.l0` asserts
   `count_diag_code(result, "TYP-0173") == 2`.

## Defaults Chosen

1. `string == string` returns `bool`, computed by `rt_string_equals`. `string != string` is the boolean negation of that
   call.
2. The typing rule requires both operands to be `string`; mixed `string`/other-type still yields `TYP-0172` (type
   mismatch), not `TYP-0173`.
3. `TYP-0173` remains a registered diagnostic but its meaning narrows to "equality not supported for this type" covering
   struct/enum/pointer-value equality, not string equality.
4. Backend lowering reuses `cem_emit_string_equals_call` for `==`. For `!=`, the backend wraps the call with the
   existing `cem_emit_unary_op("!", ...)` helper rather than introducing a second runtime helper.
5. No new runtime functions are added. No changes to ARC retain/release rules are introduced: `rt_string_equals` does
   not transfer ownership and its result is `bool`, so ARC bookkeeping is unaffected.

## Goal

1. Allow `==` and `!=` on `string` operands in the type checker, with both sides required to be `string`.
2. Lower `s1 == s2` to `rt_string_equals(s1, s2)` and `s1 != s2` to `!rt_string_equals(s1, s2)` via the existing emitter
   helpers.
3. Update the fixture set: retire the string-specific part of `typing_equality_unsupported.l1`, add a positive typing
   fixture, and add a driver fixture that exercises both operators and asserts correct runtime behavior.
4. Narrow `TYP-0173` meaning in the diagnostic-code catalog and in the test that counts string-related `TYP-0173`
   occurrences.
5. Cross-reference this change in `design-decisions.md` and move the string-equality half of the roadmap bullet from
   backlog to completed.

## Implementation Phases

### Phase 1: Typing

Extend the `==` / `!=` branch in `etc_infer_binary` so that when both operands are `string`, the operator is accepted
and yields `bool`. Reject `string` against any non-`string` operand with `TYP-0172`, matching the existing behavior for
other type mismatches.

### Phase 2: Backend / emitter

In `be_emit_binary_op` (or the equivalent dispatch function), detect `string`-typed operands on `==` / `!=` and route
through `cem_emit_string_equals_call`. For `!=`, wrap the resulting expression with `cem_emit_unary_op("!", ...)`. No
new emitter helper is required.

### Phase 3: Fixtures and tests

1. Update `typing_equality_unsupported.l1` to stop relying on string operands. If the fixture's only purpose was string
   equality, replace it with a struct-equality or enum-equality case so that `TYP-0173` still has a minimal reachable
   trigger. Update `test_typing_equality_unsupported` accordingly.
2. Add `typing_string_equality_ok.l1` exercising `s1 == s2`, `s1 != s2`, comparisons with literals, empty strings, and
   chained equality in `if` / `while` conditions. Add a corresponding pass-typing test case.
3. Add `string_equality_main.l1` as a driver/runtime fixture that compiles and runs to exit code 0, asserting
   equal/unequal literal pairs and heap-constructed pairs.
4. Add a `c_emitter_test` assertion covering the `!=` case (the existing assertion for `cem_emit_string_equals_call`
   output covers `==`).

### Phase 4: Docs

1. In `design-decisions.md`, reference the new operator support from the string-value-semantics section.
2. In `roadmap.md`, update the string-operators backlog bullet to note that equality/inequality has landed (or move the
   entry to the completed-milestones section, per the file's conventions).
3. In `docs/specs/compiler/diagnostic-code-catalog.md`, update the `TYP-0173` entry so its prose no longer implies
   string-specific rejection.

## Diagnostics

1. `TYP-0173` is retained but narrowed: it no longer fires for `string` operands. Any user-facing docs referencing it
   should be updated to reflect the narrower scope.
2. `TYP-0172` continues to fire for mixed `string` / non-`string` equality, unchanged.
3. No new diagnostic codes are introduced.

## Non-Goals

1. Ordered `string` comparison (`<`, `<=`, `>`, `>=`) — scope of the sibling plan
   `2026-04-18-string-relational-operators-noref.md`.
2. String concatenation via `+` — deferred; ARC result-ownership rules are out of scope here.
3. Any change to identity semantics. Instance equality is explicitly not exposed, per the string-value-semantics
   decision.
4. Any change to `case`-over-string lowering; it already uses the correct helper.
5. Struct or enum value equality; those remain rejected with `TYP-0173` under the narrowed meaning.

## Verification Criteria

1. `make -C l1 test-stage1 TESTS="expr_types_test"` passes, including the new positive typing case and the updated
   `TYP-0173` test.
2. `make -C l1 test-stage1 TESTS="c_emitter_test"` passes, including a `!=`-lowering helper assertion.
3. `make -C l1 test-stage1 TESTS="backend_test"` passes, including lowering coverage for `==` and `!=` on string
   operands.
4. `make -C l1 test-all` passes end-to-end.
5. The new driver fixture compiles, runs, and keeps generated C under `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`.
6. `design-decisions.md`, `roadmap.md`, and the diagnostic-code catalog reflect the narrowed `TYP-0173` meaning and the
   landed operator support.
