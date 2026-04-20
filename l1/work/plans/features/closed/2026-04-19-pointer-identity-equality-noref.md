# Feature Plan

## Implement pointer identity equality operators

- Date: 2026-04-19
- Status: Completed
- Title: Implement pointer identity equality operators
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
  - `l1/compiler/stage1_l0/tests/fixtures/typing/typing_pointer_identity_ok.l1` (new)
  - `l1/compiler/stage1_l0/tests/fixtures/typing/typing_pointer_identity_err.l1` (new)
  - `l1/compiler/stage1_l0/tests/fixtures/driver/pointer_identity_main.l1` (new)
  - `l1/docs/reference/design-decisions.md`
  - `l1/docs/roadmap.md`
- Test modules:
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/c_emitter_test.l0`
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`
- Related:
  - `l1/docs/reference/design-decisions.md`
  - `l1/work/plans/features/2026-04-19-nullable-identity-equality-noref.md`
  - `l1/work/plans/features/closed/2026-04-18-string-equality-operators-noref.md`
  - `docs/specs/compiler/diagnostic-code-catalog.md`
- Repro:
  `make -C l1 test-stage1 TESTS="expr_types_test backend_test c_emitter_test l0c_lib_test" && make -C l1 test-all`

## Summary

L1's grammar admits `==` and `!=` between arbitrary operands (`grammar.md::EqualityExpr`), but the current type checker
only accepts `int`-family, `bool`, real, and `string` operands, plus the `null` vs pointer/nullable null-check branch.
Two same-type `T*` values (for example `let t1: T* = new T(); let t2: T* = new T(); if (t1 == t2) {...}`) are rejected
with `TYP-0173` "equality not supported for type 'T\*' in this stage". This plan adds reference-identity equality on
same-type non-nullable pointer operands.

Pointer identity is the natural defined semantic for `T*`: two `T*` values are language-equivalent when they refer to
the same runtime object, and the underlying C representation already makes `==` / `!=` on pointers well-defined. This is
distinct from `string` identity (§15 of `design-decisions.md`), where content equality is the committed semantic
precisely because the backend is free to deduplicate or re-home string storage; ordinary heap pointers do not share that
constraint.

The nullable-pointer case (`T*?`) and the cross-form case (`T* == T*?` with the same inner `T`) are out of scope here
and are handled by the companion nullable-identity plan.

## Current State

1. `compiler/stage1_l0/src/expr_types.l0::etc_infer_binary` rejects `p1 == p2` for same-type `T*` operands with
   `TYP-0173`. The equality branch accepts `int`-family, `bool`, real, and `string` via `etc_is_int`, `etc_is_bool`,
   `etc_is_real`, `etc_is_string`, plus a narrow null-check branch for `NullType` vs `TY_POINTER` / `TY_NULLABLE`.
2. `compiler/stage1_l0/src/backend.l0` lowers `==` / `!=` via `cem_emit_binary_op("==", ...)` /
   `cem_emit_binary_op("!=", ...)`, which emits raw C `==` / `!=`. The null-check case already relies on this path for
   pointer-vs-`null` comparisons.
3. `compiler/stage1_l0/tests/fixtures/typing/typing_equality_unsupported.l1` asserts that two `Pair` struct values
   rejecting `==` / `!=` yields `TYP-0173`. No fixture currently asserts pointer-vs-pointer rejection, so the new
   positive fixtures can land without retiring existing negatives.
4. `l1/docs/reference/design-decisions.md` §7 documents the pointer model (`T*`, `T*?`, dereference, auto-deref) but is
   silent on pointer equality. §15 explicitly rules out `string` identity equality, but that rationale does not
   generalize to ordinary heap pointers.

## Defaults Chosen

1. `p1 op p2` for `op` in `{ ==, != }` is accepted when both operands have the same pointer type `T*` (including
   `void*`), and yields `bool`. The semantic is reference identity: two values compare equal if and only if they point
   to the same runtime object.
2. Typing strictness: the two operand types must be the same `T*`, not merely both pointers. `int*` vs `long*`, `T*` vs
   `U*`, and `T*` vs `void*` (when `T` is not `void`) are rejected with the existing `TYP-0172` mismatch diagnostic.
3. Null-check interaction: `p == null` and `null == p` for `T*` unchanged. Pointer-vs-pointer identity is an independent
   rule; it does not widen or narrow the null-check branch.
4. Nullable interaction: `T*? == T*?`, `T* == T*?`, and related forms stay rejected by this plan. They belong to the
   companion nullable-identity plan to keep the surface per plan narrow and reviewable.
5. Ordered comparisons on pointers (`<`, `<=`, `>`, `>=`) remain rejected. Address ordering is host-defined and has no
   well-defined L1 meaning; enforcing this keeps pointer comparison semantics equal to identity only.
6. Backend lowering emits raw C `==` / `!=` on pointer operands. No runtime helper, no null-check wrapping, no
   representation widening. This is a thin typing-only gate over existing emitter behavior.
7. No new diagnostic codes are introduced. `TYP-0173` narrows further: it no longer fires for same-type non-nullable
   pointer operands, but continues to cover struct and enum value equality.

## Goal

1. Allow `==` and `!=` on two same-type `T*` operands in `etc_infer_binary`, yielding `bool`.
2. Keep backend lowering at raw C `==` / `!=`; no new emitter helper.
3. Add a positive typing fixture, an error fixture for type-mismatched pointers, backend and emitter assertions, and a
   driver fixture that exercises identity on freshly allocated and aliased pointers.
4. Narrow the `TYP-0173` description in the shared diagnostic catalog to reflect the new scope.
5. Record pointer identity equality and its intentional contrast with string identity in
   `l1/docs/reference/design-decisions.md` §7.
6. Update `l1/docs/roadmap.md` to list this plan under `Active standalone plans` and add a cross-reference from the
   relevant backlog bullet.

## Implementation Phases

### Phase 1: Typing

Extend the `==` / `!=` branch in `etc_infer_binary` (around `expr_types.l0:2520-2555`) so that when both operands are
`TY_POINTER` with the same pointee type, the operator is accepted and yields `bool`. Mismatched pointer operand types
continue to fall through to `TYP-0172`. Pointer operands with ordered operators (`<`, `<=`, `>`, `>=`) continue to fail
the current relational branch with `TYP-0170`, unchanged by this plan.

Update the equality branch's final fallback so the error taxonomy stays clean:

- same-type non-nullable pointer operands: accept.
- mismatched pointer types: `TYP-0172`.
- nullable or cross-form pointer operands: still rejected (owned by the companion plan), with `TYP-0173` until that plan
  lands.

### Phase 2: Backend / emitter

No emitter changes should be required: `be_emit_binary_op` already routes non-string `==` / `!=` through
`cem_emit_binary_op("==" | "!=", lhs, rhs)`, which emits raw C pointer-compatible relational operators. Add backend and
emitter test coverage to lock in that contract, and guard against future regressions that would route pointer operands
through a string-aware dispatch.

### Phase 3: Fixtures and tests

1. Add `typing_pointer_identity_ok.l1` exercising `==` / `!=` between two `T*` locals, between a `T*` local and a
   function-returned `T*`, between two `void*` values, and in `if` / `while` conditions. Add a corresponding pass-typing
   test case in `expr_types_test.l0`.
2. Add `typing_pointer_identity_err.l1` covering mismatched pointer types (`int*` vs `long*`, `T*` vs `U*`, non-`void`
   `T*` vs `void*`). Add a corresponding error-count test case asserting `TYP-0172` diagnostics.
3. Add `pointer_identity_main.l1` as a driver/runtime fixture that compiles, runs, and exits 0 while asserting
   `p1 == p1` (self-identity), `p1 != p2` (two fresh `new T()` values), and `alias == p1` (explicit alias).
4. Add a `backend_test` assertion covering the lowering of both operators on pointer operands.
5. Extend `c_emitter_test` to assert that pointer equality lowers through `cem_emit_binary_op`, not through
   `cem_emit_string_equals_call`.

### Phase 4: Docs

1. In `l1/docs/reference/design-decisions.md`, extend §7 Pointer and Ownership Policy with a short paragraph that:
   - records that `==` and `!=` on same-type `T*` operands compare by reference identity,
   - contrasts this with §15's explicit refusal of `string` identity equality,
   - explicitly notes that ordered pointer comparisons remain rejected.
2. In `docs/specs/compiler/diagnostic-code-catalog.md`, narrow the `TYP-0173` wording so it no longer implies that
   pointer operands are rejected. The code remains for struct and enum value equality.
3. In `l1/docs/roadmap.md`, list this plan under `Active standalone plans`, cross-reference it from the relevant
   `Language core` backlog bullet, and refresh the `Version:` metadata.

## Diagnostics

1. `TYP-0172` continues to fire for mismatched pointer operand types, unchanged.
2. `TYP-0173` narrows: it no longer fires for same-type non-nullable pointer operands.
3. `TYP-0170` continues to fire for ordered pointer comparisons, unchanged.
4. No new diagnostic codes are introduced.

## Non-Goals

1. `T*? == T*?`, `T*? == T*`, `T* == T*?`, or any nullable-pointer form beyond the existing `null` check — owned by the
   companion plan `2026-04-19-nullable-identity-equality-noref.md`.
2. Ordered pointer comparisons (`<`, `<=`, `>`, `>=`). Address ordering is intentionally not defined in L1.
3. Pointer arithmetic, address-of (`&`), or pointer indexing. These remain part of the deferred unsafe/raw-pointer
   surface tracked in the roadmap.
4. Struct or enum value equality; those remain rejected with `TYP-0173` under the narrowed meaning.
5. Any change to `string` identity policy (§15). String equality remains strictly value-based.
6. Compiler-generated `hash(T)` or any relationship with `sys.hash`. That is tracked separately in the backlog.

## Verification Criteria

1. `make -C l1 test-stage1 TESTS="expr_types_test"` passes, including the new positive and negative typing cases.
2. `make -C l1 test-stage1 TESTS="c_emitter_test"` passes, including the pointer-lowering guard assertion.
3. `make -C l1 test-stage1 TESTS="backend_test"` passes, including lowering coverage for `==` and `!=` on pointer
   operands.
4. `make -C l1 test-stage1 TESTS="l0c_lib_test"` passes, including the new `pointer_identity_main.l1` driver fixture.
5. `make -C l1 test-all` passes end-to-end.
6. `l1/docs/reference/design-decisions.md`, `l1/docs/roadmap.md`, and the shared diagnostic-code catalog reflect the
   landed pointer-identity equality rule and the narrowed `TYP-0173` meaning.
