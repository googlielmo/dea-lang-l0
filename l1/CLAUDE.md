# CLAUDE.md

Guidance for Claude Code and AI agents working in the `l1/` subtree of the Dea monorepo.

Read `../CLAUDE.md` first for monorepo-wide policy, commit conventions, planning policy, shared `.venv`, and quality
standards.

Run commands from the `l1/` directory.

## Project Overview

Dea/L1 is in bootstrap-scaffold status.

- `compiler/stage1_l0/` is the initial L1 compiler seed implemented in Dea/L0.
- `compiler/stage2_l1/` is a placeholder for the future self-hosted L1 compiler.
- `compiler/shared/runtime/` is the copied shared runtime tree.
- `compiler/shared/l1/stdlib/` is the copied L1 stdlib seed.

## Bootstrap Contract

- Local development defaults to the repo-local upstream L0 Stage 2 compiler at `../l0/build/dea/bin/l0c-stage2`.
- Prepare that default with `make -C ../l0 use-dev-stage2`.
- Override the upstream compiler explicitly with `L1_BOOTSTRAP_L0C=/path/to/l0c-stage2`.
- Do not rely on whichever `l0c` happens to be active on `PATH`.

## Commands

```bash
make venv
make use-dev-stage1
source build/dea/bin/l1-env.sh
l1c --help
l1c --version
make check-examples
make test-stage1
make test-all
```

## Current Scope

- This subtree is bootstrap-only for now.
- There is no L1 install/dist/release/docs-publish workflow yet.
- Keep root `README.md` and existing L0 user-facing docs unchanged unless the task explicitly requires a minimal
  consistency fix.
