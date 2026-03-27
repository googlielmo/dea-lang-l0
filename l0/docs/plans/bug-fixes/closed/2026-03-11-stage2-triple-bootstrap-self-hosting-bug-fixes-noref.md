# Bug Fix Plan

## Stage 2 triple-bootstrap self-hosting uncovered multiple codegen and semantic parity bugs

- Date: 2026-03-11
- Status: Closed (fixed)
- Title: Fix Stage 2 self-hosting parity bugs exposed by the triple-bootstrap / triple-compilation regression
- Kind: Bug Fix
- Severity: Critical (Stage 2 could not self-host cleanly and could not reproduce Stage 1-identical retained C)
- Stage: 2
- Subsystem: Self-hosting bootstrap / semantic analysis / backend C emission
- Modules:
  - `compiler/stage2_l0/src/expr_types.l0`
  - `compiler/stage2_l0/src/backend.l0`
  - `compiler/stage2_l0/src/c_emitter.l0`
  - `compiler/stage2_l0/src/locals.l0`
  - `compiler/stage2_l0/src/lexer.l0`
  - `compiler/stage2_l0/src/parser/shared.l0`
  - `compiler/stage2_l0/src/parser/expr.l0`
  - `compiler/stage2_l0/src/parser/stmt.l0`
  - `compiler/stage2_l0/tests/expr_types_test.l0`
  - `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`
  - `docs/plans/features/closed/2026-03-11-triple-bootstrap-self-hosting-noref.md`
- Test modules:
  - `compiler/stage2_l0/tests/expr_types_test.l0`
  - `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`
- Repro:
  - `python3 compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`

## Summary

The triple-bootstrap regression did its job: it exposed that Stage 2 was not yet a faithful self-host of the Stage 1
compiler pipeline. The initial failures were not one bug but a stack of semantic-analysis, scope-tracking, parser, and
C-emission mismatches. Some bugs prevented Stage 2 from checking or building itself at all; others allowed self-hosting
to complete but produced retained C that diverged from the Stage 1 oracle.

This fix set closed that gap. After the changes below, the Stage 2 compiler can:

1. type-check the Stage 2 compiler sources with a built Stage 2 artifact,
2. build a second self-hosted compiler artifact,
3. build a third self-hosted compiler artifact,
4. reproduce second-build vs third-build compiler outputs byte-for-byte, and
5. pass the strict triple-bootstrap regression end to end.

## Bug inventory

### A. Expression typing and assignability bugs

1. `try` expression typing in Stage 2 did not match Stage 1:
   - non-nullable operands were not rejected correctly
   - the enclosing function return type was not validated correctly
   - the inferred result type did not consistently unwrap to the inner type
2. Assignment compatibility was incomplete relative to Stage 1:
   - `null` to nullable assignment was not handled correctly
   - implicit `T -> T?` wrapping parity was incomplete
   - pointer compatibility via `void*` was incomplete
3. Binary arithmetic on `byte` operands inferred the wrong natural type:
   - Stage 2 treated many byte arithmetic expressions as `byte`
   - Stage 1 treats arithmetic results as `int`
   - this caused downstream codegen divergence, especially around widening and checked narrowing

### B. Scope and constructor analysis bugs

1. `with` header scopes were not fully registered for later cleanup/body lookups.
2. Inline `with ... => cleanup` statements were not consistently type-checked through the same path as cleanup blocks.
3. `new` constructor arguments were not fully walked and typed, which left self-hosting code paths under-validated and
   caused downstream backend ICEs / bad resolution behavior.

### C. Literal decoding bugs

1. Escaped byte literals were decoded incorrectly because simple character escapes did not populate `char_value`.
2. Parsed byte expressions/case literals did not preserve decoded byte values in the AST.
3. Parsed string expressions used the raw token spelling instead of the decoded token value, which produced retained C
   mismatches such as `":\\t"` instead of `":\t"`.

### D. Backend lowering and ownership bugs

1. Lvalue lowering did not match Stage 1 behavior:
   - Stage 2 always emitted field/index lvalue syntax directly
   - Stage 1 only uses dedicated lvalue syntax when side-effect caching is needed
   - this changed retained C shape and evaluation behavior
2. Explicit nullable unwrap casts did not follow Stage 1 lowering for value-optionals.
3. Return lowering did not preserve Stage 1 move-return behavior for owned local variables and could introduce
   unnecessary retain-on-copy steps.
4. Statement-position `try` expressions lost the Stage 1 `(void)(...)` wrapper for non-ARC payloads.
5. Top-level `let` declarations emitted extra `#line` directives not present in Stage 1.
6. Type-definition emission order was not stable enough for retained-C identity and needed a proper dependency-driven
   ordering pass.

### E. C emitter parity bugs

1. Byte literals were emitted as integers instead of Stage 1-style `((l0_byte)'...')` literals.
2. `INT32_MIN` did not preserve the Stage 1 special-case spelling.
3. Cleanup and retain emission for nullable/enum cases did not match Stage 1 formatting and control-flow shape:
   - some `if (...) {` forms were split differently
   - enum cleanup could emit empty switches where Stage 1 emitted nothing
   - enum retain-copy switches used `default: break;` where Stage 1 uses `L0_UNREACHABLE("retain")`
4. Zero byte spelling used `'\x00'` instead of Stage 1’s `'\0'`.
5. The generated C main-wrapper footer did not preserve the trailing blank line Stage 1 emits.

## Root cause

The triple-bootstrap comparison was strict enough to expose two layers of defects:

1. **true semantic bugs** that prevented self-hosted Stage 2 from compiling the Stage 2 sources correctly, and
2. **oracle-parity bugs** where Stage 2 produced correct-enough C semantically, but not the same retained C that Stage 1
   produces.

The semantic bugs clustered around Stage 2 still not fully matching Stage 1 in three places:

1. expression typing (`try`, mixed int/byte behavior, assignability),
2. scope/ownership handling (`with`, owned returns, unwrap/materialization behavior),
3. literal decoding and AST storage (decoded bytes/strings vs source spelling).

The retained-C mismatches then clustered around Stage 2 still not fully matching the Stage 1 backend/emitter contract:

1. when to cache lvalues,
2. how to format byte literals and special integer constants,
3. which control-flow spelling to emit for cleanup/retain helpers,
4. where Stage 1 intentionally omits or includes small formatting details such as `#line` placement and trailing blank
   lines.

## Fix implemented

### A. Restore Stage 1 typing and assignability parity

Files:

- `compiler/stage2_l0/src/expr_types.l0`
- `compiler/stage2_l0/tests/expr_types_test.l0`
- `compiler/stage2_l0/tests/fixtures/typing/typing_try_ok.l0`
- `compiler/stage2_l0/tests/fixtures/typing/typing_try_non_nullable.l0`
- `compiler/stage2_l0/tests/fixtures/typing/typing_try_bad_return.l0`

Implemented:

1. Correct `try` typing rules and diagnostics.
2. Restored missing assignment-compatibility cases from Stage 1.
3. Changed integer arithmetic inference so byte arithmetic flows through `int` like Stage 1.
4. Added focused regression coverage for the `try` typing cases.

### B. Fix scope and constructor analysis issues needed for self-hosting

Files:

- `compiler/stage2_l0/src/locals.l0`
- `compiler/stage2_l0/src/expr_types.l0`

Implemented:

1. Registered `with` header scopes for later body/cleanup resolution.
2. Type-checked inline cleanup statements consistently.
3. Walked and type-checked `new` constructor arguments.

### C. Preserve decoded literal values through lexing and parsing

Files:

- `compiler/stage2_l0/src/lexer.l0`
- `compiler/stage2_l0/src/parser/shared.l0`
- `compiler/stage2_l0/src/parser/expr.l0`
- `compiler/stage2_l0/src/parser/stmt.l0`

Implemented:

1. Correct simple escape decoding for byte literals.
2. Added byte-value extraction helpers and stored decoded byte values in AST literals.
3. Added string-value extraction helpers and stored decoded string bytes in AST literals instead of raw token text.

### D. Align backend lowering with Stage 1

Files:

- `compiler/stage2_l0/src/backend.l0`

Implemented:

1. Restored Stage 1-style side-effect-aware lvalue caching.
2. Restored Stage 1 unwrap lowering for value-optionals.
3. Restored move-return behavior for owned local variable returns.
4. Restored statement-position `try` void-wrapping for non-ARC payloads.
5. Removed Stage-2-only top-level `let` line directives.
6. Reworked type-definition ordering to a stable dependency-driven emission pass.
7. Improved internal compiler error detail for unresolved variable references encountered during self-hosting work.

### E. Align C emission with Stage 1 retained-output shape

Files:

- `compiler/stage2_l0/src/c_emitter.l0`

Implemented:

1. Restored Stage 1 byte-literal spelling, including canonical escaped forms and `'\0'`.
2. Restored the `INT32_MIN` special-case emission.
3. Restored Stage 1 cleanup/retain control-flow spelling where retained-C identity depended on it.
4. Suppressed empty enum cleanup switches when no ARC payload exists.
5. Restored the trailing blank line after the generated C `main()` wrapper.

### F. Add the strict triple-bootstrap regression

File:

- `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`

Implemented:

1. Deterministic host compiler selection.
2. Deterministic linker-flag probing and native output stability checks.
3. Stage 1 build -> Stage 2 self-check -> Stage 2 self-build -> retained-C compare -> native-binary compare flow.
4. Final fixed-point comparison by adding one more self-build before the identity check.
5. Artifact retention and compact mismatch reporting for debugging.

## Verification

Executed:

```bash
./l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/expr_types_test.l0
./l0c -P compiler/stage2_l0/src --check parser
./l0c -P compiler/stage2_l0/src --check expr_types
./l0c -P compiler/stage2_l0/src --check backend
./l0c -P compiler/stage2_l0/src --check c_emitter
python3 compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py
```

Observed:

1. The focused Stage 2 typing regressions pass.
2. Stage 2 self-checks cleanly for the parser, typer, backend, and C emitter after the fixes.
3. The built Stage 2 compiler can self-host on the Stage 2 compiler sources.
4. The retained C emitted by the second and third self-hosted builds matches byte-for-byte.
5. The native compiler binaries emitted by the second and third self-hosted builds match byte-for-byte.
6. The triple-bootstrap regression passes end to end.

## Scope boundary

This document covers the bugs uncovered and fixed while making the strict triple-bootstrap regression pass on the
current Stage 2 compiler. It does not claim that all Stage 2 vs Stage 1 retained-output differences are closed in
general outside the code paths exercised by the self-hosting compiler build.
