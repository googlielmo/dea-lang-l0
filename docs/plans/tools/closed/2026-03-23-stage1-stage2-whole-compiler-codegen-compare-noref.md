# Tool Plan

## Stage 1 vs Stage 2 whole-compiler `--gen` comparison

- Date: 2026-03-23
- Status: Implemented
- Title: Add an on-demand Stage 1 vs Stage 2 whole-compiler `--gen` comparison script
- Kind: Tooling
- Severity: Medium
- Stage: 2
- Subsystem: Bootstrap and codegen validation
- Modules:
  - `compiler/stage2_l0/scripts/l0c_stage1_stage2_codegen_compare.py`
  - `compiler/stage2_l0/README.md`
  - `docs/reference/c-backend-design.md`
- Test modules:
  - `compiler/stage1_py/tests/cli/test_l0c_assumptions.py`
- Repro:
  `DEA_BUILD_DIR=build/dev-dea ./.venv/bin/python ./compiler/stage2_l0/scripts/l0c_stage1_stage2_codegen_compare.py`

## Summary

The current Stage 2 backend coverage has curated golden fixtures and the strict triple-bootstrap fixed-point check, but
it lacked an easy on-demand comparison between Stage 1 and Stage 2 when both compile the full Stage 2 compiler source
tree with `--gen`.

That leaves room for a whole-program codegen drift where Stage 2 can self-host consistently while still emitting C that
differs from the Stage 1 oracle.

## Fix

- build a fresh Stage 2 compiler under `build/tests/...` from trusted Stage 1 input
- run `--gen --no-line-directives -P compiler/stage2_l0/src l0c` through Stage 1 and the fresh Stage 2 compiler
- compare the resulting C programs byte-for-byte and fail with retained artifacts plus a compact unified diff
- align Stage 1 `--gen` stdout with Stage 2 by writing the already newline-terminated generated C directly instead of
  appending an extra newline through Python `print()`
- keep the comparison outside the regular Stage 2 suite under `compiler/stage2_l0/scripts/` so it can be invoked only
  when investigating a suspected divergence
- document the new explicit invocation path in Stage 2 testing docs

## Verification

```bash
./.venv/bin/python -m pytest compiler/stage1_py/tests/cli/test_l0c_assumptions.py -k codegen_stdout_preserves_single_trailing_newline
DEA_BUILD_DIR=build/dev-dea ./.venv/bin/python ./compiler/stage2_l0/scripts/l0c_stage1_stage2_codegen_compare.py
```
