# Feature Plan

## Add L1 float and double types and literals

- Date: 2026-04-04
- Status: Completed
- Title: Add L1 float and double types and literals
- Kind: Feature
- Severity: High
- Stage: 1
- Subsystem: Tokens / parser / AST / typing / backend / C emission
- Modules:
  - `compiler/stage1_l0/src/tokens.l0`
  - `compiler/stage1_l0/src/lexer.l0`
  - `compiler/stage1_l0/src/ast.l0`
  - `compiler/stage1_l0/src/ast_printer.l0`
  - `compiler/stage1_l0/src/parser/shared.l0`
  - `compiler/stage1_l0/src/parser/expr.l0`
  - `compiler/stage1_l0/src/parser/stmt.l0`
  - `compiler/stage1_l0/src/types.l0`
  - `compiler/stage1_l0/src/type_resolve.l0`
  - `compiler/stage1_l0/src/signatures.l0`
  - `compiler/stage1_l0/src/expr_types.l0`
  - `compiler/stage1_l0/src/backend.l0`
  - `compiler/stage1_l0/src/c_emitter.l0`
  - `compiler/stage1_l0/tests/type_resolve_test.l0`
  - `compiler/stage1_l0/tests/c_emitter_test.l0`
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `compiler/stage1_l0/tests/parser_test.l0`
  - `compiler/stage1_l0/tests/expr_types_test.l0`
  - `compiler/stage1_l0/tests/backend_test.l0`
  - `compiler/stage1_l0/tests/l0c_lib_test.l0`
  - `compiler/stage1_l0/tests/fixtures/typing/typing_float_ok.l1`
  - `compiler/stage1_l0/tests/fixtures/typing/typing_float_err.l1`
  - `compiler/stage1_l0/tests/fixtures/driver/float_main.l1`
  - `compiler/stage1_l0/tests/fixtures/driver/float_ops_main.l1`
  - `compiler/stage1_l0/tests/fixtures/driver/float_zero_div_main.l1`
- Test modules:
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `compiler/stage1_l0/tests/parser_test.l0`
  - `compiler/stage1_l0/tests/type_resolve_test.l0`
  - `compiler/stage1_l0/tests/expr_types_test.l0`
  - `compiler/stage1_l0/tests/c_emitter_test.l0`
  - `compiler/stage1_l0/tests/backend_test.l0`
  - `compiler/stage1_l0/tests/l0c_lib_test.l0`
- Related:
  - `l1/docs/reference/design-decisions.md`
- Repro:
  `make test-stage1 TESTS="lexer_test parser_test type_resolve_test expr_types_test c_emitter_test backend_test l0c_lib_test"`

## Summary

L1 now has its first floating-point grammar and type-system delta against L0: builtin `float` and `double` type names,
floating-point literals, and the suffix rule that `f` / `F` selects `float` while the unsuffixed form selects `double`.

This tranche reused the earlier lexer groundwork (`TT_REALNUM(sig, exp_text, is_float)`), promoted `float` and `double`
into real builtin type names, added dedicated AST literal kinds, implemented the initial typing rules and cast contract,
and extended backend/C lowering plus regression coverage across parser, typing, backend, and CLI smoke paths.

## Current State

1. `compiler/stage1_l0/src/tokens.l0` now treats `float` and `double` as builtin reserved type names, while
   `compiler/stage1_l0/src/lexer.l0` continues to emit real literals as `TT_REALNUM(sig, exp_text, is_float)`.
2. `compiler/stage1_l0/src/ast.l0` and `compiler/stage1_l0/src/parser/expr.l0` now lower real literals into `EX_FLOAT`
   and `EX_DOUBLE`, preserving canonical source spelling for C emission.
3. `compiler/stage1_l0/src/types.l0`, `compiler/stage1_l0/src/type_resolve.l0`, `compiler/stage1_l0/src/signatures.l0`,
   and `compiler/stage1_l0/src/expr_types.l0` now resolve and type-check builtin `float` / `double` usage.
4. The implemented typing rules stay intentionally narrow: implicit `float -> double` widening is allowed, direct `int`
   literals can flow into typed real contexts, explicit numeric casts are allowed between `int`, `float`, and `double`,
   and mixed `int` + real binary arithmetic still requires an explicit cast.
5. `compiler/stage1_l0/src/backend.l0` and `compiler/stage1_l0/src/c_emitter.l0` now lower `float` / `double` directly
   to C scalar types and emit real arithmetic through plain C operators while preserving the existing checked
   integer-helper path for integer arithmetic.
6. The test surface now includes parser, type-resolution, typing, C-emitter, backend, and CLI keep-C coverage, including
   subtraction, multiplication, division, casts, and plain-C floating zero-division lowering.

## Defaults Chosen

1. Unsuffixed floating literals denote builtin `double`.
2. A trailing `f` or `F` denotes builtin `float`.
3. `float` and `double` should become builtin reserved type names in L1 rather than remaining future-extension tokens.
4. Keep the current lexer grammar for this tranche: decimal real literals may include an exponent part, while `.5`,
   `1.`, and hexadecimal-float syntax remain out of scope.
5. The C backend should lower L1 `float` and `double` directly to the corresponding C scalar types unless a runtime
   constraint forces a wrapper type.
6. Per `l1/docs/reference/design-decisions.md`, floating literal payloads should be stored as opaque strings and emitted
   verbatim into generated C99 rather than evaluated by the bootstrap compiler.
7. Implicit real conversions stay narrow: `float -> double` is allowed, while `double -> float` remains explicit-only.
8. Explicit numeric `as` casts are allowed between `int`, `float`, and `double`.
9. Floating-point `/ 0.0` follows the host C / IEEE behavior in generated code and does not use checked integer helpers.

## Goal

1. Add builtin `float` and `double` types to the L1 Stage 1 language.
2. Add floating-point literal support with `f` / `F` float suffixes and unsuffixed double defaults.
3. Define the minimum typing rules needed for declarations, returns, assignments, calls, and basic operators.
4. Extend Stage 1 code generation so programs using floating-point literals and types can compile successfully.

## Implementation Phases

### Phase 1: Carry forward the existing lexer and token model

The lexer/token decisions are already implemented and should be treated as fixed input for the remaining work:

- floating literals use one `TT_REALNUM(sig, exp_text, is_float)` token
- unsuffixed real literals denote `double`
- a trailing `f` / `F` denotes `float`
- `1.0`, `1e3`, `1.0f`, and `1e3f` are accepted
- `1f` is rejected as an integer-suffix error
- `.5` and `1.` are not real literals because digits are required on both sides of `.`

The remaining implementation should preserve these decisions rather than reopen lexer grammar design.

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

1. `make -C l1 test-stage1 TESTS="lexer_test"` remains green with direct coverage for accepted and rejected floating
   literals, including exponent and suffix forms.
2. `make -C l1 test-stage1 TESTS="parser_test"` passes with source snippets using `float`, `double`, and floating
   literals in declarations and expressions.
3. `make -C l1 test-stage1 TESTS="type_resolve_test expr_types_test"` passes with positive and negative floating
   resolution and typing cases, including casts and invalid supported operator combinations.
4. `make -C l1 test-stage1 TESTS="c_emitter_test backend_test l0c_lib_test"` passes with direct C lowering coverage and
   CLI smoke programs using `float` and `double`.
5. `float`-suffixed literals infer `float`, while unsuffixed floating literals infer `double`.
6. The chosen mixed-numeric typing and cast rules are covered by tests and documented in the implementation notes.

## Open Design Constraints

1. The mixed-numeric conversion rules are the main semantic risk and should be kept intentionally narrow in the first
   tranche.
2. Lexer decisions for forms like `1f`, `1.0f`, `1e3f`, `.5`, and `1.` are already settled in Stage 1 and should not be
   reopened unless the grammar itself intentionally changes.
3. Backend lowering has to stay compatible with the bootstrap C target and preserve literal spelling/suffix fidelity.
4. The numeric-payload representation must follow the design-decision record and avoid compile-time arithmetic on
   non-native floating values.
