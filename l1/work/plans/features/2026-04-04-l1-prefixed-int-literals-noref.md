# Feature Plan

## Add L1-prefixed integer literals

- Date: 2026-04-04
- Status: Draft
- Title: Add L1-prefixed integer literals
- Kind: Feature
- Severity: Medium
- Stage: 1
- Subsystem: Lexer / parser / literal semantics
- Modules:
  - `compiler/stage1_l0/src/lexer.l0`
  - `compiler/stage1_l0/src/tokens.l0`
  - `compiler/stage1_l0/src/parser/shared.l0`
  - `compiler/stage1_l0/src/parser/expr.l0`
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `compiler/stage1_l0/tests/parser_test.l0`
  - `compiler/stage1_l0/tests/expr_types_test.l0`
- Test modules:
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `compiler/stage1_l0/tests/parser_test.l0`
  - `compiler/stage1_l0/tests/expr_types_test.l0`
- Related:
  - `l1/docs/reference/design-decisions.md`
- Repro: `make test-stage1 TESTS="lexer_test parser_test expr_types_test"`

## Summary

L1 now wants a grammar delta against L0 for integer literals: decimal literals should keep their current behavior, and
additional prefixed forms should be accepted for hexadecimal (`0x` / `0X`), binary (`0b` / `0B`), and octal (`0o` /
`0O`) integers.

Today the Stage 1 lexer only recognizes decimal `TT_INT` tokens and parses them through `string_to_int`. The parser,
AST, and type checker already treat integer literals as ordinary `int` expressions after lexing, so this feature should
stay mostly lexer-led as long as all prefixed forms continue to lower into the existing `TT_INT` / `EX_INT` pipeline.

## Current State

1. `compiler/stage1_l0/src/lexer.l0` only reads consecutive decimal digits in `ls_read_number`.
2. `compiler/stage1_l0/src/tokens.l0` only exposes one integer-literal token kind: `TT_INT(text: string, value: int)`.
3. `compiler/stage1_l0/src/parser/expr.l0` consumes integer literals through `ps_match_int()` and builds `EX_INT`.
4. `compiler/stage1_l0/src/expr_types.l0` types `EX_INT` as builtin `int`.
5. No current tests exercise non-decimal integer literal syntax in L1 Stage 1.

## Defaults Chosen

1. Prefixed integer literals remain `int` literals, not new nominal numeric kinds.
2. The existing token and AST shape should be reused unless a concrete implementation constraint forces new metadata.
3. Prefix spelling should be preserved in token text for diagnostics and debug output.
4. Range validation should continue to target the signed 32-bit `int` range after base conversion.
5. Invalid digits for a given base should be rejected lexically rather than deferred to parsing or typing.
6. This plan stays on the native `int` path and does not rely on the opaque-string policy reserved for non-native L1
   numeric literals in `l1/docs/reference/design-decisions.md`.

## Goal

1. Accept `0x`, `0b`, and `0o` integer literal prefixes in L1 source.
2. Preserve the current downstream behavior for integer expressions after lexing.
3. Define clear lexical diagnostics for malformed prefixed literals and overflow.
4. Add focused Stage 1 tests for accepted and rejected prefixed literals.

## Implementation Phases

### Phase 1: Define the lexical grammar delta

Specify the accepted spellings and boundaries for:

- hexadecimal literals with `0x` / `0X`
- binary literals with `0b` / `0B`
- octal literals with `0o` / `0O`
- optional unary `-` as the existing separate parser-level operator

This phase should also define which malformed forms are rejected, including missing digits after a prefix, invalid
base-specific digits, and identifier-like suffixes after the literal.

### Phase 2: Extend Stage 1 lexing

Refactor `ls_read_number` so it can:

- detect the base from an optional prefix
- collect digits valid for that base
- preserve original source spelling in `TT_INT.text`
- convert the parsed magnitude into the existing signed `int` payload
- report lexical failures with existing overflow behavior and new malformed-prefix diagnostics as needed

The implementation should avoid changing how plain decimal literals are tokenized today.

### Phase 3: Validate parser and typing compatibility

Confirm that prefixed integer literals continue to flow through:

- `TT_INT`
- `EX_INT`
- builtin `int` typing
- any existing constant-sensitive checks such as `int -> byte` overflow

If a downstream phase depends on decimal spellings today, this phase should document and remove that coupling.

### Phase 4: Add focused regression coverage

Add tests for:

- accepted hexadecimal, binary, and octal literals
- malformed literals such as `0x`, `0b2`, `0o8`, and identifier-like suffixes
- 32-bit range overflow in prefixed forms
- typed-expression cases that prove downstream analysis still treats prefixed literals as ordinary `int`

## Non-Goals

- numeric separators or digit-grouping syntax
- unsigned integer types
- width-specific integer suffixes
- float or double literals
- any L0 grammar change

## Verification Criteria

1. `make -C l1 test-stage1 TESTS="lexer_test"` passes with direct lexer coverage for valid and invalid prefixed forms.
2. `make -C l1 test-stage1 TESTS="parser_test"` passes with source snippets using prefixed literals in expressions.
3. `make -C l1 test-stage1 TESTS="expr_types_test"` passes with typed examples that use prefixed integer literals.
4. Prefixed literals surface as ordinary `int` expressions in Stage 1 typing.
5. Malformed prefixed literals fail during lexing/parsing with deterministic diagnostics.
6. Signed 32-bit overflow is still rejected for prefixed literals.

## Open Design Constraints

1. The lexical grammar should stay L1-local and must not accidentally broaden L0 behavior.
2. Diagnostics should distinguish malformed base syntax from generic overflow where possible.
3. The implementation should not create a parallel integer-literal representation unless later numeric features need it.
4. The design-decision record for non-native numeric literals should remain the sole policy reference for any future
   widening from `int` to L1-only numeric kinds.
