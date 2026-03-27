# Bug Fix Plan

## Stage 2 self-hosting parity fixes in semantic analysis and backend emission

- Date: 2026-03-11
- Status: Closed (fixed)
- Title: Fix Stage 2 semantic and backend parity bugs blocking self-hosting correctness
- Kind: Bug Fix
- Severity: Critical
- Stage: 2
- Subsystem: Semantic analysis / parser literal handling / backend C emission
- Modules:
  - `compiler/stage2_l0/src/backend.l0`
  - `compiler/stage2_l0/src/c_emitter.l0`
  - `compiler/stage2_l0/src/expr_types.l0`
  - `compiler/stage2_l0/src/lexer.l0`
  - `compiler/stage2_l0/src/locals.l0`
  - `compiler/stage2_l0/src/parser/expr.l0`
  - `compiler/stage2_l0/src/parser/shared.l0`
  - `compiler/stage2_l0/src/parser/stmt.l0`
- Test modules:
  - `compiler/stage2_l0/tests/expr_types_test.l0`
  - `compiler/stage2_l0/tests/fixtures/typing/typing_try_ok.l0`
  - `compiler/stage2_l0/tests/fixtures/typing/typing_try_non_nullable.l0`
  - `compiler/stage2_l0/tests/fixtures/typing/typing_try_bad_return.l0`
- Repro:
  - `./l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/expr_types_test.l0`

## Summary

Stage 2 still had a cluster of Stage 1 parity bugs in typing, scope tracking, literal decoding, lvalue lowering, and
retained-C emission. Those bugs were concentrated in the code paths exercised while compiling the Stage 2 compiler
sources, so even small mismatches were enough to break self-hosting correctness or retained-output stability.

This fix set closes the compiler-side bugs first, before the separate triple-bootstrap harness and workflow changes.

## Bug Inventory

### A. Typing and assignability bugs

1. Postfix `?` on expressions did not enforce the Stage 1 rules for nullable operands and nullable function returns.
2. Assignment compatibility was missing several Stage 1 cases, especially nullable assignment and pointer compatibility
   through `void*`.
3. Arithmetic on `byte` operands inferred the wrong result type and diverged from Stage 1’s `int` behavior.
4. `new` argument checking did not validate initializer argument types rigorously enough for self-hosting paths.

### B. Scope and literal decoding bugs

1. `with` header scopes were not fully registered for later cleanup/body lookups.
2. Inline `with ... => cleanup` statements were not type-checked consistently.
3. Escaped byte literals did not preserve decoded values correctly.
4. Parsed byte and string literals sometimes retained source spelling instead of decoded values, which later changed the
   emitted C text.

### C. Backend and C-emitter parity bugs

1. Lvalue lowering did not preserve Stage 1’s side-effect-aware caching behavior.
2. Nullable unwrap lowering for value optionals diverged from Stage 1.
3. Owned local returns could lose move-return behavior and introduce extra retain/copy work.
4. Statement-position `try` expressions lost the Stage 1 `(void)(...)` wrapper for non-ARC payloads.
5. Top-level `let` declarations emitted extra `#line` directives.
6. Type-definition ordering was not deterministic enough for stable retained-C output.
7. Byte literal spelling, enum cleanup/retain control flow, `INT32_MIN`, and generated-footer formatting did not match
   Stage 1 closely enough.

## Fix Implemented

### A. Restore Stage 1 typing behavior

1. Fixed postfix `?` typing and diagnostics in `expr_types.l0`.
2. Restored the missing assignment-compatibility cases.
3. Restored Stage 1 arithmetic inference for `byte` expressions.
4. Added targeted typing regressions for successful and failing postfix-`?` cases.

### B. Preserve scope and decoded literal values

1. Registered `with` header scopes for later resolution.
2. Routed inline cleanup statements through the same checking path as block cleanups.
3. Preserved decoded byte values in lexer and parser literal handling.
4. Preserved decoded string content in parsed string expressions and case literals.

### C. Restore backend and emitter parity

1. Reintroduced Stage 1-style side-effect-aware lvalue caching.
2. Restored value-optional unwrap lowering.
3. Restored move-return behavior for owned locals.
4. Restored statement-position `try` void-wrapping for non-ARC payloads.
5. Removed extra top-level `let` line directives.
6. Reworked type-definition ordering into a stable dependency-driven pass.
7. Restored the retained-C spellings and cleanup/retain control-flow shapes required for Stage 1 parity.

## Verification

Executed:

```bash
./l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/expr_types_test.l0
./l0c -P compiler/stage2_l0/src --check parser
./l0c -P compiler/stage2_l0/src --check expr_types
./l0c -P compiler/stage2_l0/src --check backend
./l0c -P compiler/stage2_l0/src --check c_emitter
```

Observed:

1. The targeted postfix-`?` typing regressions pass.
2. Stage 2 checks cleanly for parser, typer, backend, and C emitter after the fixes.
3. The affected self-hosting code paths now match the Stage 1 oracle closely enough for the follow-up bootstrap work.
