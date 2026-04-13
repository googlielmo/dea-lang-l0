# Feature Plan

## Add `uint`, `long`, and `ulong` to L1 through opaque bigint literals

- Date: 2026-04-13
- Status: Draft
- Title: Add `uint`, `long`, and `ulong` to L1 through opaque bigint literals
- Kind: Feature
- Severity: High
- Stage: 1
- Subsystem: Lexer / parser / AST / typing / C emission / runtime integer helpers
- Modules:
  - `compiler/stage1_l0/src/tokens.l0`
  - `compiler/stage1_l0/src/parser/shared.l0`
  - `compiler/stage1_l0/src/parser/expr.l0`
  - `compiler/stage1_l0/src/parser/stmt.l0`
  - `compiler/stage1_l0/src/ast.l0`
  - `compiler/stage1_l0/src/ast_printer.l0`
  - `compiler/stage1_l0/src/signatures.l0`
  - `compiler/stage1_l0/src/types.l0`
  - `compiler/stage1_l0/src/type_resolve.l0`
  - `compiler/stage1_l0/src/expr_types.l0`
  - `compiler/stage1_l0/src/backend.l0`
  - `compiler/stage1_l0/src/c_emitter.l0`
  - `compiler/shared/runtime/l1_runtime.h`
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `compiler/stage1_l0/tests/parser_test.l0`
  - `compiler/stage1_l0/tests/type_resolve_test.l0`
  - `compiler/stage1_l0/tests/expr_types_test.l0`
  - `compiler/stage1_l0/tests/c_emitter_test.l0`
  - `compiler/stage1_l0/tests/backend_test.l0`
  - `docs/reference/design-decisions.md`
  - `docs/specs/compiler/diagnostic-code-catalog.md`
- Test modules:
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `compiler/stage1_l0/tests/parser_test.l0`
  - `compiler/stage1_l0/tests/type_resolve_test.l0`
  - `compiler/stage1_l0/tests/expr_types_test.l0`
  - `compiler/stage1_l0/tests/c_emitter_test.l0`
  - `compiler/stage1_l0/tests/backend_test.l0`
- Related:
  - `l1/work/plans/features/closed/2026-04-04-l1-small-int-builtins-on-dea-abi-noref.md`
  - `l1/work/plans/features/closed/2026-04-10-l1-numeric-literal-lexer-groundwork-noref.md`
- Repro: `make test-stage1 TESTS="lexer_test parser_test type_resolve_test expr_types_test c_emitter_test backend_test"`

## Summary

L1 should complete the implemented fixed-width integer builtin family by adding `uint`, `long`, and `ulong` on top of
the already implemented `tiny`, `byte`, `short`, `ushort`, and `int` types.

Unlike the small-integer tranche, this work cannot rely only on `TT_INT` / `EX_INT`. The Stage 1 compiler is written in
L0, and L0 cannot express unsigned 32-bit or 64-bit integer values natively. The existing lexer already emits
`TT_BIGINT(text, base)` for integer literals outside signed 32-bit `int`; this feature should carry that opaque literal
representation through the parser, AST, type checker, and C backend without trying to evaluate those values in L0.

The emitted C and runtime boundary own the actual `uint`, `long`, and `ulong` arithmetic, cast, range, overflow, and
underflow behavior.

## Current State

1. `compiler/stage1_l0/src/tokens.l0` reserves `uint`, `long`, and `ulong` as `TT_FUTURE_EXTENSION`.
2. `compiler/stage1_l0/src/lexer.l0` already emits `TT_BIGINT(text, base)` when an integer literal does not fit in
   signed 32-bit `int`.
3. The bigint token payload is prefix-stripped, sign-inclusive, and lowercase for hexadecimal digits; it may preserve
   leading zeros.
4. `compiler/stage1_l0/src/parser/expr.l0` only consumes `TT_INT` into `EX_INT`, so bigint literals are not yet valid
   expressions.
5. `compiler/stage1_l0/src/ast.l0` has `EX_INT` but no `EX_BIGINT`; normal expression parsing also discards base
   information for non-decimal `TT_INT` literals after parsing them to native `int`.
6. The type layer, expression checker, backend, and C emitter only treat `{tiny, byte, short, ushort, int}` as the
   implemented integer family.
7. `compiler/shared/runtime/l1_runtime.h` already defines `dea_uint`, `dea_long`, and `dea_ulong`, but the Stage 1
   frontend and backend do not expose those builtins yet.

## Defaults Chosen

01. `uint` is 32-bit unsigned and lowers to `dea_uint`.
02. `long` is 64-bit signed and lowers to `dea_long`.
03. `ulong` is 64-bit unsigned and lowers to `dea_ulong`.
04. `TT_INT` literals keep the existing `EX_INT` path and native `int` payload.
05. `TT_BIGINT` literals parse into a new `EX_BIGINT` node.
06. `EX_BIGINT` stores the `TT_BIGINT` digit payload in `ExprNode.text_value` and stores the numeric base in a new
    `ExprNode.base_value` field.
07. `base_value` is required for `EX_BIGINT` only; this plan does not retroactively add structured base preservation to
    `EX_INT`.
08. Bigint range checks strip the optional leading sign and leading zeros before applying significant-digit thresholds.
09. Untyped `EX_BIGINT` literals require context. A bigint literal outside `int` with no expected `uint`, `long`, or
    `ulong` target is a type error.
10. Contextual bigint constants may convert to `uint`, `long`, or `ulong` when compile-time range checks pass.
11. Negative constants targeting `uint` or `ulong` fail at compile time.
12. Nonliteral narrowing and cross-signedness conversions require explicit casts and runtime checks.

## Goal

1. Make `uint`, `long`, and `ulong` real builtin integer types in the L1 Stage 1 compiler.
2. Preserve opaque bigint literal text and base information from lexing through type checking and C emission.
3. Define range-safe widening, checked narrowing, and contextual bigint literal behavior for the full implemented
   fixed-width integer family.
4. Extend runtime helpers and C emission so generated programs use checked `dea_*` integer operations for the new types.

## Implementation Phases

### Phase 1: Admit the new builtin names

Update lexing, parser type recognition, and semantic type construction so:

- `uint`, `long`, and `ulong` stop lexing as future-extension words
- parser type lookahead accepts them anywhere builtin types are accepted today
- `types.l0` and `type_resolve.l0` construct and resolve ordinary builtin types for the three names
- nullable wrappers follow the existing `dea_opt_*` pattern for `dea_opt_uint`, `dea_opt_long`, and `dea_opt_ulong`

### Phase 2: Carry bigint literals through the AST

Add `EX_BIGINT` and parse `TT_BIGINT` into it. The parser should preserve:

- `ExprNode.text_value`: the existing `TT_BIGINT` payload text, prefix-stripped, lowercase, sign-inclusive
- `ExprNode.base_value`: the token base, one of `2`, `8`, `10`, or `16`

Update helper paths that enumerate literal expression kinds, including AST printing, expression cleanup, signature
literal inference, case literal handling, backend side-effect classification, and constant-initializer paths.

`TT_INT` / `EX_INT` behavior should stay unchanged because native `int` values no longer need base information after
lexing. `TT_BIGINT` / `EX_BIGINT` must preserve base information because the compiler never materializes a native value.

### Phase 3: Add bigint range and diagnostic helpers

Add shared typing helpers that can classify a bigint payload without converting it to an L0 integer:

- detect a leading `-`
- compute significant digit text by stripping sign and leading zeros
- compare significant digits against the target type's base-specific bound
- handle exact boundary spellings, not only digit counts
- reject negative constants for `uint` and `ulong`

Use these thresholds as the first-pass significant-digit guard:

- `uint`: base 2 `32`, base 8 `11`, base 10 `10`, base 16 `8`
- `long`: base 2 `63` for positive values, with the signed-minimum special case allowed for negative values; base 8
  `21`; base 10 `19`; base 16 `16`
- `ulong`: base 2 `64`, base 8 `22`, base 10 `20`, base 16 `16`

Where a threshold length matches, compare against the exact textual limit for the target/base combination so
compile-time diagnostics do not reject valid boundary values or accept invalid boundary values solely by digit count.

### Phase 4: Extend typing and cast rules

Treat the implemented integral family as `{tiny, byte, short, ushort, int, uint, long, ulong}`.

Use range-safe implicit widening:

- `tiny -> short`
- `tiny -> int`
- `tiny -> long`
- `byte -> short`
- `byte -> ushort`
- `byte -> int`
- `byte -> uint`
- `byte -> long`
- `byte -> ulong`
- `short -> int`
- `short -> long`
- `ushort -> int`
- `ushort -> uint`
- `ushort -> long`
- `ushort -> ulong`
- `int -> long`
- `uint -> long`
- `uint -> ulong`

Reject other implicit signedness-changing or narrowing conversions. In particular, reject signed nonliteral values to
`uint` or `ulong` unless written as explicit casts.

Allow explicit casts among all implemented integral builtins. Runtime helpers should enforce target signedness, range,
overflow, and underflow.

Untyped `EX_BIGINT` literals fail with `TYP-0702`. `EX_BIGINT` literals in a non-integer contextual target fail with
`TYP-0703`. Bigint literals outside the expected integer target range fail with `TYP-0700`.

### Phase 5: Extend runtime helpers and C lowering

Update C lowering so builtin types emit as `dea_uint`, `dea_long`, and `dea_ulong`, and so optional wrappers emit as
`dea_opt_uint`, `dea_opt_long`, and `dea_opt_ulong`.

Add runtime helpers for checked arithmetic and casts involving the new integer widths. The helper set should be
source-aware where needed so signedness and range checks are correct for conversions such as `long -> uint`,
`ulong -> long`, and `int -> ulong`.

Emit bigint literals as C expressions only after compile-time textual range checks prove that the literal is valid for
the expected target type. The emitter should reconstruct the base prefix from `base_value` rather than relying on the
prefix-stripped digit payload alone.

### Phase 6: Add regression coverage and docs

Update lexer/parser/type-resolution/type-checking/emitter/backend tests for the new builtin types, bigint AST nodes,
conversion rules, diagnostics, and C lowering.

Update design-decision documentation and the shared diagnostic-code catalog so the implemented integer model and new
bigint literal diagnostics are explicit.

## Diagnostics

1. Keep `TYP-0700` as "integer literal is outside the target integer type range". Extend the implementation coverage to
   `uint`, `long`, and `ulong`, including negative constants targeting unsigned types.
2. Add `TYP-0702` with meaning "integer literal outside `int` requires a contextual integer type". Use it for untyped
   `EX_BIGINT` literals such as `let x = 2147483648;`.
3. Add `TYP-0703` with meaning "integer literal outside `int` cannot be used in this contextual type". Use it when an
   `EX_BIGINT` appears in an expected non-integer context and the existing mismatch diagnostics would obscure the
   literal-specific problem.

Register `TYP-0702` and `TYP-0703` in `docs/specs/compiler/diagnostic-code-catalog.md` and update L1 diagnostic parity
tests if they require catalog/message synchronization.

## Non-Goals

- changing L0 numeric semantics
- adding integer suffix syntax
- adding digit separators
- defaulting untyped bigint literals to `uint`, `long`, or `ulong`
- retroactively preserving base information for `EX_INT`
- implementing floating-point behavior
- exposing arbitrary-precision integer runtime values

## Verification Criteria

1. `make -C l1 test-stage1 TESTS="lexer_test"` passes with direct coverage proving `uint`, `long`, and `ulong` are no
   longer future-extension words and existing `TT_BIGINT` lexing still preserves text/base payloads.
2. `make -C l1 test-stage1 TESTS="parser_test type_resolve_test"` passes with declarations, parameters, returns,
   pointers, nullable types, and type-position intrinsics using the new builtins, plus bigint literals parsing as
   `EX_BIGINT`.
3. `make -C l1 test-stage1 TESTS="expr_types_test"` passes with range-safe widening cases, rejected implicit signed to
   unsigned conversions, explicit-cast cases, contextual bigint constants, and `TYP-0700` / `TYP-0702` / `TYP-0703`
   coverage.
4. `make -C l1 test-stage1 TESTS="c_emitter_test backend_test"` passes with generated C using `dea_uint`, `dea_long`,
   `dea_ulong`, optional wrappers, reconstructed bigint literal spellings, and checked runtime helper calls.
5. Bigint normalization tests cover leading-zero literals such as `0002147483648`, `0x0000000080000000`, and boundary
   unsigned values by significant digits rather than raw payload length.
6. Existing small-integer behavior remains unchanged.

## Open Design Constraints

1. `base_value` is not optional for `EX_BIGINT`; without it, prefix-stripped payloads such as `80000000` are ambiguous
   between bases.
2. Compile-time bigint checks must remain textual and conservative because Stage 1 cannot use native 64-bit arithmetic.
3. Runtime helper design must avoid host-C undefined behavior and must keep signedness/range policy at the runtime
   boundary, as with existing checked `int` helpers.
