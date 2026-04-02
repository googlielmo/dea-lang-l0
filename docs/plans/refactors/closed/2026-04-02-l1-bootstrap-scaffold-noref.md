# Refactor Plan

## Dea/L1 bootstrap scaffold and shared tooling core

- Date: 2026-04-02
- Status: Implemented
- Title: Create the Dea/L1 bootstrap scaffold, root Dea-wide plans tree, and a small shared tooling core
- Kind: Refactor
- Severity: Medium
- Stage: Shared
- Subsystem: Monorepo layout / L1 bootstrap / shared tooling
- Modules:
  - `docs/README.md`
  - `docs/reference/project-status.md`
  - `docs/plans/refactors/closed/2026-04-02-l1-bootstrap-scaffold-noref.md`
  - `scripts/dea_tooling/`
  - `l1/`
  - root monorepo guidance files
- Test modules:
  - `l1/compiler/stage1_l0/run_tests.py`
  - root and level-local make/help/bootstrap smoke checks

## Summary

Create the initial `l1/` subtree as a bootstrap-only scaffold. Seed `compiler/stage1_l0/` from the runnable L0 Stage 2
compiler baseline, retarget its public surface to `l1c` / `L1_*`, and build it with an explicit upstream L0 Stage 2
bootstrap contract.

At the same time, add a root `docs/plans/` home for Dea-wide plans and extract a small shared launcher/env/bootstrap
tooling core under root `scripts/` without prematurely generalizing the full L0 install/dist/docs stack.

## Defaults Chosen

1. Root `README.md` stays basically unchanged and L0-centered in this tranche.
2. Existing L0 user-facing docs stay in place and are not rewritten for L1 yet.
3. Local L1 development defaults to repo-local `l0/build/dea/bin/l0c-stage2`.
4. CI and future release/bootstrap validation must use an explicit upstream compiler path via `L1_BOOTSTRAP_L0C`.
5. Shared tooling extraction is intentionally narrow: launcher/env/bootstrap helpers only.

## Current State

The scaffold now includes:

1. Root `docs/plans/` plus root `docs/reference/project-status.md` for Dea-wide planning/status material.
2. A root shared tooling core under `scripts/dea_tooling/`, adopted by the current L0 launcher/env generation helpers.
3. An `l1/` subtree with:
   - `compiler/stage1_l0/` seeded from the runnable L0 Stage 2 compiler,
   - `compiler/stage2_l1/` as a placeholder,
   - shared runtime and `shared/l1/stdlib/` bootstrap assets,
   - bootstrap scripts, Makefile targets, and local guidance files,
   - an initial `l1/docs/` scaffold.
4. Public L1 bootstrap naming wired through the stage1 build/test flow:
   - `l1c`
   - `l1c-stage1`
   - `L1_HOME`
   - `L1_SYSTEM`
   - `L1_RUNTIME_INCLUDE`
   - `L1_BOOTSTRAP_L0C`
5. The copied L1 runtime header renamed to `l1_runtime.h`, with emitted C/test expectations updated accordingly.
6. The copied L1 stdlib and L1-language fixture corpus now use the `.l1` extension, while `stage1_l0` implementation
   sources and implementation tests remain `.l0`.

## Validation Snapshot

The implemented scaffold has been exercised with:

1. `make help`
2. `make -C l1 help`
3. `make -C l1 venv`
4. `make -C l0 use-dev-stage2`
5. `make -C l1 build-stage1`
6. `./l1/build/l1/bin/l1c-stage1 --version`
7. `./l1/build/l1/bin/l1c-stage1 --help`
8. `./l1/build/l1/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/src l1c`
9. `make -C l1 test-stage1`

## Follow-on Work

The scaffold work covered by this plan is implemented. The remaining items are separate follow-on efforts and are not
blockers for closing this plan:

1. Any additional Dea-wide reference documents that should move from level-local ownership into root `docs/reference/`.
2. L1 install/dist/release/docs/CI parity beyond the current bootstrap-only scaffold.
3. Any later shared-tooling extraction beyond the current narrow launcher/env/bootstrap layer.
