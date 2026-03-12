# Feature Plan

## Add a stable shared CLI contract spec for Stage 1 and Stage 2

- Date: 2026-03-12
- Status: Draft
- Title: Define a stable shared CLI contract under `docs/specs/` for Stage 1 and Stage 2 compiler behavior
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: CLI / specs / source-path normalization
- Modules:
    - `docs/specs/compiler/stage1-contract.md`
    - `docs/specs/compiler/cli-contract.md`
    - `docs/reference/architecture.md`
- Test modules:
    - `compiler/stage1_py/tests/cli/test_cli_mode_flags.py`
    - `compiler/stage2_l0/tests/cli_args_test.l0`
    - `compiler/stage2_l0/tests/l0c_stage2_help_output_test.sh`
    - `compiler/stage2_l0/tests/l0c_stage2_verbose_output_test.sh`

## Summary

The repository currently has one compiler contract doc for Stage 1 only:
`docs/specs/compiler/stage1-contract.md`.
That file mixes Stage 1-specific details with behavior that is intended to be shared across both stages, especially in
the CLI surface, mode flags, mode-scoped option validation, target normalization, search-path behavior, and exit-code
rules.

This creates two problems:

1. Shared CLI behavior has no stable normative home, so Stage 2 parity work depends on reading Stage 1 code and old
   plans instead of a spec.
2. Small cross-stage parity questions, such as path-like target normalization and effective project-root selection,
   are easy to treat as implementation quirks rather than contract behavior.

The fix is to add a dedicated shared CLI contract under `docs/specs/compiler/` and narrow
`stage1-contract.md` so it points to that shared spec rather than silently acting as the only oracle.

## Implementation

1. Add a new spec file, `docs/specs/compiler/cli-contract.md`, with `Version: YYYY-MM-DD`.
2. Scope the new shared spec to behavior that is intended to be stage-independent:
    - supported mode flags and global options
    - mode selection rules
    - `--` separator behavior
    - mode-scoped option validity
    - target normalization rules for dotted names, `.l0` paths, absolute paths, and parent-containing paths
    - default project-root and system-root behavior
    - search precedence
    - compiler identity/help/version expectations where shared
    - exit-code rules where shared
3. Keep stage-specific text out of the shared spec unless the difference is explicit and concrete.
4. Update `docs/specs/compiler/stage1-contract.md` so it becomes a Stage 1 contract plus navigation index that points
   to `cli-contract.md` for shared CLI behavior instead of restating or owning the shared rules.
5. Update any nearby reference docs that currently imply `stage1-contract.md` is the only CLI contract, especially
   cross-links in `docs/reference/architecture.md` if needed.
6. Do not create a separate Stage 2 contract in this change; the goal is one shared CLI spec plus the existing
   Stage 1-specific contract.

## Verification

Execute:

```bash
rg -n "cli-contract|stage1-contract" docs/specs docs/reference
python3 -m pytest compiler/stage1_py/tests/cli/test_cli_mode_flags.py
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/cli_args_test.l0
bash compiler/stage2_l0/tests/l0c_stage2_help_output_test.sh
bash compiler/stage2_l0/tests/l0c_stage2_verbose_output_test.sh
```

Expected:

1. The shared CLI rules have one normative home under `docs/specs/compiler/cli-contract.md`.
2. `stage1-contract.md` still describes Stage 1-specific guarantees but no longer acts as the accidental owner of
   shared CLI normalization details.
3. Existing Stage 1 and Stage 2 CLI parity tests still pass after the documentation split and cross-link updates.
