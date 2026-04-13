# Feature Plan

## Add `tiny`, `short`, and `ushort` to L1 on the `dea_*` ABI base

- Date: 2026-04-04
- Status: Completed
- Title: Add `tiny`, `short`, and `ushort` to L1 on the `dea_*` ABI base
- Kind: Feature
- Severity: High
- Stage: 1
- Subsystem: Lexer / parser / typing / C emission / runtime integer helpers
- Modules:
  - `compiler/stage1_l0/src/tokens.l0`
  - `compiler/stage1_l0/src/parser/expr.l0`
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
  - `l1/work/plans/features/closed/2026-04-04-l1-dea-c-abi-prefix-migration-noref.md`
- Repro: `make test-stage1 TESTS="lexer_test parser_test type_resolve_test expr_types_test c_emitter_test backend_test"`

## Summary

After the public C ABI migration to `dea_*`, L1 can add its first new integral builtin types on a stable base: `tiny`,
`short`, and `ushort`.

This tranche keeps the feature intentionally narrow. It makes those three names real builtin types in the Stage 1
compiler, keeps integer literals inferred as `int`, keeps literals represented as `TT_INT` tokens and `EX_INT` nodes,
and introduces only the minimum conversion and runtime-helper surface required for declarations, calls, returns,
assignments, casts, and code generation.

## Dependency

This plan depends on `2026-04-04-l1-dea-c-abi-prefix-migration-noref.md` landing first. It assumes the public runtime
header and emitted C surface already use `dea_*` / `DEA_*` names.

## Available Infrastructure

`compiler/stage1_l0/src/util/numbers.l0` already provides range-checking helpers for Phase 2 constant-range diagnostics:
`fits_in_tiny` (`-128..127`), `fits_in_byte` (`0..255`), `fits_in_short` (`-32768..32767`), and `fits_in_ushort`
(`0..65535`). The same module provides `realnum_to_string` and `bigint_to_string` for number-literal display.

## Current State

1. The grammar now documents `tiny`, `short`, and `ushort` as builtin type names, but `compiler/stage1_l0/src/tokens.l0`
   still lexes them as `TT_FUTURE_EXTENSION`.
2. `compiler/stage1_l0/src/parser/expr.l0` only recognizes the currently implemented builtin names in type position.
3. `compiler/stage1_l0/src/types.l0` and `compiler/stage1_l0/src/type_resolve.l0` only construct/resolve the existing
   builtin integer set.
4. `compiler/stage1_l0/src/expr_types.l0` only treats `int` and `byte` as integral types and only implements the
   existing `byte -> int` implicit widening plus `int -> byte` checked cast path.
5. `compiler/stage1_l0/src/c_emitter.l0` only lowers the existing builtin integer types and only emits the existing
   checked narrowing helper pattern.

## Defaults Chosen

01. `tiny` is 8-bit signed and lowers to `dea_tiny`.
02. `byte` remains 8-bit unsigned and is distinct from `tiny`.
03. `short` is 16-bit signed and lowers to `dea_short`.
04. `ushort` is 16-bit unsigned and lowers to `dea_ushort`.
05. Integer literals remain inferred as `int`; this tranche does not add suffixes or non-`int` literal inference.
06. Integer literals reuse `TT_INT` tokens and `EX_INT` expression nodes; no small-int literal token or AST node kinds
    are introduced.
07. Fitting compile-time `int` literals may flow into narrower typed integer contexts without a runtime check.
08. Nonliteral narrowing remains explicit and lowers through checked runtime helpers where the destination range cannot
    contain the source range.
09. Implicit nonliteral conversions stay intentionally narrow and only cover explicit widening cases.
10. `long`, `uint`, and `ulong` remain reserved but unimplemented after this tranche.

## Goal

1. Make `tiny`, `short`, and `ushort` real builtin integer types in the L1 Stage 1 compiler.
2. Define the minimum typing and cast behavior needed for normal Stage 1 usage.
3. Extend runtime narrowing helpers and C emission so generated programs can use those types through the `dea_*` ABI.

## Implementation Phases

### Phase 1: Admit the new builtin names

Update lexing, builtin-name recognition, and semantic type construction so:

- `tiny`, `short`, and `ushort` stop lexing as future extensions
- parser type lookahead accepts them anywhere builtin types are accepted today
- semantic type construction and resolution produce ordinary builtin types for the three names

Keep `long`, `uint`, and `ulong` as future-extension words.

### Phase 2: Extend typing and cast rules

Treat the implemented integral family as `{tiny, byte, short, ushort, int}` and adopt these implicit widening rules
only:

- `tiny -> short`
- `tiny -> int`
- `byte -> short`
- `byte -> ushort`
- `byte -> int`
- `short -> int`
- `ushort -> int`

Reject all other implicit signedness-changing or narrowing conversions.

Allow fitting compile-time `int` literals to flow into narrower typed integer contexts, including annotated lets,
assignments, returns, call arguments, struct/enum constructor fields, and nullable wrapping. These checks reuse existing
`TT_INT` / `EX_INT` literal representation and emit no runtime range check when the literal fits.

Reject nonliteral narrowing in typed contexts unless it is written as an explicit cast, e.g. reject
`let x: tiny = someint + 1` but accept `let x: tiny = (someint + 1) as tiny`.

Allow explicit casts among all implemented integral builtins. Add one shared `TYP-0700` constant-range diagnostic for
compile-time `int` literals outside narrower target ranges:

- `tiny`: `-128..127`
- `byte`: `0..255`
- `short`: `-32768..32767`
- `ushort`: `0..65535`

### Phase 3: Extend runtime helpers and C lowering

In `compiler/shared/runtime/l1_runtime.h`, add checked narrowing helpers on the `dea_*` ABI surface for the new targets.
Expected emitted helper spellings are:

- `_rt_narrow_dea_tiny`
- `_rt_narrow_dea_byte`
- `_rt_narrow_dea_short`
- `_rt_narrow_dea_ushort`

Update C lowering so builtin types emit as `dea_tiny`, `dea_short`, and `dea_ushort`, and so implicit widening and
checked narrowing casts target the new helper/type names.

Optional-wrapper emission for the new builtins should follow the same `dea_opt_*` pattern established by the ABI
migration plan.

### Phase 4: Add regression coverage and docs

Update lexer/parser/type-resolution/type-checking/emitter/backend tests for the new builtin types and conversion rules.
Update design-decision documentation so implemented integer types and widths/signedness are accurate.

## Non-Goals

- implementing `long`, `uint`, or `ulong`
- changing integer literal syntax, inference, token kinds, or AST node kinds
- introducing arithmetic promotion beyond the explicit widening set above
- changing L0 semantics or runtime naming
- adding floating-point behavior

## Verification Criteria

1. `make -C l1 test-stage1 TESTS="lexer_test"` passes with direct coverage proving `tiny`, `short`, and `ushort` are no
   longer future-extension words.
2. `make -C l1 test-stage1 TESTS="parser_test type_resolve_test"` passes with declarations, parameters, returns,
   pointers, nullable types, and type-position intrinsics using the new builtins.
3. `make -C l1 test-stage1 TESTS="expr_types_test"` passes with positive widening cases, contextual literal narrowing
   cases, negative forbidden nonliteral narrowing cases, and explicit-cast overflow coverage for the new targets.
4. `make -C l1 test-stage1 TESTS="c_emitter_test backend_test"` passes with generated C using `dea_tiny`, `dea_short`,
   `dea_ushort`, and the new checked narrowing helpers.
5. After the change, `long`, `uint`, and `ulong` still behave as reserved-but-unimplemented names.

## Outcome

1. `tiny`, `short`, and `ushort` are implemented builtin integer types in the Stage 1 frontend, type resolver, type
   checker, backend, C emitter, and runtime header.
2. Integer literals remain ordinary `TT_INT` / `EX_INT` literals. Fitting literals may be used in narrower typed integer
   contexts; nonliteral narrowing requires an explicit cast.
3. `TYP-0700` now reports the shared meaning "integer literal is outside the target integer type range" for both
   contextual literal narrowing and explicit cast constant-range failures.
4. Generated C uses the `dea_*` ABI names for the new builtin types, optional wrappers, and checked narrowing helpers.
5. `docs/reference/design-decisions.md` and `docs/specs/compiler/diagnostic-code-catalog.md` document the resulting
   integer model and diagnostic meaning.
6. Verification passed with:
   - `make -C l1 test-stage1 TESTS="lexer_test parser_test type_resolve_test expr_types_test c_emitter_test backend_test"`
   - `make -C l1 test-stage1 TESTS="expr_types_test diagnostic_code_parity_test.py diagnostic_message_parity_test.py"`
   - `make -C l1 test-stage1`

## Open Design Constraints

1. This work must not begin on top of the legacy `l0_*` public ABI surface; it depends on the `dea_*` migration plan
   first.
2. `byte` and `tiny` must remain semantically distinct even though both are 8-bit wide.
3. Conversion rules must stay narrow enough to avoid introducing accidental mixed-signedness semantics before a broader
   integer-model plan exists.
