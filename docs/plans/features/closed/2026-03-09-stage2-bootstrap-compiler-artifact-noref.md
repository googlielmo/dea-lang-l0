# Feature Plan

## Bootstrap, Make workflow, and installable Stage 2 toolchain

- Date: 2026-03-10
- Status: Closed (implemented)
- Title: Bootstrap, Make workflow, and installable Stage 2 toolchain
- Kind: Feature
- Severity: High
- Stage: 2
- Subsystem: Bootstrap/build workflow / top-level Make UX / install layout
- Modules:
    - `scripts/build-stage2-l0c.sh`
    - `scripts/build_stage2_l0c.py`
    - `scripts/dist_tools_lib.py`
    - `scripts/gen_dist_tools.py`
    - `Makefile`
    - `README.md`
    - `compiler/stage2_l0/README.md`
    - `docs/reference/project-status.md`
    - `docs/reference/architecture.md`
    - `CLAUDE.md`
- Test modules:
    - `compiler/stage2_l0/tests/source_paths_test.l0`
    - `compiler/stage2_l0/tests/l0c_codegen_test.sh`
    - `compiler/stage2_l0/tests/l0c_stage2_default_dist_test.sh`
    - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`
    - `compiler/stage2_l0/tests/l0c_stage2_install_prefix_test.sh`
    - `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`
    - `tests/test_make_dist_workflow.py`

## Summary

This feature defines a staged path from today’s repo-only Stage 2 execution model to a user-facing Stage 2 compiler
artifact and, later, to a real installable toolchain.

Triple-bootstrap self-hosting validation and the strict triple-compilation test are tracked separately in
`docs/plans/features/closed/2026-03-11-triple-bootstrap-self-hosting-noref.md`. That follow-on work depends on
this plan’s Phase 1 and Phase 2 deliverables, but it does not replace this plan’s Phase 3 install-prefix scope.

The plan had three phases, and all three are now implemented:

1. Phase 1 builds a standalone Stage 2 compiler artifact under `build/stage2/bin` from the Stage 1 compiler.
2. Phase 2 adds a top-level `Makefile` that centralizes the repo-local developer workflow under `dist/bin`.
3. Phase 3 extends that workflow into a repo-independent install prefix with copied shared stdlib/runtime assets and
   installs the self-hosted Stage 2 compiler (`Compiler 2` in the triple-bootstrap chain), not the initial Stage 1
   bootstrap artifact.

The feature is Stage-2-first. Stage 1 remains the bootstrap compiler throughout these phases, but only Phase 2 needs a
repo-local `l0c-stage1` wrapper. Phase 3 does not require Stage 1 to be installed into the final prefix.

## Goals

1. Produce a concrete, runnable Stage 2 compiler artifact as the first deliverable.
2. Centralize the common developer workflow under one top-level `Makefile`.
3. Support repo-local alias switching between Stage 1 and Stage 2 without replacing the source-tree Stage 1 wrapper.
4. Preserve a clean path from repo-local developer tooling to a later repo-independent install prefix.
5. Keep Stage 1 as the bootstrap builder until a separate plan explicitly changes that.

## Non-Goals

1. Replacing the source-tree Stage 1 wrapper with Stage 2 in this feature.
2. Requiring Stage 2 self-hosting in this feature; that work is tracked in
   `docs/plans/features/closed/2026-03-11-triple-bootstrap-self-hosting-noref.md`.
3. Making Stage 1 independently installable under the final Phase 3 prefix.
4. Defining system package-manager integration.
5. Introducing multiple competing developer entrypoints once the `Makefile` exists.

## Public Interface and Deliverables

### Phase 1: built Stage 2 compiler artifact — COMPLETE

Phase 1 introduces a low-level builder:

1. `scripts/build-stage2-l0c.sh`

Its job is to invoke the Stage 1 compiler on `compiler/stage2_l0/src/l0c.l0` and produce a runnable Stage 2 compiler
artifact.

Default output:

1. `build/stage2/bin/l0c-stage2`
2. `build/stage2/bin/l0c-stage2.native`

Optional retained C output when requested:

1. `build/stage2/bin/l0c-stage2.c`

`l0c-stage2` is a small POSIX shell launcher. It must:

1. compute the repo root relative to itself,
2. set `L0_HOME` to the repo `compiler/` directory when unset,
3. leave `L0_SYSTEM` unset so normal compiler defaults apply,
4. exec the sibling native binary unchanged.

Phase 1 output is meant to be directly usable from a normal repo checkout:

```bash
./scripts/build-stage2-l0c.sh
./build/stage2/bin/l0c-stage2 --check -P examples hello
./build/stage2/bin/l0c-stage2 --gen -P examples hello
```

Phase 1 also adds one forward-compatibility hook for later phases:

1. the builder supports a repo-local output-root override via `DIST_DIR=<path>`

Phase 1 `DIST_DIR` must resolve to a strict subdirectory inside the repository so the generated launcher can compute
the repo root relative to itself. That override exists so Phase 2 and Phase 3 can reuse the same build logic instead
of reimplementing it.

Phase 1 also enables a more efficient Stage 2 codegen golden-test path:

1. `compiler/stage2_l0/tests/l0c_codegen_test.sh` should build a fresh Stage 2 compiler once before iterating fixtures,
2. it should use a dedicated repo-local test output root under `build/tests/...`, not the default `build/stage2`,
3. it should reuse that built `l0c-stage2` wrapper for all fixture `--gen` invocations in the same script run.

### Phase 2: repo-local top-level Make workflow

Phase 2 adds a top-level `Makefile` as the canonical repo-local developer entrypoint.

Repo-local dist root:

1. default: `DIST_DIR=dist`
2. override: `make DIST_DIR=build/dev-dist ...`

Phase 2 layout:

1. `<DIST_DIR>/bin/l0c-stage1`
2. `<DIST_DIR>/bin/l0c-stage2`
3. `<DIST_DIR>/bin/l0c-stage2.native`
4. `<DIST_DIR>/bin/l0-env.sh`
5. `<DIST_DIR>/bin/l0c` as an explicit symlink to either `l0c-stage1` or `l0c-stage2`

Phase 2 is intentionally repo-centric:

1. wrappers compute the repo root relative to themselves,
2. `l0-env.sh` may set `L0_HOME` to the repo `compiler/`,
3. Phase 2 does not copy `compiler/shared/...` into `dist/`,
4. Phase 2 does not try to make `dist/` relocatable outside the repo.
5. new implementation helpers may be written in Python even though the generated launchers remain shell scripts.

Public Make targets:

1. `help`
2. `venv`
3. `install-dev-stage1`
4. `install-dev-stage2`
5. `install-dev-stages`
6. `use-dev-stage1`
7. `use-dev-stage2`
8. `test-stage1`
9. `test-stage2`
10. `test-stage2-trace`
11. `triple-test`
12. `test-all`
13. `docs`
14. `docs-pdf`
15. `clean`
16. `clean-dist`

Target behavior:

1. `venv` creates or reuses `./.venv`, preferring `uv` when available and falling back to `python -m venv`.
2. `install-dev-stage1` writes `<DIST_DIR>/bin/l0c-stage1`.
3. `install-dev-stage2` builds and installs the Phase 1 artifact into `<DIST_DIR>/bin`.
4. `install-dev-stages` installs both stage-specific commands and does not rewrite `<DIST_DIR>/bin/l0c`.
5. `use-dev-stage1` and `use-dev-stage2` are the only targets that switch `<DIST_DIR>/bin/l0c`.
6. `use-dev-stage1` and `use-dev-stage2` print the exact `source <DIST_DIR>/bin/l0-env.sh` command to run next.
7. `test-stage1` ensures the local virtual environment exists, then runs `python -m pytest -n auto` from `./.venv`.
8. `test-stage2` runs `./compiler/stage2_l0/run_tests.py`.
9. `test-stage2-trace` runs `./compiler/stage2_l0/run_trace_tests.py`.
10. `test-all` runs the three test targets above.
11. `triple-test` runs `./compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py` only as a convenience entrypoint for
    the separately tracked strict bootstrap fixed-point regression.
12. `docs` runs `./scripts/gen-docs.sh`.
13. `docs-pdf` runs `./scripts/gen-docs.sh --pdf`.

Phase 2 `l0-env.sh` behavior:

1. it must be sourced,
2. it computes the repo root relative to itself,
3. it exports `L0_HOME="$repo_root/compiler"`,
4. it activates `"$repo_root/.venv/bin/activate"` if present,
5. it prepends `<DIST_DIR>/bin` to `PATH`,
6. it does not force `L0_SYSTEM`.

Compiler selection in Phase 2 is expressed by the `l0c` symlink, not by a new environment variable.

### Phase 3: repo-independent install prefix

Phase 3 turns the repo-local workflow into a true install layout.

Canonical install variable:

1. `PREFIX`

Supported examples:

1. `PREFIX=dist`
2. `PREFIX=/tmp/l0-install`
3. `PREFIX=/usr/local`

Phase 3 required install layout:

1. `<PREFIX>/bin/l0c-stage2`
2. `<PREFIX>/bin/l0c-stage2.native`
3. `<PREFIX>/bin/l0c`
4. `<PREFIX>/bin/l0-env.sh`
5. `<PREFIX>/shared/l0/stdlib/...`
6. `<PREFIX>/shared/runtime/...`

The `shared/...` trees are copied from:

1. `compiler/shared/l0/stdlib`
2. `compiler/shared/runtime`

Phase 3 is repo-independent:

1. installed wrappers and `l0-env.sh` must derive paths from `PREFIX`, not from the repo checkout,
2. the installed Stage 2 compiler must work after the repository is moved or removed,
3. `l0-env.sh` must set `L0_HOME="$PREFIX"` and derive `L0_SYSTEM` and `L0_RUNTIME_INCLUDE` from it when unset,
4. `install` must scrub inherited `L0_SYSTEM`, `L0_RUNTIME_INCLUDE`, and `L0_RUNTIME_LIB` during its internal
   self-hosted rebuild so a caller shell sourced from an installed prefix cannot redirect Compiler 2 bootstrap inputs
   away from the repo source tree.

Phase 3 does not require `l0c-stage1` to be installed into the final prefix.

## Key Implementation Changes

1. Keep `scripts/build-stage2-l0c.sh` as the single low-level builder for Stage 2, and make it reusable by later
   phases through the repo-local `DIST_DIR` override.
2. Keep Stage 2 default-root behavior aligned with Stage 1: explicit `-S/--sys-root` wins, `L0_SYSTEM` is
   authoritative, and `L0_HOME/shared/l0/stdlib` is the fallback.
3. Make `compiler/stage2_l0/tests/l0c_codegen_test.sh` consume a freshly built Phase 1 artifact once per script run
   instead of rebuilding Stage 2 through Stage 1 for every golden fixture.
4. Keep codegen-test bootstrap artifacts isolated under `build/tests/...` so the regression harness does not interfere
   with a developer-managed `build/stage2` checkout artifact.
5. Add the top-level `Makefile` only in Phase 2; it is the developer UX layer, not a second compiler driver.
6. Structure wrapper and env-script generation so there are two modes:
    1. repo-relative mode for Phase 2
    2. prefix-relative mode for Phase 3
7. Keep Phase 3 Stage-2-first: copied shared assets and installed Stage 2 are mandatory; Stage 1 packaging is deferred
   and not required by this plan.
8. Keep `install` shell-state-independent: its temporary self-hosted rebuild must not consume caller-provided
   installed-prefix `L0_*` paths.

## Test Plan

### Phase 1

1. Running `./scripts/build-stage2-l0c.sh` creates `l0c-stage2` and `l0c-stage2.native`.
2. Output-root override writes the same artifact shape under the alternate root.
3. `./build/stage2/bin/l0c-stage2 --check -P examples hello` succeeds.
4. `./build/stage2/bin/l0c-stage2 --gen -P examples hello` succeeds if `--gen` is implemented at execution time.
5. `source_paths` unit tests cover:
    1. no env values,
    2. `L0_SYSTEM` precedence,
    3. `L0_HOME` fallback,
    4. explicit sys-root suppression of defaults.
6. `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh` bootstraps Stage 2 under a dedicated repo-local
   `build/tests/...` root and validates the built wrapper end to end.
7. `compiler/stage2_l0/tests/l0c_stage2_default_dist_test.sh` keeps coverage of the builder default
   `build/stage2/bin` destination without leaving `build/stage2` behind after cleanup.
8. `compiler/stage2_l0/tests/l0c_codegen_test.sh` bootstraps Stage 2 once into a dedicated repo-local
   `build/tests/...` root and reuses that built wrapper across all golden fixtures in the same run.

### Phase 2

1. `make venv`
2. `make install-dev-stage1`
3. `make install-dev-stage2`
4. `make install-dev-stages`
5. `make use-dev-stage1`
6. `make use-dev-stage2`
7. `make DIST_DIR=build/dev-dist install-dev-stages`
8. `make DIST_DIR=build/dev-dist use-dev-stage2`
9. after sourcing `<DIST_DIR>/bin/l0-env.sh`, `l0c --check -P examples hello` succeeds with Stage 1 selected
10. after sourcing `<DIST_DIR>/bin/l0-env.sh`, `l0c --check -P examples hello` succeeds with Stage 2 selected
11. `make test-stage1`
12. `make test-stage2`
13. `make test-stage2-trace`
14. `make triple-test`
15. `make test-all`
16. `make docs`
17. `make docs-pdf`

### Phase 3

1. `make PREFIX=/tmp/l0-install install`
2. `source /tmp/l0-install/bin/l0-env.sh`
3. `/tmp/l0-install/bin/l0c --check -P <project> <module>` succeeds
4. `/tmp/l0-install/bin/l0c-stage2 --gen ...` succeeds
5. stdlib resolves from `<PREFIX>/shared/l0/stdlib`
6. runtime headers resolve from `<PREFIX>/shared/runtime`
7. no repo-relative dependency on `compiler/shared/...` remains
8. `install` still succeeds when the caller shell exports installed-prefix `L0_HOME`, `L0_SYSTEM`, and
   `L0_RUNTIME_INCLUDE`; those values must not affect the internal self-hosted rebuild
9. `install` installs the self-hosted Stage 2 compiler (`Compiler 2`), not the initial Stage 1-built artifact

## Assumptions and Defaults

1. Phase 1 is the concrete first deliverable: a built Stage 2 compiler artifact under `build/stage2/bin`.
2. Phase 2 is repo-local developer tooling under `dist/`; it is not yet a real install story.
3. Phase 3 is the first phase that promises a relocatable, repo-independent install prefix.
4. `DIST_DIR` is reserved for Phase 2 repo-local workflow; `PREFIX` is the install root for Phase 3.
5. Alias switching for `l0c` remains explicit and is never an implicit side effect of install targets.
6. New utility helpers are acceptable where they reduce duplication or isolate path-generation policy.
7. Phase 2 `DIST_DIR` values must stay inside the repository; outside-repo install roots are deferred to Phase 3.
8. All new L0 code added while implementing this feature should use Doxygen Javadoc-style comments with autobrief.
