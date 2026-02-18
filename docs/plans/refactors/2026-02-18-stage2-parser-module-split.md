# Refactor Plan

## Split `parser.l0` into manageable modules (`parser.*`, merged API)

- Date: 2026-02-18
- Status: Closed (implemented)
- Title: Split Stage 2 parser into internal modules while preserving `import parser` API
- Kind: Refactor
- Severity: Medium (maintainability and reviewability)
- Stage: 2
- Subsystem: Frontend Parser
- Modules: `compiler/stage2_l0/src/parser.l0`, `compiler/stage2_l0/src/parser/impl/shared.l0`, `compiler/stage2_l0/src/parser/impl/expr.l0`, `compiler/stage2_l0/src/parser/impl/stmt.l0`, `compiler/stage2_l0/src/parser/impl/decl.l0`

## Summary

Refactor `compiler/stage2_l0/src/parser.l0` (1,740 LOC) into coarse internal modules while preserving the external
`import parser` contract exactly.
Use `parser.*` for parser internals and keep public parser API types/functions in `parser.l0`.
Keep parser behavior/diagnostics unchanged.

## Target File Layout

1. `compiler/stage2_l0/src/parser.l0`
   Public parser API types plus facade wrappers (stable external API).
2. `compiler/stage2_l0/src/parser/impl/shared.l0`
   Internal parser state, token/span helpers, name/type helpers.
3. `compiler/stage2_l0/src/parser/impl/expr.l0`
   Expression parser functions.
4. `compiler/stage2_l0/src/parser/impl/stmt.l0`
   Pattern plus statement parser functions.
5. `compiler/stage2_l0/src/parser/impl/decl.l0`
   Top-level/module parser plus internal parse entrypoints.

## Public API and Type Interface

Keep `module parser` as the only public import target used by tests/callers.

`parser.l0` will expose:

1. `struct ParseError`
2. `enum ParseErrorState`
3. `struct ParseResult`
4. `func parse_result_free(self: ParseResult*)`
5. `func parse_module_tokens(tokens: TokenVector, filename: string) -> ParseResult*`
6. `func parse_module_source(source: string, filename: string) -> ParseResult*`
7. Internal facade conversion helpers:
   `impl_error_to_public`, `impl_result_to_public`

Rationale:

1. Public API remains stable at `import parser`.
2. Internal API (`ImplParse*`) is decoupled from public API to avoid import cycles.
3. This keeps `ParseNoError` and `ParseHasError` usage unchanged for consumers.

## Internal Function Ownership

`parser.shared.l0`:

1. `ParserState` and parser state lifecycle.
2. `tok_is*`, `ps_peek/advance/check/match/expect*`, literal token helpers.
3. span helpers.
4. variable-name validation.
5. qualified-name helpers (`QualifiedNameResult`, `ps_try_parse_qualified_name`).
6. type parsing helpers (`ps_parse_type`, builtin-type predicates, call-arg type disambiguation).
7. reserved-operator checks.

`parser.expr.l0`:

1. `ps_parse_expr` down to `ps_parse_primary_expr`.
2. postfix/cast/unary/binary precedence logic.

`parser.stmt.l0`:

1. `ps_parse_pattern`.
2. all statement parsing (`block`, `if`, `while`, `for`, `match`, `case`, `with`, simple stmt, stmt dispatcher).

`parser.decl.l0`:

1. top-level decl parsing (`func`, `extern`, `struct`, `enum`, `type`, top-level `let`).
2. module/import parsing.
3. internal entrypoint used by facade.

Internal impl-only API types:

1. `ImplParseError`, `ImplParseErrorState`, `ImplParseResult` live in `parser.shared`.
2. `parser.decl` returns `ImplParseResult*`, and `parser.l0` converts to public `ParseResult*`.

## Migration Sequence

1. Baseline validation run:
   `./compiler/stage2_l0/run_tests.sh` and parser trace plus triage check.
2. Extract shared internals to `parser/impl/shared.l0`.
3. Extract expression logic to `parser/impl/expr.l0`.
4. Extract pattern/statement logic to `parser/impl/stmt.l0`.
5. Extract module/top-level logic and parse entrypoint to `parser/impl/decl.l0`.
6. Keep public API in `parser.l0` and add impl-to-public conversion.
7. Remove now-obsolete `parser_impl/*` modules.
8. Remove dead code/imports; keep diagnostics/messages/spans untouched.
9. Run full validation gates.

## Acceptance Criteria

1. External parser API unchanged for existing consumers:
   `compiler/stage2_l0/tests/parser_test.l0` compiles unchanged with `import parser`.
2. Parser behavior unchanged:
   all current parser tests pass and no changed `PAR-xxxx` codes/messages unless bugfix is explicitly intended.
3. Memory/ARC trace safety unchanged:
   `run_parser_trace.sh` exit code `0`.
4. `check_trace_log.py ... --triage --max-details 8` shows:
   `errors=0`, `warnings=0`, `leaked_object_ptrs=0`, `leaked_string_ptrs=0`.
5. Do not enforce exact `op_counts` parity (informational only).

## Test Cases and Scenarios

1. Existing Stage 2 tests:
   `./compiler/stage2_l0/run_tests.sh`
2. Focused parser regression:
   `./l0c -P compiler/stage2_l0/src run compiler/stage2_l0/tests/parser_test.l0`
3. Trace plus triage:
   `./compiler/stage2_l0/run_parser_trace.sh`
4. `./compiler/stage2_l0/check_trace_log.py <stderr-log> --triage --max-details 8`

## Implementation Verification

Executed on 2026-02-18:

1. `./l0c -P compiler/stage2_l0/src run compiler/stage2_l0/tests/parser_test.l0`
   Result: pass (`parser_test: all tests passed`).
2. `./compiler/stage2_l0/run_tests.sh`
   Result: pass (`8/8` tests passed).
3. `./compiler/stage2_l0/run_parser_trace.sh`
   Result: pass (`exit_code=0`).
4. `./compiler/stage2_l0/check_trace_log.py /tmp/l0_stage2_parser_trace_20260218_165506.stderr.log --triage --max-details 8`
   Result: pass (`errors=0`, `warnings=0`, `leaked_object_ptrs=0`, `leaked_string_ptrs=0`).

## Assumptions and Defaults

1. Dotted module names under `src/parser/impl/*.l0` are supported by the current Stage 1 driver/module loader.
2. No import cycles are introduced (`parser` depends on `parser.*`; impl modules do not import `parser`).
3. Refactor is structural only: no grammar or semantic scope changes.
