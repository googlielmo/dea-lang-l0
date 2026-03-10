# Bug Fix Plan

## Stage 2 source-path defaults ignored documented `L0_HOME` stdlib fallback

- Date: 2026-03-10
- Status: Closed (fixed)
- Title: Restore Stage 2 source-root defaulting parity with Stage 1 by honoring the `L0_HOME/shared/l0/stdlib` fallback
- Kind: Bug Fix
- Severity: Medium (direct Stage 2 artifact failed to resolve `std.*` without explicit `L0_SYSTEM`)
- Stage: 2
- Subsystem: Driver / source path resolution
- Modules:
    - `compiler/stage2_l0/src/source_paths.l0`
    - `scripts/build-stage2-l0c.sh`
- Test modules:
    - `compiler/stage2_l0/tests/source_paths_test.l0`
    - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`
- Repro:
    - `env -i PATH="$PATH" L0_HOME="$PWD/compiler" /tmp/l0c-stage2.native --check -P examples hello`

## Summary

Stage 2 source-path defaulting previously read only `L0_SYSTEM` when no explicit `-S/--sys-root` roots were provided.
That behavior did not match the documented environment contract shared by the repository wrappers and Stage 1, where
`L0_HOME` is the base for deriving the default stdlib root at `shared/l0/stdlib`.

The gap was mostly hidden during normal source-tree execution because `./l0c` runs through Stage 1 first, and Stage 1
initializes `L0_SYSTEM` from `L0_HOME`. The new Phase 1 bootstrap artifact exposed the mismatch because its launcher
intentionally sets `L0_HOME` but leaves `L0_SYSTEM` unset.

## Root Cause

`compiler/stage2_l0/src/source_paths.l0` implemented only this precedence:

1. explicit `-S/--sys-root`
2. `L0_SYSTEM`
3. otherwise no system roots

That omitted the repo-wide fallback established by the shared-assets layout work and used by Stage 1:

1. explicit `-S/--sys-root`
2. `L0_SYSTEM`
3. `L0_HOME/shared/l0/stdlib`

As a result, a directly built Stage 2 binary could not resolve `std.io` and other stdlib modules when launched with
only `L0_HOME` configured.

## Fix Implemented

1. Update Stage 2 source-path defaulting to match Stage 1 precedence:
   explicit sys-root suppresses defaults, then `L0_SYSTEM`, then `L0_HOME/shared/l0/stdlib`.
2. Keep `L0_SYSTEM` authoritative when set.
3. Add a focused Stage 2 unit test for:
   no env values, `L0_SYSTEM` precedence, `L0_HOME` fallback, and explicit sys-root suppression.
4. Add an end-to-end bootstrap regression that builds `l0c-stage2` and verifies direct `--check`/`--gen` execution
   through the generated launcher.

## Verification

Executed:

```bash
./l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/source_paths_test.l0
./compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh
./compiler/stage2_l0/run_tests.sh
./compiler/stage2_l0/run_trace_tests.sh
```

Observed:

1. `source_paths_test` covers the missing fallback and precedence rules.
2. The bootstrap artifact works when only `L0_HOME` is injected by the wrapper.
3. The full Stage 2 test suite remains green.
4. The full Stage 2 trace suite remains green.

## Assumptions

- The Stage 1 environment-default contract is the oracle for equivalent Stage 2 root-resolution behavior.
- The bootstrap launcher should continue leaving `L0_SYSTEM` unset so default-path derivation remains centralized in
  compiler logic.
