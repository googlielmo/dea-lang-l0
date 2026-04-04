# Feature Plan

## Add L1 float and double types and literals

- Date: 2026-04-04
- Status: Draft
- Title: Add L1 float and double types and literals
- Kind: Feature
- Severity: High
- Stage: 1
- Subsystem: Lexer / parser / AST / typing / C emission
- Modules:
  - `compiler/stage1_l0/src/tokens.l0`
  - `compiler/stage1_l0/src/lexer.l0`
  - `compiler/stage1_l0/src/ast.l0`
  - `compiler/stage1_l0/src/parser/shared.l0`
  - `compiler/stage1_l0/src/parser/expr.l0`
  - `compiler/stage1_l0/src/types.l0`
  - `compiler/stage1_l0/src/type_resolve.l0`
  - `compiler/stage1_l0/src/expr_types.l0`
  - `compiler/stage1_l0/src/c_emitter.l0`
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `compiler/stage1_l0/tests/parser_test.l0`
  - `compiler/stage1_l0/tests/expr_types_test.l0`
- Test modules:
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `compiler/stage1_l0/tests/parser_test.l0`
  - `compiler/stage1_l0/tests/expr_types_test.l0`
  - numeric codegen smoke coverage
- Related:
  - `l1/docs/reference/design-decisions.md`
- Repro: `make test-stage1 TESTS="lexer_test parser_test expr_types_test"`

## Summary

L1 also wants its first floating-point grammar and type-system delta against L0: builtin `float` and `double` type
names, floating-point literals, and the suffix rule that `f` / `F` selects `float` while the unsuffixed form selects
`double`.

Unlike prefixed integer literals, this feature is not lexer-local. `float` and `double` are currently reserved as
future-extension words, the AST only has integer/byte/string/bool/null literal nodes, the type layer only exposes
`bool`, `byte`, `int`, `string`, and `void`, and the C emitter only knows how to lower the existing literal kinds. This
plan therefore spans the full Stage 1 pipeline from lexing through C emission and semantic rules.

## Current State

1. `compiler/stage1_l0/src/tokens.l0` reserves `float` and `double` as `TT_FUTURE_EXTENSION` rather than builtin type
   names.
2. `compiler/stage1_l0/src/lexer.l0` only lexes decimal integer literals and does not recognize decimal-point or
   floating suffix syntax.
3. `compiler/stage1_l0/src/ast.l0` only has `EX_INT`, `EX_BYTE`, `EX_STRING`, `EX_BOOL`, and `EX_NULL` among literal
   node kinds.
4. `compiler/stage1_l0/src/parser/expr.l0` only lowers integer literals into `EX_INT`.
5. `compiler/stage1_l0/src/types.l0` does not define builtin `float` or `double` constructors.
6. `compiler/stage1_l0/src/c_emitter.l0` does not emit floating-point literal spellings or builtin floating C types.

## Defaults Chosen

1. Unsuffixed floating literals denote builtin `double`.
2. A trailing `f` or `F` denotes builtin `float`.
3. `float` and `double` should become builtin reserved type names in L1 rather than remaining future-extension tokens.
4. The first implementation should target decimal floating literals only unless a later plan explicitly adds exponent or
   hexadecimal-float syntax.
5. The C backend should lower L1 `float` and `double` directly to the corresponding C scalar types unless a runtime
   constraint forces a wrapper type.
6. Per `l1/docs/reference/design-decisions.md`, floating literal payloads should be stored as opaque strings and emitted
   verbatim into generated C99 rather than evaluated by the bootstrap compiler.

## Goal

1. Add builtin `float` and `double` types to the L1 Stage 1 language.
2. Add floating-point literal support with `f` / `F` float suffixes and unsuffixed double defaults.
3. Define the minimum typing rules needed for declarations, returns, assignments, calls, and basic operators.
4. Extend Stage 1 code generation so programs using floating-point literals and types can compile successfully.

## Implementation Phases

### Phase 1: Define the grammar and token model

Specify:

- accepted literal spellings for decimal floating literals
- the exact `f` / `F` suffix rule for `float`
- the unsuffixed rule for `double`
- the boundary between integer literals and floating literals such as `1`, `1.0`, `1f`, and `1.0f`
- whether the first tranche accepts forms like `.5` and `1.` or requires digits on both sides of the decimal point

This phase should also decide whether the lexer introduces separate token kinds for `float` and `double` literals or a
single floating token that carries parsed-kind metadata.

### Phase 2: Introduce builtin floating types

Update the identifier and type pipeline so:

- `float` and `double` are treated as builtin reserved type names
- parser type recognition accepts them anywhere builtin types are valid today
- `types.l0` and `type_resolve.l0` can construct and compare builtin floating types consistently

This phase should keep the builtin-type handling structurally aligned with the existing `int` / `byte` / `bool` model.

### Phase 3: Add AST, parser, and typing support for floating literals

Extend Stage 1 so floating literals:

- parse into explicit literal expression nodes or a clearly documented extension of the current literal node shape
- retain their source spelling as the payload representation
- infer `float` or `double` according to the suffix rule
- participate in assignment, return, call-argument, cast, and operator checking

This phase must define the first-pass arithmetic and comparison rules for mixed numeric operands, including whether
implicit `float <-> double` or `int -> float/double` conversions are allowed.

### Phase 4: Add C lowering and execution coverage

Update code generation so the new builtin types and literals emit valid C, then add smoke coverage proving Stage 1 can:

- type-check local declarations with floating literals
- return floating values from functions
- pass floating arguments to functions
- emit and compile C for at least one `float` and one `double` path

## Non-Goals

- numeric promotion beyond the minimum rules required for the first floating-point tranche
- advanced math library surface or stdlib APIs
- hexadecimal floating literals
- digit separators
- NaN/Infinity lexical forms
- any L0 grammar or runtime change

## Verification Criteria

1. `make -C l1 test-stage1 TESTS="lexer_test"` passes with direct coverage for accepted and rejected floating literals.
2. `make -C l1 test-stage1 TESTS="parser_test"` passes with source snippets using `float`, `double`, and floating
   literals in declarations and expressions.
3. `make -C l1 test-stage1 TESTS="expr_types_test"` passes with positive and negative typing cases for floating
   assignments, returns, and calls.
4. A Stage 1 codegen smoke path compiles code using both `float` and `double`.
5. `float`-suffixed literals infer `float`, while unsuffixed floating literals infer `double`.
6. The chosen mixed-numeric typing rules are covered by tests and documented in the implementation notes.

## Open Design Constraints

1. The mixed-numeric conversion rules are the main semantic risk and should be kept intentionally narrow in the first
   tranche.
2. Lexer decisions for forms like `1f`, `1.0f`, `.5`, and `1.` must be settled up front to avoid churn across parser and
   typing.
3. Backend lowering has to stay compatible with the bootstrap C target and preserve literal spelling/suffix fidelity.
4. The numeric-payload representation must follow the design-decision record and avoid compile-time arithmetic on
   non-native floating values.
