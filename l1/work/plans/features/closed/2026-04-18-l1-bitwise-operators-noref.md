# Feature Plan

## Add L1 bitwise operators

- Date: 2026-04-18
- Status: Completed
- Title: Add L1 bitwise operators
- Kind: Feature
- Severity: Medium
- Stage: L1
- Subsystem: Parser / expression typing / constant folding / C emitter
- Modules:
  - `l1/compiler/stage1_l0/src/parser/shared.l0`
  - `l1/compiler/stage1_l0/src/parser/expr.l0`
  - `l1/compiler/stage1_l0/src/expr_types.l0`
  - `l1/compiler/stage1_l0/src/backend.l0`
  - `l1/compiler/stage1_l0/src/c_emitter.l0`
- Test modules:
  - `l1/compiler/stage1_l0/tests/parser_test.l0`
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`
- Related:
  - `l1/docs/roadmap.md`
  - `docs/specs/compiler/diagnostic-code-catalog.md`
- Repro: `make -C l1 test-stage1 && make -C l1 check-examples`

## Summary

This completed plan lowered the bitwise tokens `&`, `|`, `^`, `~`, `<<`, and `>>` from reserved lexer surface into real
operators with precedence, typing rules, and C backend codegen.

## Current State

1. `l1/compiler/stage1_l0/src/tokens.l0` already defines `TT_AMP`, `TT_PIPE`, `TT_CARET`, `TT_TILDE`, `TT_LSHIFT`, and
   `TT_RSHIFT` with their printable spellings.
2. `ps_check_reserved_binary_op` in `l1/compiler/stage1_l0/src/parser/shared.l0` rejects the binary forms with
   `PAR-0226`; the unary `~` case in `l1/compiler/stage1_l0/src/parser/expr.l0` rejects the prefix form with the same
   code.
3. There is no precedence entry, no AST node kind dedicated to bitwise ops, no typing rule, no folding rule, and no C
   emitter branch for any of these operators.
4. Adjacent features (prefixed integer literals, small-int builtins, wide-integer builtins) already landed, so bitwise
   ops need to type-check coherently against `tiny`, `byte`, `short`, `ushort`, `int`, `uint`, `long`, `ulong`.

## Defaults Chosen

1. Bitwise AND, OR, and XOR are binary operators returning the common integer type of their operands, rejecting mixed
   signed/unsigned without an explicit cast.
2. Bitwise NOT (`~`) is a prefix unary operator that preserves the operand's integer type.
3. Shift operators `<<` and `>>` take an integer left operand and an unsigned or non-negative integer right operand; the
   result type is the left operand's type.
4. Right shift on a signed integer is arithmetic (sign-extending); right shift on an unsigned integer is logical. This
   matches C99 implementation-defined behavior under the backend's current targets.
5. Bitwise operators are not defined for `bool`. Logical `&&` and `||` remain the supported operators on `bool`.
6. Bitwise operators participate in compile-time constant folding using the same integer-range rules as the existing
   arithmetic folder.
7. Precedence follows the C family: unary `~` binds tightest of the bitwise set, then `<<` / `>>`, then `&`, then `^`,
   then `|`. The exact placement against existing comparison and logical operators is finalized in Phase 1.

## Goal

1. Accept the six bitwise operators in L1 source and route them to dedicated AST nodes.
2. Type-check them against the current integer-type lattice with clear mismatch diagnostics.
3. Fold bitwise ops over integer literal operands at compile time.
4. Emit them through the C backend so existing C99 semantics apply at runtime.
5. Remove the `PAR-0226` branches for these operators and either retire the code or narrow its use to remaining reserved
   forms.

## Implementation Phases

### Phase 1: Lock the grammar delta

Define precedence and associativity for the bitwise operators relative to existing arithmetic, comparison, and logical
operators. Record the decision in the design-decisions reference if it constrains future features (shift/compare
ambiguities, chained shifts, etc.). Decide whether `~` shares the existing unary precedence level with `-` and `!`.

### Phase 2: Parser support

Replace the `ps_check_reserved_binary_op` branches for `&`, `|`, `^`, `<<`, `>>` with real parse rules at the chosen
precedence levels. Replace the `TT_TILDE` branch in `ps_parse_unary_expr` with a real unary-parse branch. Introduce
dedicated AST shapes (either new `EX_BITAND` / `EX_BITOR` / `EX_BITXOR` / `EX_SHL` / `EX_SHR` / `EX_BITNOT` kinds, or a
shared `EX_BINOP` with operator metadata) consistent with how existing arithmetic ops are represented.

### Phase 3: Typing

Extend `expr_types.l0` with rules for:

- binary bitwise ops over equal integer types, with widening rules consistent with `+`/`-`/`*`/`/`
- shift ops with integer left operand and non-negative integer right operand
- unary `~` over any integer type, preserving the type
- error diagnostics for `bool`, floating-point, pointer, or mixed-sign operands

Register any new diagnostic codes in `docs/specs/compiler/diagnostic-code-catalog.md` before landing code.

### Phase 4: Constant folding

Fold literal bitwise ops in the existing constant evaluator. Preserve the result's declared integer type; reject shifts
whose right operand is negative or `>= bit_width(left)` at fold time.

### Phase 5: Backend and C emission

Lower each operator to the matching C99 operator in `backend.l0` / `c_emitter.l0`. Add parentheses defensively where C
precedence differs or where readability demands it. Ensure the generated C respects the signed/unsigned semantics chosen
for the shift operators.

### Phase 6: Regression coverage

Add tests in:

- `parser_test.l0` — precedence, associativity, operator pairings
- `expr_types_test.l0` — typed acceptance and rejection
- `l0c_lib_test.l0` — end-to-end runtime behavior including a shift-by-variable case

## Non-Goals

- operator overloading
- assignment-operator forms (`&=`, `|=`, `^=`, `<<=`, `>>=`) — tracked separately if they become desired
- bigint/wide-integer literal handling beyond what the existing literal path already supports
- new integer promotion rules beyond what current arithmetic ops do

## Verification Criteria

1. `make -C l1 test-stage1 TESTS="parser_test"` passes with new precedence and associativity cases.
2. `make -C l1 test-stage1 TESTS="expr_types_test"` passes with typed acceptance/rejection coverage.
3. `make -C l1 test-stage1 TESTS="l0c_lib_test"` passes with an end-to-end fixture exercising each operator at runtime.
4. `make -C l1 test-stage1` and `make -C l1 check-examples` both pass.
5. No code path still emits `PAR-0226` for the six operators listed above; if `PAR-0226` remains, its catalog entry
   narrows to the operators still unsupported.
6. Any newly registered diagnostic codes appear in `docs/specs/compiler/diagnostic-code-catalog.md`.
