# Feature Plan

## Introduce `is` intrinsic for enum payload-ignoring comparison

- Date: 2026-04-20
- Status: Draft
- Title: Introduce `is` intrinsic for enum payload-ignoring comparison
- Kind: Feature
- Severity: Medium
- Stage: L1
- Subsystem: Parser / Typing / Backend / Specs
- Modules:
  - `l1/compiler/stage1_l0/src/parser.l0`
  - `l1/compiler/stage1_l0/src/expr_types.l0`
  - `l1/compiler/stage1_l0/src/backend.l0`
  - `l1/compiler/shared/l1/stdlib/std/std.l1`
  - `l1/docs/reference/design-decisions.md`
- Test modules:
  - `l1/compiler/stage1_l0/tests/parser_test.l0`
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
- Related:
  - `l1/docs/roadmap.md`
- Repro: None

## Summary

The current L1 implementation uses the `ord(x) == ord(EnumVariant)` pattern to test whether a value has a specific enum
tag. This is cumbersome and requires synthesizing dummy payload values for variants that carry data (e.g.,
`ord(x) == ord(RGB(0,0,0))`), generating unnecessary allocation or initialization just for a tag check.

This plan introduces an `is(x, Variant)` intrinsic into the implicit `dea` module to replace manual `ord` comparison.
The intrinsic evaluates true if the tag of `x` matches the tag of `Variant`, ignoring the payload of `x`.

## Goal

Provide a clean, ergonomic syntax `is(expr, EnumVariant)` that checks enum tags without constructing dummy payloads.

## Implementation Phases

### Phase 1: `is` Intrinsic Support

1. Update `parser.l0` and AST to parse `is` as a recognized intrinsic or builtin call.
2. Update `expr_types.l0` to typecheck `is(value, EnumVariant)`. The first argument must be an enum expression, and the
   second must be a literal constructor reference to a variant of that enum type (even if it normally takes arguments).
3. Lower `is(expr, EnumVariant)` in `backend.l0` to the equivalent of `ord(expr) == ord(EnumVariant)` in the emitted C
   code, relying on the C enum tag without evaluating payload initialization.
4. Update `l1/docs/reference/design-decisions.md` to document `is(x, Variant)`.

### Phase 2: Refactor Existing L1 Code

1. Audit and replace `ord(x) == ord(...)` occurrences with `is(x, ...)` in `l1/compiler/shared/l1/stdlib/**/*.l1`.
2. Update L1 examples in `l1/examples/` and test fixtures to use `is` instead of `ord`.

## Verification Criteria

- `is(x, Variant)` parses and type-checks successfully.
- It correctly evaluates to a boolean `true` when the enum tags match.
- Code generation produces efficient tag comparison without constructing temporary payload values.
- All stdlib and compiler tests pass.
- No new memory leaks are introduced (verified via ARC trace rules).
