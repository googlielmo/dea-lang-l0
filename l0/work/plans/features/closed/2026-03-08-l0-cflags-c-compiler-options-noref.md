# Feature Plan

## Add `L0_CFLAGS` as default C compiler options with CLI-last merge semantics

- Date: 2026-03-08
- Status: Closed (implemented)
- Title: Support `L0_CFLAGS` in Stage 1 and Stage 2 CLI plumbing, merged with `--c-options`
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: CLI/build option resolution (`l0c`), compiler-driver option precedence
- Modules:
  - `compiler/stage1_py/l0c.py`
  - `compiler/stage2_l0/src/l0c.l0`
  - `README.md`
  - `docs/specs/compiler/stage1-contract.md`
- Test modules:
  - `compiler/stage1_py/tests/cli/test_l0c_assumptions.py`
  - `compiler/stage2_l0/tests/l0c_test.l0`
- Repro: `L0_CFLAGS="-DNDEBUG -fno-omit-frame-pointer" ./l0c -C "-g" hello.l0`

## Summary

Introduce `L0_CFLAGS` so users can set default C compiler flags from the environment while preserving existing
`--c-options` behavior.

Final policy in this feature:

1. `L0_CFLAGS` and `--c-options` are additive.
2. Merge order is deterministic: environment options first, CLI options second.
3. Tokenization remains whitespace-based (same model as existing `--c-options` splitting).

## Public Interface / CLI Behavior

1. New environment variable contract: `L0_CFLAGS` provides extra C compiler flags/options for `--build` and `--run`
   paths.
2. Precedence/ordering contract: effective option vector is `split(L0_CFLAGS) + split(--c-options)`.
3. No shell-style quote parsing is introduced in this iteration.

## Detailed Behavior

### Stage 1 (`compiler/stage1_py/l0c.py`)

1. Add `_split_c_options(raw_options)` helper and reuse it for both env and CLI sources.
2. In `cmd_build`, collect:
   - `env_opts = split($L0_CFLAGS)`
   - `cli_opts = split(args.c_options)`
   - `extra_opts = env_opts + cli_opts`
3. Use merged `extra_opts` for:
   - emitted C compiler command arguments,
   - optimization-default suppression in `_get_optimize_flag` (for example `-O*` in env or CLI suppresses auto `-O1`).
4. Update `--c-options` help text to document the `L0_CFLAGS` prepend behavior.

### Stage 2 (`compiler/stage2_l0/src/l0c.l0`)

1. Add pure helper functions for option splitting/merging:
   - `l0c_append_c_option_words`
   - `l0c_merge_c_option_words`
   - `l0c_collect_c_option_words`
2. Resolve options from `env_get("L0_CFLAGS")` and `opts.c_options` with the same env-first, CLI-last semantics.
3. Keep `--build` and `--run` NYI; this feature adds resolution plumbing for forward parity without changing NYI status.

## Implementation Sequence

1. Add Stage 1 option-splitting helper and merge logic.
2. Wire merged options into compile command and optimization-flag decision path.
3. Add Stage 1 tests for env-only and env+CLI ordering scenarios.
4. Add Stage 2 merge helpers and invoke collection in NYI run/build dispatch paths.
5. Add Stage 2 tests that validate merge order and empty-input handling.
6. Update user-facing docs (`README.md`, Stage 1 contract spec).

## Acceptance Criteria

1. Stage 1 build command includes `L0_CFLAGS` options when `--c-options` is absent.
2. When both are present, Stage 1 command places env options before CLI options.
3. Stage 1 optimization-default logic observes merged flags (for example `-O*` suppression and debug-flag behavior).
4. Stage 2 exposes testable merge helpers with the same ordering semantics.
5. Stage 2 `--build`/`--run` remain NYI and continue returning NYI diagnostics.
6. Documentation explicitly lists `L0_CFLAGS` and merge policy.

## Test Cases and Scenarios

1. Stage 1: env-only flags are propagated to compiler args.
2. Stage 1: env+CLI flags are merged with env-first ordering.
3. Stage 1: merged flags influence auto-optimization selection as expected.
4. Stage 2: merge helper returns expected env-first + CLI-second sequence.
5. Stage 2: merge helper ignores null/blank inputs safely.

## Verification

Executed during implementation:

```bash
cd compiler/stage1_py && pytest tests/cli/test_l0c_assumptions.py
./l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/l0c_test.l0
./compiler/stage2_l0/run_tests.sh
```

## Assumptions and Defaults

1. `L0_CFLAGS` is intended for default global C flags; per-invocation tuning stays on `--c-options`.
2. Whitespace splitting is sufficient for current CLI/env contract and matches existing behavior.
3. Stage 2 build/run backend invocation remains outside this feature scope.

## Non-Goals

1. Implementing shell-quote aware argument parsing for `L0_CFLAGS` or `--c-options`.
2. Implementing Stage 2 `--build`/`--run` backend compilation pipeline.
3. Introducing additional env vars for C linker behavior in this change.

## Related Docs

- `docs/specs/compiler/stage1-contract.md`
- `docs/reference/project-status.md`
- `README.md`
