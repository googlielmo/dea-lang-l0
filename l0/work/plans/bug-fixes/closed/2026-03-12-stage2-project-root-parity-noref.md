# Bug Fix Plan

## Stage 2 project-root parity for path-like entry targets

- Date: 2026-03-12
- Status: Closed (fixed)
- Title: Restore Stage 2 project-root selection parity with Stage 1 for path-like entry targets
- Kind: Bug Fix
- Severity: Low
- Stage: 2
- Subsystem: CLI / source paths / build driver
- Modules:
  - `compiler/stage2_l0/src/l0c_lib.l0`
  - `compiler/stage2_l0/src/build_driver.l0`
  - `compiler/stage2_l0/src/source_paths.l0`
- Test modules:
  - `compiler/stage2_l0/tests/source_paths_test.l0`
  - `compiler/stage2_l0/tests/l0c_stage2_verbose_output_test.sh`
- Repro:
  - `diff <(./scripts/l0c -vvv examples/demo.l0 2>&1) <(build/dea/bin/l0c-stage2 -vvv examples/demo.l0 2>&1)`

## Summary

Stage 2 diverged from Stage 1 when the CLI target was path-like and no explicit `-P/--project-root` was provided. For
`examples/demo.l0`, Stage 1 normalized the target first and logged:

`Project root(s): 'examples'`

Stage 2 applied the default project root before normalizing the target, so it logged:

`Project root(s): '.','examples'`

This did not usually break resolution, but it was a real parity drift in both the effective project-root list and the
verbose stderr contract.

## Fix Implemented

1. Updated Stage 2 input preparation in both `l0c_lib.l0` and `build_driver.l0` so target normalization runs before
   default project-root insertion.
2. Preserved the Stage 1 behavior split:
   - module-name target with no `-P`: default project roots remain `'.'`
   - module-name target with explicit `-P`: keep only the explicit roots
   - path-like target with no `-P`: use only the path parent when it is not `.`
   - path-like target with explicit `-P`: keep the explicit roots plus the normalized path parent when needed
3. Added a low-level source-path regression and extended the built-artifact verbose-output regression to cover the
   `examples/demo.l0` path-target case directly.

## Verification

Executed:

```bash
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/source_paths_test.l0
bash compiler/stage2_l0/tests/l0c_stage2_verbose_output_test.sh
diff <(./scripts/l0c -vvv examples/demo.l0 2>&1) <(build/dea/bin/l0c-stage2 -vvv examples/demo.l0 2>&1)
diff <(./scripts/l0c -vvv demo -P examples 2>&1) <(build/dea/bin/l0c-stage2 -vvv demo -P examples 2>&1)
```

Observed:

1. The path-like target case no longer includes `'.'` ahead of the parent directory in Stage 2.
2. The explicit `-P examples` case remains unchanged.
3. The remaining direct diffs versus Stage 1 are expected: Stage 2 identity text and Stage 2 temp C filename shape.
