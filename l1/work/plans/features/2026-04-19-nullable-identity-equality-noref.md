# Feature Plan

## Implement strict T? vs T? equality

- Date: 2026-04-19
- Status: Draft
- Title: Implement strict T? vs T? equality
- Kind: Feature
- Severity: Medium
- Stage: L1
- Subsystem: Typing / backend / C emission / runtime / tests / docs
- Modules:
  - `l1/compiler/stage1_l0/src/expr_types.l0`
  - `l1/compiler/stage1_l0/src/backend.l0`
  - `l1/compiler/stage1_l0/src/c_emitter.l0`
  - `l1/compiler/shared/runtime/l1_runtime.h`
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/c_emitter_test.l0`
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`
  - `l1/compiler/stage1_l0/tests/fixtures/typing/typing_nullable_identity_ok.l1` (new)
  - `l1/compiler/stage1_l0/tests/fixtures/typing/typing_nullable_identity_err.l1` (new)
  - `l1/compiler/stage1_l0/tests/fixtures/driver/nullable_identity_main.l1` (new)
  - `l1/docs/reference/design-decisions.md`
  - `l1/docs/roadmap.md`
- Test modules:
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/c_emitter_test.l0`
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`
- Related:
  - `l1/docs/reference/design-decisions.md`
  - `l1/work/plans/features/2026-04-19-pointer-identity-equality-noref.md`
  - `l1/work/plans/features/closed/2026-04-18-string-equality-operators-noref.md`
  - `docs/specs/compiler/diagnostic-code-catalog.md`
- Repro:
  `make -C l1 test-stage1 TESTS="expr_types_test backend_test c_emitter_test l0c_lib_test" && make -C l1 test-all`

## Summary

L1's nullable types (`T?`) currently cannot be compared for equality unless one side is the literal `null`. Two same-
type nullable values such as `let a: int? = 5; let b: int? = 5; a == b` are rejected with `TYP-0173`, even though the
grammar admits the expression and every underlying inner-type equality rule is already supported.

This plan adds strict `T? == T?` equality: the operator is accepted when both operand types are the same `T?`, and the
semantics follow "three-valued on the null bit, then inner-T equality on the payload". The strictness is deliberate:
`T? == T` and `T == T?` remain rejected even when `T` supports `==`. Closing that gap would require either silent
lift-to-nullable or silent unwrap, both of which would erode the explicit-nullability contract L1 inherited from L0 (§4
Nullability policy). Users who want to compare across nullable and non-nullable forms must cast explicitly:
`x as T? == y` or `x == y as T`, depending on the side whose type they want to move.

This plan lands after the companion pointer-identity plan (`2026-04-19-pointer-identity-equality-noref.md`) so the
nullable-pointer subcase `T*? == T*?` inherits the same-type identity rule consistently.

## Current State

1. `compiler/stage1_l0/src/expr_types.l0::etc_infer_binary` only accepts equality operands that are same-type `int`-
   family, `bool`, real, or `string`, plus integer-widening pairs and the `null` vs pointer/nullable null-check branch
   (`expr_types.l0:2520-2555`). Any `T? == T?` or `T? == T` falls through to `TYP-0173` or `TYP-0172`.
2. `compiler/stage1_l0/src/backend.l0` lowers `==` / `!=` via `cem_emit_binary_op`. Nullable-pointer operands (`T*?`)
   inherit the pointer-null niche representation documented in `design-decisions.md` §8, so raw C `==` already
   implements the correct semantic. Nullable non-pointer operands (for example `int?`) are represented by the
   `dea_opt_*` wrapper form and cannot be lowered to raw C `==`.
3. `compiler/shared/runtime/l1_runtime.h` exposes `rt_string_equals` for string content equality. There is no
   per-inner-type nullable equality helper; every inner type's nullable representation must be reducible either to
   pointer-null (`T*?`) or to the `dea_opt_*` wrapper (`int?`, `bool?`, real, string).
4. `l1/docs/reference/design-decisions.md` §8 Nullability, Casts, and Introspection commits to `T?` and `null`, to
   pointer-null representation for nullable pointers, and to `l0_opt_*`-style wrappers for non-pointer nullables, but is
   silent on the equality surface for `T?`.

## Defaults Chosen

1. `a op b` for `op` in `{ ==, != }` is accepted when both operand types are the same `T?` (identical inner `T` and
   identical nullable wrapping) and yields `bool`.
2. Inner-type scope: this plan accepts `T?` where the inner `T` is any type already accepted by the existing `T == T`
   rule at plan landing time (that is, `int`-family, `bool`, real, `string`, and — once the companion plan lands —
   same-type non-nullable pointer). If `T == T` is not accepted for some inner `T` (for example struct or enum value
   equality), `T? == T?` remains rejected with `TYP-0173` under that narrowed meaning.
3. Semantics: both operands null returns `true`; exactly one operand null returns `false`; both operands non-null
   returns the result of the corresponding inner-type `T == T`. `!=` is the logical negation of the same evaluation.
4. Strictness: `T? == T`, `T == T?`, `T? == U?` (different inner types), and `T? == null` mixed forms follow these
   rules:
   - `T? == null` / `null == T?`: unchanged, still the existing null-check branch.
   - `T? == T` / `T == T?` (same inner `T`): rejected with `TYP-0172` and a message that names the mismatch; the user
     must cast with `as` to reach a same-`T?` or same-`T` pair.
   - `T? == U?` for different inner types: rejected with `TYP-0172`, same as non-nullable mismatch.
5. Ordered comparisons on `T?` (`<`, `<=`, `>`, `>=`) remain rejected in this plan. A defined three-valued ordering on
   null payloads is a separate design question; if pursued, it belongs in a follow-up plan.
6. Representation-aware backend lowering:
   - for nullable-pointer operands (`T*?`), reuse the existing raw C `==` / `!=`; the pointer-null niche already
     implements the three-valued rule correctly.
   - for nullable non-pointer operands, lower through a new emitter helper `cem_emit_opt_equals_call` that expands to an
     inline expression of the shape
     `((!a.has_value && !b.has_value) || (a.has_value && b.has_value && a.value op_inner b.value))`, where `op_inner` is
     the correct inner-type equality expression (raw C `==` for numeric and bool operands, `rt_string_equals` for
     `string?`).
7. No new runtime helper is added in this plan. `rt_string_equals` and the existing `dea_opt_*` accessor fields remain
   the only runtime touchpoints.
8. No new diagnostic codes are introduced. `TYP-0172` (mismatch) and `TYP-0173` (unsupported-in-this-stage) cover the
   new rejection cases.

## Goal

1. Allow `==` and `!=` on two same-`T?` operands in `etc_infer_binary`, yielding `bool`, for every inner `T` whose
   `T == T` rule is already accepted.
2. Add backend lowering that chooses between raw C `==` (nullable-pointer) and a new inline emitter helper
   (nullable-non-pointer) based on the representation.
3. Keep `T? == T` and `T == T?` rejected with `TYP-0172`, and document the required explicit-cast pattern in the
   design-decisions reference.
4. Add positive and negative typing fixtures, backend and emitter assertions, and a driver fixture that exercises the
   full truth table (null/null, null/non-null, non-null/null, non-null/non-null with equal and unequal payloads) for at
   least `int?`, `string?`, and `T*?`.
5. Record the strict `T? == T?` rule and the explicit-cast requirement in `l1/docs/reference/design-decisions.md` §8.
6. Update `l1/docs/roadmap.md` to list this plan under `Active standalone plans` and cross-reference it from the
   relevant backlog bullet.

## Implementation Phases

### Phase 1: Typing

Extend the `==` / `!=` branch in `etc_infer_binary` so that when both operand types are `TY_NULLABLE` with identical
inner types and the inner type's `T == T` rule is already accepted, the operator is accepted and yields `bool`. When the
inner `T == T` rule is not accepted, fall through to the existing `TYP-0173` path with a clear message that names the
unsupported inner type. When only one operand is nullable, or the inner types differ, emit `TYP-0172` with a message
that names the mismatch and, in the same-inner-type case, suggests the `as` cast.

Update helpers near the existing `_is_nullable_or_ptr` / `etc_is_*` predicates to expose "inner type of a nullable" and
"inner-type equality is accepted". Keep the existing null-check branch unchanged.

### Phase 2: Backend / emitter

1. In `be_emit_binary_op` (or equivalent dispatch), detect nullable-typed operands on `==` / `!=` and branch on inner
   representation:
   - nullable-pointer: keep `cem_emit_binary_op(op, ...)` (raw C `==` / `!=`).
   - nullable-non-pointer: call the new `cem_emit_opt_equals_call(op, lhs, rhs, inner_ty)` emitter helper.
2. In `c_emitter.l0`, introduce `cem_emit_opt_equals_call` that returns the full inline C expression, parenthesized, and
   picks the inner comparison based on `inner_ty` (raw C `==` / `!=` for numeric and bool inner types,
   `rt_string_equals(...)` for `string` inner type, and raw C `==` / `!=` for pointer inner type).
3. Keep ARC rules unchanged. The helper does not take ownership of its operands; `rt_string_equals` already returns a
   plain `dea_bool` without affecting reference counts.

### Phase 3: Fixtures and tests

1. Add `typing_nullable_identity_ok.l1` exercising `==` / `!=` on `int?`, `bool?`, `float?`, `double?`, `string?`, and
   `T*?`, for all four null/non-null combinations, including comparisons with `null` (existing null-check branch should
   still work), and in `if` / `while` conditions.
2. Add `typing_nullable_identity_err.l1` covering mixed `T? == T`, `T == T?`, and mismatched inner-type `T? == U?`
   cases. Assert `TYP-0172` diagnostics and that the messages name the mismatch.
3. Add `nullable_identity_main.l1` as a driver/runtime fixture that compiles, runs, and exits 0 while asserting the full
   truth table for each representative inner type (numeric, string, and pointer).
4. Add `backend_test` and `c_emitter_test` assertions covering both the nullable-pointer lowering (raw C `==`) and the
   nullable-non-pointer lowering through `cem_emit_opt_equals_call`.

### Phase 4: Docs

1. In `l1/docs/reference/design-decisions.md` §8, add a short subsection describing:
   - the strict same-`T?` equality rule,
   - the refusal of `T? == T` and `T == T?` without an explicit cast, and the cast idioms that fix it,
   - the reuse of pointer-null representation for `T*?` equality, deferring to the pointer-identity plan's §7 note.
2. In `docs/specs/compiler/diagnostic-code-catalog.md`, adjust the `TYP-0172` / `TYP-0173` wording so the narrowed
   meanings are correct after both this plan and the companion pointer-identity plan land.
3. In `l1/docs/roadmap.md`, list this plan under `Active standalone plans`, cross-reference the relevant backlog bullet,
   and refresh the `Version:` metadata.

## Diagnostics

1. `TYP-0172` fires for `T? vs T`, `T vs T?`, and `T? vs U?` (different inner types). Messages should name the mismatch
   and mention the `as` cast option when both sides share an inner `T`.
2. `TYP-0173` narrows further: it fires for `T? == T?` only when the inner `T == T` rule itself is not accepted (today
   this covers struct and enum inner types).
3. `TYP-0170` continues to fire for ordered `T?` comparisons, unchanged.
4. No new diagnostic codes are introduced.

## Non-Goals

1. Implicit `T -> T?` or `T? -> T` conversion for equality. The explicit-cast requirement is the whole point of the
   strictness rule.
2. Ordered comparisons on `T?` (`<`, `<=`, `>`, `>=`). Three-valued ordering on null payloads is a separate design
   question, not in scope here.
3. Equality for nullable structs or nullable enums (`Point?`, `Color?`). Those remain rejected with the narrowed
   `TYP-0173` until `T == T` is extended for those kinds in a later plan.
4. Any change to the pointer-null niche representation in §8. This plan assumes the representation and only adds typing
   and lowering on top of it.
5. Any change to `string` identity policy (§15). String equality remains value-based.
6. Compiler-generated `hash(T?)`. Tracked separately in the backlog.

## Verification Criteria

1. `make -C l1 test-stage1 TESTS="expr_types_test"` passes, including the new positive and negative typing cases.
2. `make -C l1 test-stage1 TESTS="c_emitter_test"` passes, including `cem_emit_opt_equals_call` output assertions.
3. `make -C l1 test-stage1 TESTS="backend_test"` passes, including lowering coverage for `T*?` and nullable non-pointer
   operands.
4. `make -C l1 test-stage1 TESTS="l0c_lib_test"` passes, including the new `nullable_identity_main.l1` driver fixture.
5. `make -C l1 test-all` passes end-to-end.
6. `l1/docs/reference/design-decisions.md`, `l1/docs/roadmap.md`, and the shared diagnostic-code catalog reflect the
   implemented strict `T? == T?` rule and the narrowed `TYP-0172` / `TYP-0173` meanings.
