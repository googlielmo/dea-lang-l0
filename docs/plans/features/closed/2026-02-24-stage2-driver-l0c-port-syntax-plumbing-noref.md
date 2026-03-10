# Feature Plan

## Port Stage 2 driver and `l0c` CLI plumbing with syntax-first execution

- Date: 2026-02-24
- Status: Implemented (2026-02-25)
- Title: Port Stage 2 driver and `l0c` command-line tool with syntax-check and token-dump modes
- Kind: Feature
- Severity: Medium (compiler workflow enablement and CLI parity scaffolding)
- Stage: 2
- Subsystem: Driver + CLI
- Modules: `compiler/stage2_l0/src/l0c.l0`, `compiler/stage2_l0/src/cli_args.l0`,
  `compiler/stage2_l0/src/driver.l0`, `compiler/stage2_l0/src/source_paths.l0`,
  `compiler/stage2_l0/src/diag_print.l0`
- Test modules: `compiler/stage2_l0/tests/cli_args_test.l0`, `compiler/stage2_l0/tests/driver_test.l0`,
  `compiler/stage2_l0/tests/l0c_test.l0`, `compiler/stage2_l0/tests/diag_print_test.l0`
- Other docs: `compiler/stage2_l0/README.md`, `docs/reference/project-status.md`

## Summary

Implement a Stage 2-native driver and CLI surface that mirrors Stage 1 mode-flag structure and validation behavior,
while executing only syntax-capable paths for now.

Operational modes in this phase:

1. `--check`: run lexer+parser across the transitive import closure and report syntax diagnostics.
2. `--tok`: dump lexer tokens for the entry module, or all modules with `--all-modules`.

All other Stage 1 modes are parsed and validated but return explicit NYI diagnostics.

Implementation includes ownership-safe ARC behavior for string option unwrap and pass-through paths in
`l0c`, `driver`, `source_paths`, `diag_print`, and `util.strings` aligned with `docs/reference/ownership.md`.
The Stage 2 code also uses `std.io::read_file` directly (no `util.io` wrapper module).

The repository root `./l0c` wrapper remains unchanged and continues to invoke Stage 1.

## Public Interfaces / Types / CLI Additions

1. New CLI entry module: `compiler/stage2_l0/src/l0c.l0`.
2. Public testable entrypoint:
   `func run_with_argv(argv: VectorString*) -> int`.
3. Runtime entrypoint:
   `func main()` collects process args via `std.system::argc/argv` and calls `run_with_argv`.
4. New CLI parsing module: `compiler/stage2_l0/src/cli_args.l0`.
5. New source path + target normalization module: `compiler/stage2_l0/src/source_paths.l0`.
6. New syntax driver module: `compiler/stage2_l0/src/driver.l0`.
7. New diagnostic rendering module: `compiler/stage2_l0/src/diag_print.l0`.

## Locked Decisions For This Plan

1. Stage 2 CLI accepts mode flags only; no legacy command-word rewrite shim.
2. Default mode remains `--build` for Stage 1 parity.
3. Functional modes in this phase are exactly `--check` and `--tok`.
4. `--run`, `--build`, `--gen`, `--ast`, `--sym`, `--type` return explicit NYI diagnostics.
5. Entry target normalization matches Stage 1:
   dotted module names and `.l0` path inputs are both accepted.
6. Diagnostic rendering follows Stage 1 style:
   header + source snippet line + caret span when location info is available.
7. Root `./l0c` script remains Stage 1-owned in this phase.
8. String ownership in this feature follows `docs/reference/ownership.md`:
   avoid manual retain on ordinary assignment and `opt as string` unwrap paths in these modules.
9. Stage 2 sources use `std.io::read_file` directly for file reads in this feature scope.

## Detailed Behavior Specification

### 1. CLI parsing and dispatch

1. Support Stage 1 global mode flags:
   `--run`/`-r`, `--build`, `--gen`/`-g`/`--codegen`, `--check`/`--analyze`, `--tok`/`--tokens`,
   `--ast`, `--sym`/`--symbols`, `--type`/`--types`.
2. Keep default mode `build` when mode flag is omitted.
3. Support Stage 1 global options/shape in parser surface:
   `-P/--project-root`, `-S/--sys-root`, `-v/--verbose`, `-l/--log`, `-o/--output`,
   `--keep-c`, `-c/--c-compiler`, `-C/--c-options`, `-I/--runtime-include`, `-L/--runtime-lib`,
   `-NLD/--no-line-directives`, `--trace-arc`, `--trace-memory`, `-a/--all-modules`, `--include-eof`.
4. Enforce one target only for all modes in this phase.
5. Parse `--` separator and enforce Stage 1 rules:
   post-`--` args are accepted only with `--run`.
6. Enforce Stage 1-equivalent mode-scoped option validation.
7. Dispatch command handlers by normalized mode.

### 2. Source path + target normalization

1. If target is dotted module name, validate identifier components and resolve via search paths.
2. If target is `.l0` path:
   use basename stem as module name and append target directory to project roots.
3. If target is absolute path or contains directory components without `.l0`, follow Stage 1 normalization behavior.
4. Default `project_root` to `.` when omitted.
5. Default `sys_root` from `L0_SYSTEM` (platform separator aware), else empty.
6. Search precedence is fixed:
   system roots first, then project roots.

### 3. Syntax driver pipeline

1. Maintain module cache keyed by module name.
2. Maintain loading-set to detect import cycles.
3. Resolve entry module and recursively load imports.
4. For each loaded source:
   read UTF-8 text, lex, parse, store module on success.
5. Aggregate parse and lex diagnostics from parser result collectors.
6. Detect and report:
   module not found, module-name mismatch, import cycle, UTF-8 decode/read failures.
7. Return an analysis result shape suitable for future semantic/codegen extension:
   entry module name, module map, diagnostics, error flag.

### 4. Diagnostics formatting

1. Print diagnostic header with severity, phase/code, and message.
2. If location exists and source line can be loaded:
   print `line | source` and caret indicator span.
3. If source cannot be loaded, print header only.
4. `--check` and `--tok` use the same formatter for tool-level errors.

### 5. Mode execution semantics

1. `--check`:
   run syntax driver on entry closure, print diagnostics, exit `1` on any errors else `0`.
2. `--tok`:
   tokenize target source(s), print token rows, honor `--include-eof`, return non-zero on lexical/load errors.
3. NYI modes (`run`, `build`, `gen`, `ast`, `sym`, `type`):
   emit deterministic NYI diagnostic and return non-zero.

## Implementation Sequence

1. Create `source_paths.l0` with Stage 1-equivalent search/normalize behavior.
2. Create `driver.l0` with module loading, import closure, and diagnostic aggregation.
3. Create `diag_print.l0` for Stage 1-like diagnostic rendering.
4. Create `cli_args.l0` with mode flags, option parsing, mode-scoped checks, and `--` handling.
5. Create `l0c.l0` with dispatcher and command handlers.
6. Add Stage 2 CLI/driver tests in dedicated test modules.
7. Run ownership remediation pass for Stage 2 driver/CLI string lifetimes (remove incorrect manual retains).
8. Add Stage 2 diagnostic-render trace regression coverage.
9. Update Stage 2 README with invocation and current mode support matrix.
10. Update project status doc if needed to reflect new Stage 2 driver/CLI capability.

## Acceptance Criteria

1. Stage 2 CLI parses the Stage 1 mode-flag surface and validates mode-scoped options correctly.
2. `--check` runs syntax validation on transitive imports and returns non-zero on syntax/import/load errors.
3. `--tok` dumps tokens for entry module and supports `--all-modules` + `--include-eof`.
4. Target handling supports dotted module names and `.l0` path input.
5. Non-syntax modes return explicit NYI diagnostics without crashing.
6. Root `./l0c` remains unchanged (Stage 1 wrapper).
7. Stage 2 test runner remains green with added tests.
8. Stage 2 trace test runner passes with `leaked_object_ptrs=0` and `leaked_string_ptrs=0`.
9. Targeted trace triage for `driver_test` and `l0c_test` reports zero leaked string pointers.
10. Diagnostic snippet printing path is exercised and trace-clean.

## Test Cases and Scenarios

1. CLI dispatch:
   default-mode dispatch to `build` handler;
   each explicit mode routes correctly.
2. CLI validation:
   multi-target rejection;
   invalid mode/option combinations rejected with explicit messages;
   `--` args accepted only with `--run`.
3. Driver target normalization:
   module-name target;
   `.l0` path target;
   invalid module-name diagnostics.
4. Driver import graph:
   transitive import success;
   import-cycle failure path.
5. Diagnostic rendering:
   with and without location;
   snippet/caret formatting behavior.
6. Token dump behavior:
   entry-only;
   all-modules;
   EOF include toggle.
7. NYI mode behavior:
   deterministic non-zero exit + stable NYI message per mode.
8. Ownership trace regression:
   `driver_test` and `l0c_test` produce no ARC/memory leaks in triage.
9. Diagnostic snippet ownership:
   location-bearing diagnostics (snippet + caret path) remain trace-clean.

## Assumptions and Defaults

1. This plan intentionally excludes Stage 2 semantic passes and code generation.
2. Stage 2 CLI keeps Stage 1 parity at interface/validation level, not execution parity yet.
3. Diagnostic code namespaces: `l0c.l0` reuses Stage 1 codes (`L0C-0011`, `L0C-0040`, `L0C-0070`) for equivalent
   operations and uses `L0C-9510` for Stage 2 NYI mode diagnostics. `cli_args.l0` keeps `L0C-2xxx` codes for CLI
   parsing/validation errors that have no Stage 1 counterpart (Stage 1 uses Python argparse for these). `driver.l0`
   reuses Stage 1 `DRV-0010`, `DRV-0020`, and `DRV-0030` for equivalent conditions and introduces `DRV-0011` for
   resolved-path read failures. Existing parser/lexer codes (`PAR-*`, `LEX-*`) are preserved.
4. Root CLI migration (switching `./l0c` to Stage 2) is deferred to a separate feature.

## Non-Goals

1. Implementing Stage 2 `--build`/`--run`/`--gen` backend pipeline.
2. Implementing Stage 2 AST/symbol/type dump output.
3. Introducing legacy Stage 1 command-word compatibility (`run`, `gen`, etc.) in Stage 2 CLI.
