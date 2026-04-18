# Feature Plan

## Land string relational comparison operators

- Date: 2026-04-18
- Status: Completed
- Title: Land string relational comparison operators
- Kind: Feature
- Severity: Medium
- Stage: L1
- Subsystem: Typing / backend / C emission / tests / docs
- Modules:
  - `l1/compiler/stage1_l0/src/expr_types.l0`
  - `l1/compiler/stage1_l0/src/backend.l0`
  - `l1/compiler/stage1_l0/src/c_emitter.l0`
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/c_emitter_test.l0`
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`
  - `l1/compiler/stage1_l0/tests/fixtures/typing/typing_string_relational_ok.l1` (new)
  - `l1/compiler/stage1_l0/tests/fixtures/typing/typing_string_relational_err.l1` (new)
  - `l1/compiler/stage1_l0/tests/fixtures/driver/string_relational_main.l1` (new)
  - `l1/docs/reference/design-decisions.md`
  - `l1/docs/roadmap.md`
- Test modules:
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/c_emitter_test.l0`
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`
- Related:
  - `l1/work/plans/features/closed/2026-04-18-string-equality-operators-noref.md`
  - `l1/work/plans/docs/2026-04-18-l1-string-value-semantics-decision-noref.md` (meta-plan)
- Repro:
  `make -C l1 test-stage1 TESTS="expr_types_test backend_test c_emitter_test l0c_lib_test" && make -C l1 test-all`

## Summary

`<`, `<=`, `>`, `>=` over `string` operands are currently rejected by the L1 Stage 1 compiler as non-numeric
(`TYP-0170`). `rt_string_compare` already exists in the runtime and returns a three-valued `int` result. This plan wires
the relational path through typing and backend so that lexicographic byte-wise string comparisons compile and execute
with the semantics documented in the string-value-semantics decision.

This plan should land after, or alongside, the equality plan (`2026-04-18-string-equality-operators-noref.md`). It does
not depend on the equality plan landing first, but sharing review and emitter-test coverage is efficient.

## Completion Notes

1. `etc_infer_binary` now accepts `string < <= > >= string` and still reports `TYP-0170` for mixed `string` /
   non-`string` relational operands.
2. `cem_emit_string_compare_call` now lowers ordered string comparisons as `(rt_string_compare(lhs, rhs) op 0)`, and
   `be_emit_binary_op` routes all four relational operators through that helper for `string` operands.
3. Regression coverage now includes a positive typing fixture, a mixed-operand typing error fixture, backend and emitter
   assertions, and a kept-C CLI/runtime fixture that exercises empty strings, prefix ordering, equality via `<=` / `>=`,
   and heap-built strings.
4. `l1/docs/reference/design-decisions.md` and `l1/docs/roadmap.md` now describe ordered string comparison as shipped
   behavior, and this plan is closed under `l1/work/plans/features/closed/`.

## Current State

1. `compiler/stage1_l0/src/expr_types.l0::etc_infer_binary` processes `<` / `<=` / `>` / `>=` in the numeric-operand
   branch and rejects `string` operands with `TYP-0170`.
2. `compiler/stage1_l0/src/backend.l0` lowers relational operators via `cem_emit_binary_op(op, ...)`, emitting raw C
   relational operators. There is no string-aware dispatch.
3. `compiler/shared/runtime/l1_runtime.h::rt_string_compare` returns `dea_int`: `0` on equality, negative if `a < b`,
   positive if `a > b`. The implementation is byte-wise via `memcmp` with length fallback.
4. No emitter helper exists today for string-vs-string relational lowering; `cem_emit_string_equals_call` covers
   equality only.

## Defaults Chosen

1. `s1 op s2` for `op` in `{ <, <=, >, >= }` returns `bool` and is computed as `rt_string_compare(s1, s2) op 0`.
2. The typing rule requires both operands to be `string`; mixed `string`/other-type yields `TYP-0170` (or `TYP-0172`
   depending on where the existing mismatch diagnostic lives for these operators) — the existing behavior for type
   mismatches is preserved.
3. A new emitter helper `cem_emit_string_compare_call(op: string, lhs: string, rhs: string) -> string` is introduced,
   returning the full C expression `(rt_string_compare(lhs, rhs) op 0)`. This mirrors the style of
   `cem_emit_string_equals_call`.
4. No new runtime functions are added. `rt_string_compare` remains the single source of comparison truth.
5. Byte-wise lexicographic ordering (what `rt_string_compare` already implements) is the committed semantic.
   Locale-aware ordering is explicitly out of scope; if ever needed, it belongs in a `std.text` or `std.locale` library
   layer, not as an operator semantic change.

## Goal

1. Allow `<`, `<=`, `>`, `>=` on `string` operands in the type checker, with both sides required to be `string`,
   yielding `bool`.
2. Lower each relational operator on strings to `rt_string_compare(s1, s2) op 0` via a new
   `cem_emit_string_compare_call` helper.
3. Add positive typing fixtures, backend lowering coverage, and a driver fixture exercising ordering with
   distinct-length prefixes, empty strings, and both sides of equality.
4. Cross-reference the new support in `design-decisions.md` and update `roadmap.md`.

## Implementation Phases

### Phase 1: Typing

Extend the relational branch in `etc_infer_binary` so that `string`/`string` operand pairs are accepted for `<`, `<=`,
`>`, `>=` and yield `bool`. Preserve existing mismatch diagnostics for non-matched type pairs.

### Phase 2: Emitter helper

Add `cem_emit_string_compare_call` to `c_emitter.l0`. Signature:
`func cem_emit_string_compare_call(op: string, lhs: string, rhs: string) -> string`. Output shape:
`(rt_string_compare(lhs, rhs) op 0)` with balanced parentheses consistent with the surrounding emitter style. Add a
dedicated `c_emitter_test` assertion.

### Phase 3: Backend dispatch

In the relational-operator lowering path, detect `string`-typed operands and route through the new helper with the
operator spelling preserved. Other typed relational paths remain unchanged.

### Phase 4: Fixtures and tests

1. Add `typing_string_relational_ok.l1` exercising all four operators in `return`, `if`, and `while` contexts.
2. Add `string_relational_main.l1` as a driver/runtime fixture that compiles and runs to exit code 0, covering: equal
   strings, prefix-vs-superstring ordering, empty string against non-empty, and mixed literal/heap operands.
3. Extend `backend_test.l0` with lowering assertions for each operator on string operands.
4. Ensure `TYP-0170` test cases that asserted rejection of `string < int` still pass unchanged (type-mismatch rejection
   remains in effect for mixed operands).

### Phase 5: Docs

1. In `design-decisions.md`, extend the string-value-semantics section to note that ordering is byte-wise lexicographic
   via `rt_string_compare`, consistent with `std.string::cmp_s`.
2. In `roadmap.md`, update the string-operators backlog bullet to mark relational comparison as landed (or move to
   completed milestones per file convention).

## Diagnostics

1. No new diagnostic codes are introduced.
2. `TYP-0170` continues to fire for mixed `string` / non-`string` relational comparisons.

## Non-Goals

1. Equality / inequality on `string` — sibling plan `2026-04-18-string-equality-operators-noref.md`.
2. String concatenation via `+` — deferred.
3. Locale-aware or Unicode-aware collation. The committed semantic is byte-wise lexicographic.
4. Any change to the existing `std.string::cmp_s` wrapper; it already forwards to `rt_string_compare`.

## Verification Criteria

1. `make -C l1 test-stage1 TESTS="expr_types_test"` passes with the new positive typing fixture.
2. `make -C l1 test-stage1 TESTS="c_emitter_test"` passes with the new helper assertion.
3. `make -C l1 test-stage1 TESTS="backend_test"` passes with lowering coverage for all four relational operators.
4. `make -C l1 test-all` passes end-to-end.
5. The new driver fixture compiles, runs, and keeps generated C under `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`.
6. `design-decisions.md` and `roadmap.md` reflect the landed feature.
