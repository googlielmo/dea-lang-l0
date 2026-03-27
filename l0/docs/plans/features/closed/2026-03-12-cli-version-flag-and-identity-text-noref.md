# Feature Plan

## Add shared CLI identity text and `--version` to Stage 1 and Stage 2

- Date: 2026-03-12
- Status: Closed (implemented)
- Title: Add `--version` and shared compiler identity text for both compiler stages
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: CLI
- Modules:
  - `compiler/stage1_py/l0c.py`
  - `compiler/stage2_l0/src/cli_args.l0`
  - `compiler/stage2_l0/src/l0c_lib.l0`
- Test modules:
  - `compiler/stage1_py/tests/cli/test_cli_mode_flags.py`
  - `compiler/stage2_l0/tests/cli_args_test.l0`
  - `compiler/stage2_l0/tests/l0c_stage2_help_output_test.sh`

## Summary

Both compiler stages need a stable `--version` flag and a shared user-facing identity string that also appears at the
top of `--help`. The returned string should come from a function rather than being inlined so a later change can replace
it with a semantic version, commit hash, build id, or similar metadata without reshaping the CLI code.

Final exact outputs:

- Stage 1 `--version`: `Dea language / L0 compiler (Stage 1)`
- Stage 2 `--version`: `Dea language / L0 compiler (Stage 2)`

The same stage-specific text is used as the help heading, and `-v` emits that exact line on stderr through the normal
info-level logging path even when the command then fails with usage such as `l0c -v`.

## Implementation

1. Introduce a small compiler identity/version text function in each stage.
2. Wire Stage 1 `argparse` to use that function for both the help description and `--version`.
3. Extend the Stage 2 custom parser with a `--version` short-circuit and a printer that emits the same text.
4. Update help output in both stages to use the shared text, and emit the same text on normal verbose runs.
5. Add targeted regression tests.

## Verification

Executed:

```bash
python3 -m pytest compiler/stage1_py/tests/cli/test_cli_mode_flags.py
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/cli_args_test.l0
bash compiler/stage2_l0/tests/l0c_stage2_help_output_test.sh
```

Observed:

1. Stage 1 `--help` and `--version` both use `Dea language / L0 compiler (Stage 1)`.
2. Stage 2 `--help` and `--version` both use `Dea language / L0 compiler (Stage 2)`.
3. `-v` emits the same stage-specific identity line on successful runs and on missing-target usage failures in both
   stages.
