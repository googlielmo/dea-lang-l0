# Refactor Plan

## Unify Stage 2 lexer/parser diagnostics through `util.diag`

- Date: 2026-02-24
- Status: Closed (implemented)
- Title: Refactor Stage 2 lexer and parser to use `util.diag` with parser multi-diagnostic collection
- Kind: Refactor
- Severity: Medium (frontend diagnostics consistency and parser usability)
- Stage: 2
- Subsystem: Frontend Lexer/Parser
- Modules: `compiler/stage2_l0/src/util/diag.l0`, `compiler/stage2_l0/src/lexer.l0`,
  `compiler/stage2_l0/src/parser.l0`, `compiler/stage2_l0/src/parser/shared.l0`,
  `compiler/stage2_l0/src/parser/decl.l0`, `compiler/stage2_l0/src/parser/expr.l0`,
  `compiler/stage2_l0/src/parser/stmt.l0`
- Test modules: `compiler/stage2_l0/tests/parser_test.l0` (and optional new `diag` tests)

## Summary

Unify diagnostics in Stage 2 by using `util.diag` in both lexer and parser.

Keep lexer fail-fast behavior, but emit lexer failures as `Diagnostic` entries instead of `LexerErrorState`.

Refactor parser from single-error state to `DiagCollector`, then add top-level declaration synchronization so one parse run can collect multiple parser errors.

Use diagnostics-only parser result surface (remove public single-error enum), with helper functions for caller/test ergonomics.

## Public API and Type Interface

1. `module parser`:
   Replace public `ParseError` / `ParseErrorState` usage with diagnostics on `ParseResult`.
2. `struct ParseResult`:
   Keep arenas and `root_module`, add `diags: DiagCollector*`.
3. Public helpers:
   `parse_has_errors(result: ParseResult*) -> bool`,
   `parse_diag_count(result: ParseResult*) -> int`,
   optional convenience getter for first error diagnostic.
4. `parse_result_free`:
   must free diagnostics collector ownership.
5. `module lexer`:
   keep `tokenize(self: LexerState*) -> TokenVector?`,
   but migrate `LexerState.error` to `LexerState.diags`.

## Internal Design Changes

1. `util.diag`:
   add missing collector lifecycle/access helpers required by parser/lexer ownership and callers:
   count/get/free.
2. Lexer internals:
   replace all `self.error = Error(...)` paths with `diag_error(...)` emission;
   keep current fail-fast control flow (`null` return on first lexer error).
3. Parser state (`parser.shared`):
   replace single `ImplParseErrorState` with `DiagCollector*`;
   replace `ps_set_error` with append-style diagnostic emission.
4. Parser recovery (`parser.decl`):
   after a failed top-level declaration parse, synchronize to next declaration boundary and continue.
5. Parser expression/statement modules:
   keep current error sites/codes/messages, but route through diagnostic collector.
6. Lex-to-parse path:
   in `impl_parse_module_source`, propagate lexer diagnostics into parse result diagnostics.

## Recovery Scope

Top-level synchronization only:

1. Recover between top-level declarations/import/module sections.
2. Do not add deep statement-level recovery in this change.
3. Keep expression/statement local behavior mostly unchanged to avoid semantic drift.

## Implementation Sequence

1. Extend `util.diag` helper surface (count/get/free).
2. Migrate `lexer.l0` state from enum error to `DiagCollector`.
3. Migrate parser internal result/state structs to diagnostics collector.
4. Replace parser error writes (`ps_set_error`) with collector appends.
5. Implement top-level sync-and-continue in module declaration loop.
6. Refactor `parser.l0` public result conversion to diagnostics-only API.
7. Update parser tests from `ParseHasError` matching to diagnostics inspection.
8. Add multi-error parser test cases.
9. Run Stage 2 gates.

## Acceptance Criteria

1. Lexer still fails at first error, but error is represented as a `Diagnostic` in lexer state.
2. Parser no longer exposes public single-error state; callers consume diagnostics.
3. Parser can collect multiple errors across malformed top-level declarations in one source.
4. Existing `PAR-xxxx` and `LEX-xxxx` codes remain stable.
5. Stage 2 tests pass:
   `./compiler/stage2_l0/run_tests.sh`
   and trace gate:
   `./compiler/stage2_l0/run_trace_tests.sh`.

## Test Cases and Scenarios

1. Existing parser success/failure tests rewritten to diagnostics API.
2. New parser recovery test:
   source with two broken top-level decls yields at least two parser error diagnostics.
3. New parser recovery continuity test:
   broken top-level decl followed by valid decl still parses remaining declarations.
4. Lexer propagation test through parser API:
   lex error (`LEX-*`) appears in parse diagnostics.
5. Optional `util.diag` helper tests for count/get/free semantics.

## Assumptions and Defaults

1. Chosen interface direction: parser diagnostics-only public API (no public `ParseErrorState`).
2. Chosen recovery level: top-level synchronization only.
3. Chosen lexer API shape: keep `tokenize(...)` signature and store diagnostics in lexer state.
4. This change is diagnostics/recovery refactor only; no language grammar or semantic feature expansion.

## Implementation Verification

Executed on 2026-02-24:

1. `./l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/parser_test.l0`
   Result: pass (`parser_test: all tests passed`).
2. `./compiler/stage2_l0/run_tests.sh`
   Result: pass (`9/9` tests passed).
3. `./compiler/stage2_l0/run_trace_tests.sh`
   Result: pass (`9/9` trace checks passed).
