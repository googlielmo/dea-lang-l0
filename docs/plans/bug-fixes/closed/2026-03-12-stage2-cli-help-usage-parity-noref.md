# Bug Fix Plan

## Stage 2 CLI help and usage parity

- Date: 2026-03-12
- Status: Closed (fixed)
- Title: Restore Stage 2 `l0c` help and usage output parity without porting Python `argparse`
- Kind: Bug Fix
- Severity: Medium
- Stage: 2
- Subsystem: CLI / driver entrypoint
- Modules:
  - `compiler/stage2_l0/src/cli_args.l0`
  - `compiler/stage2_l0/src/l0c_lib.l0`
- Test modules:
  - `compiler/stage2_l0/tests/cli_args_test.l0`
  - `compiler/stage2_l0/tests/l0c_stage2_help_output_test.sh`
- Repro:
  - `make use-dev-stage2 && source dist/bin/l0-env.sh && l0c`
  - `make use-dev-stage2 && source dist/bin/l0-env.sh && l0c -h`

## Summary

Stage 2 currently parses the modern global-flag CLI shape but does not provide the expected usage/help UX from the
developer-facing `l0c` launcher. Running `l0c` with no arguments emits only a diagnostic, and `-h` / `--help` are
reported as unknown options. This diverges from Stage 1 and makes the stage-switchable dist workflow feel broken.

The fix should preserve the custom Stage 2 parser and dispatcher rather than port Python `argparse`. The missing
behavior is presentation-oriented: help flag detection, usage rendering, exit-code handling, and regression coverage.
The final user-visible output is intentionally Stage 2-specific where identity text is involved:
`--help` now prints `Dea language / L0 compiler (Stage 2)`, while no-argument failures keep the existing
`error: [L0C-2021] missing required target module/file name` diagnostic after the short usage banner.

## Implementation Outline

1. Teach `cli_parse()` to detect `-h` / `--help` before normal validation and return a non-error parse result that
   requests help output.
2. Add explicit Stage 2 usage/help rendering functions alongside the Stage 2 CLI definitions so the text remains local
   to the parser contract.
3. Update the Stage 2 entrypoint dispatch to print full help on explicit help requests and short usage on CLI parse
   failures before the existing diagnostics.
4. Add parser-level coverage for help requests and a built-artifact regression test that checks `--help` and the
   no-argument error path.

## Verification

Executed:

```bash
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/cli_args_test.l0
bash compiler/stage2_l0/tests/l0c_stage2_help_output_test.sh
```

Observed:

1. `cli_args_test.l0` passes with the new help-request short-circuit behavior.
2. The built Stage 2 launcher prints full help with the exact heading
   `Dea language / L0 compiler (Stage 2)` on `--help`.
3. Invoking the built Stage 2 launcher with no arguments now prints the short usage banner before the existing
   missing-target diagnostic and exits with code `2`.
