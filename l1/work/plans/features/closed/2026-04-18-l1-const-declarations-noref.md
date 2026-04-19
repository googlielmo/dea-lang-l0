# Feature Plan

## Add L1 const declarations

- Date: 2026-04-18
- Status: Completed
- Title: Add L1 const declarations
- Kind: Feature
- Severity: Medium
- Stage: L1
- Subsystem: Lexer / parser / expression typing / constant evaluator / C emitter
- Modules:
  - `l1/compiler/stage1_l0/src/tokens.l0`
  - `l1/compiler/stage1_l0/src/ast.l0`
  - `l1/compiler/stage1_l0/src/ast_printer.l0`
  - `l1/compiler/stage1_l0/src/parser/decl.l0`
  - `l1/compiler/stage1_l0/src/parser/stmt.l0`
  - `l1/compiler/stage1_l0/src/expr_types.l0`
  - `l1/compiler/stage1_l0/src/signatures.l0`
  - `l1/compiler/stage1_l0/src/backend.l0`
  - `l1/compiler/stage1_l0/src/c_emitter.l0`
  - `l1/compiler/stage1_l0/src/analysis.l0`
- Test modules:
  - `l1/compiler/stage1_l0/tests/lexer_test.l0`
  - `l1/compiler/stage1_l0/tests/parser_test.l0`
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/c_emitter_test.l0`
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`
- Related:
  - `l1/docs/roadmap.md`
  - `l1/docs/reference/design-decisions.md`
  - `l1/work/plans/features/2026-04-17-l1-let-non-constant-initializers-noref.md`
  - `docs/specs/compiler/diagnostic-code-catalog.md`
- Repro:
  `make -C l1 test-stage1 TESTS="lexer_test parser_test expr_types_test backend_test c_emitter_test l0c_lib_test" && make -C l1 test-stage1 && make -C l1 check-examples`

## Summary

L1 today exposes only `let` declarations, which must currently bind compile-time constant initializers at top level.
This plan introduces a dedicated `const` declaration form whose contract is that the initializer must be evaluable at
compile time and whose binding is statically known and non-assignable. `const` coexists with the non-constant-`let` work
(see the related active plan) by splitting the two intents: `let` for run-time-initialized bindings, `const` for
compile-time-known bindings exposed in typing, folding, and the generated C ABI as true compile-time constants.

## Completion Notes

1. `const` is now a real lexer keyword (`TT_CONST`) and parses as `const NAME: T = EXPR;` at top level with dedicated
   parser diagnostics for missing type annotations, missing initializers, and attempted block-local use.
2. Top-level `const` bindings reuse the existing top-level binding pipeline via a binding-level `is_const` flag, while
   signature resolution now emits `SIG-0200` when a `const` initializer falls outside the existing static-initializer
   subset.
3. The type checker now emits `TYP-0360` for assignment to top-level `const` bindings, including field assignment
   through value-typed `const` bases, and generated C now lowers `const` bindings as `static const` declarations.
4. Regression coverage now includes lexer, parser, typing, backend, emitter, and kept-C runtime tests plus dedicated
   typing and driver fixtures for successful `const` use, non-constant initializers, and assignment rejection.
5. `l1/docs/reference/grammar.md`, `l1/docs/reference/design-decisions.md`, `l1/docs/roadmap.md`, and
   `docs/specs/compiler/diagnostic-code-catalog.md` now describe shipped top-level `const` behavior. Block-local `const`
   remains deferred and is explicitly rejected with `PAR-0263`.
6. Shipped `const`-specific diagnostics now live in dedicated reserved blocks for future follow-up work: `PAR-0260` to
   `PAR-0279`, `SIG-0200` to `SIG-0219`, and `TYP-0360` to `TYP-0379`.

## Current State

1. Top-level `let` declarations today require compile-time-evaluable initializers. The in-flight
   `2026-04-17-l1-let-non-constant-initializers-noref` plan lifts that restriction so `let` can carry run-time
   initializers through a module-init path.
2. There is no `const` keyword in `l1/compiler/stage1_l0/src/tokens.l0` and no constant-binding declaration in the
   parser or AST.
3. The constant evaluator used by `let` and by match-arm literals already folds integer, float, bool, and string literal
   expressions; there is no reusable "this expression is constant" predicate surfaced in typing.
4. The C emitter models top-level `let` bindings as mutable C globals. There is no `static const` emission path today.

## Defaults Chosen

1. `const NAME: T = EXPR;` is the syntactic form, mirroring `let`.
2. `const` is a reserved keyword added to the lexer; using it as an identifier becomes a lexer/parser error.
3. The initializer of a `const` must be evaluable by the existing constant evaluator, without exception. Non-constant
   expressions are rejected with a dedicated diagnostic rather than falling back to a module-init path.
4. `const` bindings are non-assignable. Any attempt to assign to, `drop`, or take an address of them is a typing error.
5. `const` bindings have the same scoping rules as `let`: module-level and (optionally) block-local. Block-local `const`
   is in scope for this plan only if it can be implemented without compiler changes beyond a simple
   mutability/assignability bit; otherwise it is deferred to a follow-up.
6. Public top-level `const` bindings are exposed in the generated C as `static const T dea_<module>_<name>;` (or the
   current ABI equivalent for `let` with a `const` qualifier), keeping the `dea_*` ABI policy.
7. `const` is distinct from a future `constexpr`-like facility: it does not introduce compile-time function evaluation
   beyond what the existing folder supports.

## Goal

1. Add `const` as a keyword and a top-level (and optionally block-local) declaration form.
2. Enforce compile-time-evaluable initializers with a clear diagnostic.
3. Enforce non-assignability in the type checker and drop/addressing rules.
4. Emit `const` bindings as true C constants, distinct from mutable `let` globals.
5. Update relevant docs (roadmap, design-decisions reference) to reflect the new surface.

## Implementation Phases

### Phase 1: Reserve the keyword

Add `TT_CONST` to `tokens.l0`, wire it into the lexer keyword table, and add a reserved-word test in `lexer_test.l0`.
Confirm no existing source in `l1/` uses `const` as an identifier.

### Phase 2: Parser and AST

Add a `const` declaration node, parsed alongside `let` in `parser/decl.l0`. Require an explicit type annotation; do not
permit `const` without a type (to keep folding deterministic). Require an initializer. Produce a top-level-only
diagnostic initially; relax to block-local only if Phase 4 confirms the simple path.

### Phase 3: Typing and assignability

Extend the declaration/binding representation with a mutability bit. Reject assignment to `const` bindings, reject
`drop` of a `const`, and reject `&` address-of in contexts that imply mutability. Register the new diagnostic codes in
`docs/specs/compiler/diagnostic-code-catalog.md` before landing.

### Phase 4: Constant evaluator

Reuse the existing constant evaluator. If the evaluator cannot fold the initializer, emit a dedicated
`const`-initializer diagnostic rather than the current generic folding error, so the user sees why `const` rejects an
expression that `let` would accept under the run-time-init path.

### Phase 5: Backend and C emission

Emit public top-level `const` bindings as `static const T ...` in the generated C translation unit. Ensure values appear
inline at use sites where the folder already collapses them, consistent with today's `let` constant path.

### Phase 6: Docs and migration

Update `l1/docs/reference/design-decisions.md` with the `const` vs `let` split. Decide whether any existing `let`
bindings in the stdlib should become `const` and make those changes in the same plan's landing commit to keep the
example surface consistent with the new recommendation.

### Phase 7: Regression coverage

Add tests in:

- `lexer_test.l0` — keyword tokenization and identifier rejection
- `parser_test.l0` — `const` accepted, missing type rejected, missing initializer rejected
- `expr_types_test.l0` — assignment to `const` rejected, drop/addressing rejected, initializer-must-be-constant
  diagnostic
- `l0c_lib_test.l0` — an end-to-end fixture exercising a `const` used at run time

## Non-Goals

- compile-time function evaluation beyond the existing folder
- `const` on function parameters or return types
- `const` methods or immutable-struct semantics
- pub/visibility changes beyond what `let` exposes today
- interaction with future generics, lambdas, or `hash(T)` — tracked separately

## Verification Criteria

1. `make -C l1 test-stage1 TESTS="lexer_test parser_test expr_types_test"` passes.
2. `make -C l1 test-stage1 TESTS="l0c_lib_test"` passes with the new runtime fixture.
3. `make -C l1 test-stage1` and `make -C l1 check-examples` both pass.
4. `const` initializers that cannot be folded emit the dedicated diagnostic, not the generic folding error.
5. Any newly registered diagnostic codes appear in `docs/specs/compiler/diagnostic-code-catalog.md`.
6. `l1/docs/reference/design-decisions.md` documents the `const` vs `let` split.
