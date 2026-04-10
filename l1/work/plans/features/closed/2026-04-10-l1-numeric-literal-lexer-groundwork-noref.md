# Feature Plan

## Establish L1 numeric-literal lexer groundwork

- Date: 2026-04-10
- Status: Completed
- Title: Establish L1 numeric-literal lexer groundwork
- Kind: Feature
- Severity: Medium
- Stage: 1
- Subsystem: Lexer / token model / diagnostics / lexer tests
- Modules:
  - `compiler/stage1_l0/src/lexer.l0`
  - `compiler/stage1_l0/src/tokens.l0`
  - `compiler/stage1_l0/src/parser/shared.l0`
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `docs/specs/compiler/diagnostic-code-catalog.md`
- Test modules:
  - `compiler/stage1_l0/tests/lexer_test.l0`
  - `compiler/stage1_l0/tests/parser_test.l0`
- Related:
  - `l1/work/plans/features/2026-04-04-l1-small-int-builtins-on-dea-abi-noref.md`
  - `l1/work/plans/features/2026-04-04-l1-float-double-literals-noref.md`
- Repro: `make test-stage1 TESTS="lexer_test parser_test"`

## Summary

L1 Stage 1 needs a broader numeric-literal lexer surface than the original L0-derived scaffold. Integer literals should
keep their existing `TT_INT` path, and the lexer should also recognize decimal / exponent real literals into a dedicated
`TT_REALNUM` token.

This tranche should stay intentionally lexer-local. It should establish token shape, diagnostics, and regression
coverage needed before later plans add more builtin integer types and full floating-point parser / typing / backend
support.

## Current State

1. `compiler/stage1_l0/src/lexer.l0` only recognized decimal integers in the original scaffold; this tranche needs to
   broaden the lexer-local numeric grammar without forcing downstream semantic changes yet.
2. Existing Stage 1 parser, AST, typing, and backend work still treat numeric literals as integer-local, so real
   literals must remain token infrastructure only in this tranche.
3. Dedicated shared diagnostics are needed before later numeric plans can rely on deterministic lexer failures for
   malformed exponent tails, suffixes, and real-literal boundary cases.
4. Focused Stage 1 lexer tests are needed so future small-integer and floating-point work can build on a stable literal
   token contract.

## Defaults Chosen

1. Real literals should remain lexer/token infrastructure only in this tranche; no parser, AST, typing, or C-emission
   support should be claimed here.
2. `TT_REALNUM` uses a compact payload: `TT_REALNUM(sig: string, exp_text: string, is_float: bool)`.
3. `sig` preserves the significand, including any leading `-` and decimal point.
4. `exp_text` preserves exponent presence and explicit sign as `""`, `"12"`, `"-12"`, or `"+12"` without preserving `e`
   versus `E`.
5. Token rendering should reconstruct a normalized lexeme using lowercase `e` and lowercase `f`.
6. Bare suffix forms such as `123f` remain invalid; `.5` and `1.` are not accepted as real literals in this tranche.

## Goal

1. Establish a stable lexer/token foundation for future L1-only numeric work.
2. Keep prefixed integer literals flowing through the existing `TT_INT` behavior.
3. Introduce a dedicated real-literal token and dedicated lexer diagnostics without broadening downstream semantics yet.
4. Add focused lexer-only regression coverage for accepted and rejected real-literal spellings.

## Outcome

1. `compiler/stage1_l0/src/lexer.l0` now recognizes real literals with decimal-point and exponent syntax, plus optional
   `f` / `F` suffixes, and emits `TT_REALNUM(sig, exp_text, is_float)`.
2. `compiler/stage1_l0/src/tokens.l0` now owns normalized rendering and cleanup for the new token payload.
3. `compiler/stage1_l0/src/parser/shared.l0` now measures `TT_REALNUM` spans correctly for diagnostics.
4. Shared compiler diagnostics now include:
   - `LEX-0065` invalid real literal: missing exponent digits
   - `LEX-0066` invalid character after real literal
   - `LEX-0067` invalid suffix after real literal
   - `LEX-0068` invalid float suffix after integer literal
5. `compiler/stage1_l0/tests/lexer_test.l0` now directly verifies positive and negative real-literal lexing, including
   exponent payload preservation and current non-goals such as `1.` and `.5`.

## Open Design Constraints

1. This groundwork should remain a lexer-local tranche until the floating-point plan decides parser, AST, typing, and
   backend semantics.
2. Later floating-point work should treat this token payload as the current starting point rather than reintroducing a
   more fragmented exponent representation without a concrete need.
3. Later small-integer and floating-point work should build on these registered diagnostics and lexer tests instead of
   duplicating lexer-only behavior elsewhere.
