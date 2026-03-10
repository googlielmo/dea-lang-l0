# Refactor Plan

## Replace subcommands with global mode flags in `l0c`

- Date: 2026-02-19
- Status: Closed (implemented)
- Title: Replace `l0c` subcommand parser with global mode flags and a simple legacy command shim
- Kind: Refactor
- Severity: Medium (CLI consistency and UX)
- Stage: 1
- Subsystem: Driver CLI
- Modules: `compiler/stage1_py/l0c.py`, `compiler/stage2_l0/run_tests.sh`, `compiler/stage2_l0/run_parser_trace.sh`,
- Test modules: `compiler/stage1_py/tests/cli/test_cli_mode_flags.py`
- Other docs: `docs/specs/compiler/stage1-contract.md`, `docs/specs/runtime/trace.md`, `compiler/stage2_l0/README.md`,
  `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`

## Summary

Replace command words (`run`, `build`, `gen`, `check`, `tok`, `ast`, `sym`, `type`) with global mode flags (`--run`,
`--build`, `--gen`, `--check`, `--tok`, `--ast`, `--sym`, `--type`) so all options can be passed globally and
consistently.

Default mode is `--build` when no mode flag is specified.

Keep a simple compatibility shim that accepts legacy command words and rewrites them to mode flags before parsing.

Parse target inputs as a positional list for future multi-target work, but reject more than one target for now.

## Public CLI Interface

1. New primary style:
   `./l0c [global-options] [mode-flag] <target> [-- program-args]`
2. Modes:
   `--run`/`-r`, `--build`, `--gen`/`-g`/`--codegen`, `--check`/`--analyze`, `--tok`/`--tokens`, `--ast`, `--sym`/`--symbols`,
   `--type`/`--types`
3. Default mode:
   `--build` when omitted.
4. Run program arguments:
   use `--` separator in new syntax.
5. Legacy command compatibility:
   first recognized legacy command token is rewritten to equivalent mode flag.
6. Target arity today:
   parser accepts list syntax, but execution fails with clear error when `len(targets) > 1`.
7. Short-flag conflict resolution:
   keep `-I` for `--runtime-include`; `--include-eof` is long-only.
8. Mode-scoped option validation:
   reject incompatible mode/flag combinations with explicit parser errors (for example, `--keep-c` is allowed only in
   `build|run`).
9. `--run --keep-c` output behavior:
   keep generated C at `./a.c` by default (same location as default `--build --keep-c`) while keeping the executable
   temporary; if `-o <name>` is provided, keep C as `<name>.c`.

## Implementation Sequence

1. Replace argparse subparsers with one parser and a mutually-exclusive mode-flag group.
2. Add legacy argv rewrite helpers and `--` runtime-args splitting logic.
3. Normalize parsed args to current command handlers (`args.entry`, `args.args` for run).
4. Dispatch via mode-to-handler map instead of subparser `set_defaults(func=...)`.
5. Keep existing command handler implementations unchanged where possible.
6. Update Stage 2 helper scripts and docs to mode-flag syntax.
7. Add parser/dispatch tests under `tests/cli` for new behavior and compatibility.

## Acceptance Criteria

1. `./l0c app.main` executes build mode.
2. `./l0c --run app.main -- a b` forwards `a b` as runtime args.
3. `./l0c --run app.main a` errors and instructs using `--`.
4. Legacy commands still work (`./l0c run app.main a`, `./l0c gen app.main`, etc.).
5. Multi-target invocation errors clearly for now.
6. CLI docs/specs/examples reflect mode-flag syntax.
7. Stage 2 helper scripts run via mode flags.

## Test Cases and Scenarios

1. Default mode dispatch to build.
2. Explicit mode dispatch for each mode flag family.
3. Legacy command rewrite and alias coverage.
4. Run-args separation with `--`.
5. Validation errors for unsupported multi-target execution.
6. Validation error when `--` program args are used outside run mode.
7. Mode/flag compatibility validation failures return argparse error (`2`) with explicit valid-mode guidance.
8. `-I` remains runtime include while `--include-eof` remains available for token dumps.

## Assumptions and Defaults

1. Compatibility shim remains intentionally simple (no deep mixed legacy/new parsing).
2. Multi-target execution semantics are deferred to a later change.
3. Existing Stage 1 command handlers remain canonical execution units.
4. Legacy command examples in historical docs/plans are not rewritten unless they describe active user workflows.
