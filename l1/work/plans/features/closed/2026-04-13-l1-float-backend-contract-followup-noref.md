# Feature Plan

## Define L1 floating-point semantic and C backend contract

- Date: 2026-04-13
- Status: Completed
- Title: Define L1 floating-point semantic and C backend contract
- Kind: Feature
- Severity: High
- Stage: 1
- Subsystem: Typing / semantics / backend / C emission / validation / tests
- Modules:
  - `compiler/stage1_l0/src/build_driver.l0`
  - `compiler/stage1_l0/src/expr_types.l0`
  - `compiler/stage1_l0/src/backend.l0`
  - `compiler/stage1_l0/src/c_emitter.l0`
  - `compiler/stage1_l0/src/sem_context.l0`
  - `compiler/stage1_l0/src/types.l0`
  - `compiler/stage1_l0/tests/expr_types_test.l0`
  - `compiler/stage1_l0/tests/build_driver_test.l0`
  - `compiler/stage1_l0/tests/c_emitter_test.l0`
  - `compiler/stage1_l0/tests/backend_test.l0`
  - `compiler/stage1_l0/tests/l0c_lib_test.l0`
  - `compiler/stage1_l0/tests/fixtures/typing/typing_float_ok.l1`
  - `compiler/stage1_l0/tests/fixtures/typing/typing_float_err.l1`
  - `compiler/stage1_l0/tests/fixtures/driver/float_main.l1`
  - `compiler/stage1_l0/tests/fixtures/driver/float_ops_main.l1`
  - `compiler/stage1_l0/tests/fixtures/driver/float_zero_div_main.l1`
- Test modules:
  - `compiler/stage1_l0/tests/expr_types_test.l0`
  - `compiler/stage1_l0/tests/build_driver_test.l0`
  - `compiler/stage1_l0/tests/c_emitter_test.l0`
  - `compiler/stage1_l0/tests/backend_test.l0`
  - `compiler/stage1_l0/tests/l0c_lib_test.l0`
- Related:
  - `l1/work/plans/features/closed/2026-04-04-l1-float-double-literals-noref.md`
  - `l1/docs/reference/design-decisions.md`
  - `l1/docs/reference/c-backend-design.md`
- Repro: `make test-stage1 TESTS="expr_types_test c_emitter_test backend_test build_driver_test l0c_lib_test"`

## Summary

The completed float-literal tranche added builtin `float` and `double`, real literals, narrow initial typing rules, and
plain C lowering to `float` / `double`. That work is complete and remains the starting point for this plan.

What remained to do was the language and backend contract for floating-point behavior. In particular, the closed plan
allows plain-C lowering for floating division, but leaves too much semantic weight on host C behavior and does not yet
state when such lowering is valid, what floating division by zero means at the L1 language level, or which backend and
build configurations must be rejected.

This follow-up plan defines the missing semantic boundary. It keeps the implemented syntax and literal model unchanged,
retains the current narrow conversion policy unless explicitly corrected, and adds the contract, validation, and test
surface needed so floating-point support is specified rather than merely emitted.

## Dependency

This plan depends on `l1/work/plans/features/closed/2026-04-04-l1-float-double-literals-noref.md` landing first. It
assumes builtin `float` / `double`, real literal AST nodes, the current narrow conversion rules, and direct C lowering
are already in place.

## Current State

1. L1 already has builtin `float` and `double`, typed real literal AST nodes, narrow implicit `float -> double`
   widening, explicit numeric casts among `int`, `float`, and `double`, and mixed `int` plus real arithmetic that still
   requires explicit casts.
2. Stage 1 already lowers `float` and `double` directly to C scalar types and emits floating arithmetic through plain C
   operators rather than checked integer helpers.
3. The closed plan explicitly treats floating `/ 0.0` as plain-C lowering behavior in emitted code.
4. No explicit L1 semantic section yet states whether floating arithmetic is non-panicking, whether floating division by
   zero is defined, or what subset of C targets is accepted for float-using programs.
5. No explicit backend validation step yet rejects unsupported float targets or incompatible build modes.
6. No explicit rule yet constrains future float constant folding to match the language contract.

## Defaults Chosen

01. This plan does not change the completed syntax, lexer, token, or literal-spelling decisions from the closed
    float-literal feature.
02. Floating-point arithmetic is non-panicking.
03. Floating division by zero is defined and does not panic.
04. On supported targets, `float` and `double` use IEEE-style non-trapping arithmetic with signed zero, infinities, and
    NaNs.
05. Integer division by zero remains a runtime error and continues to use the existing checked-integer path.
06. The language-level meaning of floating operations is defined by L1, not delegated to unspecified host C behavior.
07. The C backend lowers L1 `float` and `double` directly to C `float` and `double` only on targets that satisfy the L1
    floating-point backend contract.
08. If the backend cannot guarantee the required floating-point properties, compilation fails for programs that use
    `float` or `double`.
09. The current narrow conversion policy remains in force unless separately revised: implicit `float -> double` is
    allowed; implicit `double -> float`, `int -> float`, `int -> double`, `float -> int`, and `double -> int` are not
    allowed.
10. Stage 1 does not perform arithmetic evaluation of floating-point expressions unless it can guarantee results
    identical to the L1 floating-point contract.
11. This plan defines when explicit numeric casts are required versus rejected implicitly, but does not by itself expand
    the numeric surface with broader promotions or floating-environment controls.

## Goal

1. Define the L1 semantic contract for floating arithmetic, including division by zero.
2. Define the C backend contract required to lower L1 `float` and `double` soundly.
3. Make operator, comparison, assignment, return, and call typing rules for floating values mechanically explicit where
   the closed plan left them only partially implied.
4. Add backend validation so unsupported targets and invalid float-affecting build modes are rejected.
5. Add tests proving that Stage 1 preserves the floating-point contract it claims to implement.
6. Correct any ambiguity inherited from the closed float-literal plan without reopening completed lexer or literal work.

## Floating-Point Semantic Contract

1. `float` and `double` are builtin non-integer numeric types.
2. Floating arithmetic is non-panicking.
3. Floating division by zero is defined and does not panic.
4. On supported targets, floating arithmetic follows IEEE-style non-trapping behavior with signed zero, infinities, and
   NaNs.
5. Integer division by zero remains a runtime error.
6. The language-level meaning of floating operations is part of L1 and must not be left to unspecified host C behavior.
7. Backends may reject float-using programs on targets that cannot satisfy the required floating-point properties.

## C Backend Floating-Point Contract

When a program uses `float` or `double`, the Stage 1 C backend requires:

1. `float` lowers to C `float`; `double` lowers to C `double`.
2. The lowered C types must be binary radix floating-point types with the expected precision for the L1 types they
   represent.
3. The target must provide infinities and NaNs for the lowered types.
4. Floating arithmetic must be non-trapping in ordinary execution.
5. The backend must not enable optimization modes or code generation assumptions that invalidate NaN, infinity,
   signed-zero, or ordinary ordered-comparison semantics relied on by L1.
6. If these requirements are not met, compilation fails for programs that use `float` or `double`.

This contract intentionally narrows the set of acceptable C targets instead of assuming every C99 target is a valid L1
floating-point target.

## Operator and Typing Rules

### Unary Arithmetic Typing

1. Unary `-` is allowed for `int`, `float`, and `double`.
2. The result type of unary `-` is the operand type.
3. No implicit numeric conversion is performed for unary `-`.

### Binary Arithmetic Typing

For `+`, `-`, `*`, and `/`:

1. `int op int -> int` remains unchanged and continues to use the existing integer typing and lowering path.
2. `float op float -> float`.
3. `double op double -> double`.
4. `float op double` and `double op float` are allowed by implicit widening of the `float` operand to `double`, and the
   result type is `double`.
5. `int op float`, `float op int`, `int op double`, and `double op int` are rejected unless the integer operand is
   explicitly cast to the matching floating type.
6. No other implicit arithmetic promotions exist in this tranche.

### Assignment and Initialization Typing

1. Assignment and initialization require the source expression type to match the destination type after applying only
   the allowed implicit `float -> double` widening.
2. `float` may be assigned or initialized into `double` without an explicit cast.
3. `double` may not be assigned or initialized into `float` without an explicit cast.
4. `int` may not be assigned or initialized into `float` or `double` without an explicit cast, except where an already
   implemented special-case rule for direct integer literals into typed real contexts is intentionally preserved. If
   that exception remains, it must be documented explicitly in the implementation notes and tests.
5. `float` or `double` may not be assigned or initialized into `int` without an explicit cast.

### Return Typing

1. A `return` expression must match the declared return type after applying only the allowed implicit `float -> double`
   widening.
2. Returning `float` from a function returning `double` is allowed.
3. Returning `double` from a function returning `float` is rejected without an explicit cast.
4. Returning `int` from a function returning `float` or `double` is rejected without an explicit cast, except where the
   implementation intentionally preserves the already documented direct-integer-literal exception.
5. Returning `float` or `double` from a function returning `int` is rejected without an explicit cast.

### Call-Argument Typing

1. Each call argument must match its parameter type after applying only the allowed implicit `float -> double` widening.
2. Passing `float` to a `double` parameter is allowed.
3. Passing `double` to a `float` parameter is rejected without an explicit cast.
4. Passing `int` to a `float` or `double` parameter is rejected without an explicit cast, except where the
   implementation intentionally preserves the already documented direct-integer-literal exception.
5. Passing `float` or `double` to an `int` parameter is rejected without an explicit cast.

### Comparison Typing

For ordered comparisons and equality comparisons:

1. `int` with `int` is allowed under the existing integer rules.
2. `float` with `float` is allowed.
3. `double` with `double` is allowed.
4. `float` with `double` and `double` with `float` are allowed by implicit widening of the `float` operand to `double`.
5. `int` with `float`, `float` with `int`, `int` with `double`, and `double` with `int` are rejected unless an explicit
   cast makes the operand types compatible.
6. Comparison results have type `bool`.
7. Floating comparison semantics at runtime follow the L1 floating-point contract on supported targets.

### Explicit Cast Rules

1. Explicit casts are required for every numeric conversion except implicit `float -> double` widening in expression
   typing.
2. `double -> float` is allowed only by explicit cast.
3. `int -> float` and `int -> double` are allowed only by explicit cast, except where the implementation intentionally
   preserves the already documented direct-integer-literal exception in typed real contexts.
4. `float -> int` and `double -> int` are allowed only by explicit cast.
5. The exact runtime semantics of explicit floating and integer casts must be documented and tested as part of this
   follow-up work if they are not already fully specified.

## Division-by-Zero Rule

1. Integer division by zero is a runtime error.
2. Floating division by zero is well-typed for floating operands and does not panic.
3. The compiler does not insert runtime panic checks around floating division.
4. Lowering uses ordinary C floating division on supported targets.
5. The meaning of floating division by zero comes from the L1 floating-point contract, not from ad hoc runtime checks.

## Constant-Folding Rule

1. Stage 1 preserves floating literal payloads and does not perform arithmetic evaluation of floating-point expressions
   unless it can guarantee results identical to the L1 floating-point contract.
2. Any future floating constant folding must preserve the same semantics as runtime execution on supported targets.
3. The compiler and emitted C must not disagree about the meaning of floating literals, arithmetic, division by zero, or
   non-finite results.

## Implementation Phases

### Phase 1: Document and lock the floating semantic contract

Update the language reference and design-decision documentation so they state:

- floating arithmetic is non-panicking
- floating division by zero is defined
- integer division by zero remains a runtime error
- supported targets use IEEE-style non-trapping behavior with signed zero, infinities, and NaNs
- unsupported targets must be rejected rather than accepted with vague behavior

This phase is documentation-first because the backend and test work need a stable contract to enforce.

### Phase 2: Make typing rules fully mechanical

Update `expr_types.l0` and related typing logic so the implemented rules for floating arithmetic, comparisons,
assignments, returns, calls, and casts are explicit, uniform, and covered by tests.

This phase must also resolve one inherited ambiguity from the closed plan: whether the currently implemented direct
integer-literal flow into typed real contexts is intended as a permanent language rule or a temporary typing
convenience. That behavior should either be ratified and documented narrowly, or removed so the cast policy becomes
uniform.

### Phase 3: Add backend target validation

Update Stage 1 backend and C emission support so float-using programs are accepted only on targets that satisfy the L1
floating backend contract.

This phase should:

- emit compile-time checks in generated C support code or backend headers for the required target properties
- reject targets where the lowered C types do not satisfy the required representation assumptions
- reject targets where required non-finite values are unavailable
- reject backend modes or build configurations that would invalidate required floating semantics

### Phase 4: Lock lowering behavior to the contract

Update backend and emitter tests so floating arithmetic lowering is not merely present but contract-bound.

This phase should prove that:

- floating division never routes through checked integer helpers
- generated C preserves literal spelling and suffix fidelity
- generated code for floating division by zero is ordinary C floating division on supported targets
- no backend rewrite silently changes the agreed float contract later

### Phase 5: Add execution and regression coverage

Add typing, backend, emitter, and CLI smoke coverage for the contract surface, including positive and negative cases.

This phase should cover:

- allowed and rejected mixed-float operations
- assignment, return, and call cases under the narrow conversion policy
- direct tests for float zero-division lowering and non-panicking behavior
- backend rejection behavior when target validation fails
- any ratified exception for direct integer literals into typed real contexts

## Non-Goals

- reopening the lexer grammar for floating literals
- changing the `f` / `F` suffix rule or unsuffixed-`double` default
- adding hexadecimal floating literals
- adding digit separators
- adding NaN or Infinity lexical forms
- adding unary `+`
- adding advanced math library surface or stdlib APIs
- adding dynamic floating-point environment control
- adding signaling-NaN or trap-oriented semantics
- introducing a broad numeric promotion lattice
- changing any L0 grammar or runtime surface

## Verification Criteria

1. The language reference documents the floating semantic contract and the backend acceptance boundary.
2. `make -C l1 test-stage1 TESTS="expr_types_test"` passes with positive and negative cases for floating arithmetic,
   comparison, assignment, return, call, and cast typing under the chosen narrow rules.
3. `make -C l1 test-stage1 TESTS="c_emitter_test backend_test"` passes with direct coverage for backend validation,
   float lowering, and rejection of unsupported float targets or invalid backend modes.
4. `make -C l1 test-stage1 TESTS="l0c_lib_test"` passes with CLI smoke programs covering floating arithmetic and
   floating division by zero lowering.
5. No runtime panic path is emitted for floating division.
6. Float-using code is rejected when backend target validation fails.
7. Stage 1 floating constant handling does not perform unsound arithmetic evaluation.
8. Any preserved special-case rule for direct integer literals in typed real contexts is either explicitly documented
   and tested, or removed.

## Open Design Constraints

1. The follow-up plan must not reopen the completed lexer and literal feature unless a separate future plan does so.
2. The current narrow conversion policy should remain narrow; this plan is about specifying and validating it, not
   replacing it with a promotion lattice.
3. Backend lowering must stay compatible with the bootstrap C target while still being honest about unsupported targets.
4. The language-level meaning of floating operations must not be delegated to unspecified host C behavior.
5. The implementation must distinguish clearly between integer checked arithmetic and floating non-panicking arithmetic.
6. The existing direct-integer-literal exception in typed real contexts is the main remaining semantic irregularity and
   must be resolved explicitly rather than left as folklore.

## Future Surface, Deferred

This plan does not require a broader floating library surface, but later work will likely need explicit classification
helpers such as:

- `is_nan`
- `is_inf`
- `is_finite`

These are deferred. Their absence does not change the contract defined here.
