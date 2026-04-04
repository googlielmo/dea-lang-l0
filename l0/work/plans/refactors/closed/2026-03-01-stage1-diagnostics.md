# Refactor Plan

## Unified Stage 1 Diagnostics Collector and Full Error Recovery

- Date: 2026-03-01
- Status: Closed (implemented)
- Title: Unified Stage 1 Diagnostics Collector and Full Error Recovery
- Kind: Refactor
- Severity: Medium (Developer Experience)
- Stage: Stage 1 Compiler
- Subsystem: Lexer, Parser, Driver, CLI
- Modules:
  - `compiler/stage1_py/l0_lexer.py`
  - `compiler/stage1_py/l0_parser.py`
  - `compiler/stage1_py/l0_driver.py`
  - `compiler/stage1_py/l0_diagnostics.py`
  - `compiler/stage1_py/l0c.py`
- Test modules:
  - `compiler/stage1_py/tests/lexer/test_lexer.py`
  - `compiler/stage1_py/tests/parser/test_parser_recovery.py`
  - `compiler/stage1_py/tests/parser/test_parser_parse_errors.py`
  - `compiler/stage1_py/tests/integration/test_byte_type.py`
  - `compiler/stage1_py/tests/integration/test_case_statement.py`
  - `compiler/stage1_py/tests/integration/test_with_statement.py`

## Summary

Refactor the Stage 1 compiler to use a unified diagnostics collector across all phases, bringing it in line with the
architecture established in Stage 2. This replaces the legacy exception-based bail-out mechanism in the lexer and parser
with a flexible reporting system that supports error collection and full synchronization-based recovery.

The work establishes the diagnostics list as the single source of truth for errors, removing `LexerError` and
`ParseError` from the external API. The parser now implements synchronization loops at statement and declaration
boundaries, allowing it to continue analyzing source files after encountering malformed constructs and providing
comprehensive multi-error reports.

## Changes

1. **`l0_lexer.py`**:
   - Added `diagnostics: List[Diagnostic]` support to the `Lexer` class.
   - Replaced immediate `LexerError` raises with `self._error()` calls and implemented basic recovery (e.g., skipping
     invalid characters or terminating literals early).
   - Removed `LexerError` class and updated `tokenize()` to always complete without throwing exceptions.
2. **`l0_parser.py`**:
   - Added `diagnostics: List[Diagnostic]` support to the `Parser` class.
   - Introduced `_error` (log and continue) and `_error_bail` (log and raise internal synchronization exception) helper
     methods.
   - Renamed `ParseError` to `_ParseSyncException` and moved it to internal use only.
   - Implemented `_sync_top_level()` and `_sync_stmt()` synchronization loops to recover from syntax errors at
     declaration and statement boundaries.
   - Updated `_expect_semicolon` to use non-bailing `_error`, enabling auto-recovery for missing semicolons.
   - Updated `parse_module` to catch synchronization exceptions in its header preamble and return a partial AST.
3. **`l0_driver.py`**:
   - Updated `L0Driver` to initialize and manage a master diagnostics list.
   - Passed this list down to `Lexer` and `Parser` instances during source loading.
   - Removed legacy `LexerError` and `ParseError` catch blocks from `analyze()`.
   - Implemented an early exit in `analyze()` after building the compilation unit if errors were found, ensuring
     semantic analysis is only run on validly parsed ASTs.
4. **`l0_diagnostics.py`**:
   - Broke a circular dependency with `l0_lexer.py` by using `TYPE_CHECKING` and forward references for the `Token` type
     in diagnostic utility functions.
5. **`l0c.py`**:
   - Refactored diagnostic printing into `print_diagnostic_list` to support printing arbitrary collections of
     diagnostics.
   - Updated `cmd_ast` and `cmd_tok` to check for and display diagnostics from the driver or lexer upon failure,
     providing rich error snippets even for non-compilation modes.

## Verification

### Automated Tests

- Updated roughly 30 tests across multiple modules to check the `diagnostics` list instead of expecting `LexerError` or
  `ParseError` exceptions.
- Renamed and updated `compiler/stage1_py/tests/parser/test_parser_recovery.py` to verify multi-error reporting:
  - `test_parser_recovery_from_missing_semicolon`
  - `test_parser_recovery_from_missing_import_semicolon`
- Verified a full `pytest` pass for Stage 1 (1023 passed).

### Manual Verification

- Verified that `./l0c --ast temp/test.l0` reports multiple missing semicolon errors with high-quality source snippets
  and carets.
- Confirmed that stable error codes (e.g., `[PAR-0100]`) are correctly reported in all diagnostics.

## Assumptions and Defaults

- Error codes remain stable and are embedded in diagnostic messages.
- The diagnostics list is the definitive source for determining compilation success or failure.
