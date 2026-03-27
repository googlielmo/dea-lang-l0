# Refactor Plan

## Monorepo restructuring for multi-level language development

- Date: 2026-03-24
- Status: In Progress
- Title: Restructure repository into a monorepo layout supporting Dea/L0, L1, and future language levels
- Kind: Refactor
- Severity: Medium
- Stage: Shared
- Subsystem: Repository layout / build workflow / CI / documentation
- Modules:
  - All current top-level files and directories
- Test modules:
  - All existing test suites (must remain green after migration)

## Prerequisite

This plan is executed **after Dea/L0 1.0 is released** and only after both the disposable-clone drill and the disposable
GitHub hosted-workflow rehearsal pass. Until then, the current flat layout is preserved.

## Summary

Restructure the single-language repository into a monorepo where each language level (`l0/`, `l1/`, `l2/`, ...) is a
self-contained subtree. Shared vendor tools and monorepo policy files live at the repository root. While the repository
is still effectively L0-only, the root `README.md` remains the main public landing page, and monorepo-specific guidance
lives in `MONOREPO.md`.

## Goals

1. Each language level is an autonomous project with its own compiler, docs, tests, scripts, and Makefile.
2. The bootstrap chain between levels is explicit: L1 Stage 1 is compiled by L0 Stage 2, L2 Stage 1 by L1 Stage 2, etc.
3. Shared vendor tools (currently `tools/m.css`) live at the monorepo root and are referenced by all levels.
4. The root `Makefile` remains minimal monorepo orchestration only: `help`, `venv`, and `clean`.
5. Python tooling is shared through a single root `.venv` and a single root `.pre-commit-config.yaml`.
6. CI workflows are per-level with explicit shared-input triggers when needed.
7. The tree move lands as a rename-focused migration, with all required operational rewiring validated in the same
   tranche.

## Non-Goals

- Extracting `dist_tools_lib.py` or docgen into shared libraries (deferred until L1 needs them).
- Designing L1 CI workflows (deferred until L1 exists).
- Changing any L0 functionality, semantics, or public interfaces.
- Creating a second root command namespace for L0-specific targets.

## Target Layout

```
dea/
  l0/                               current repo contents (minus shared vendor tools and root policy files)
    compiler/
      stage1_py/
      stage2_l0/
      shared/
      docgen/
    docs/
    examples/
    tests/
    scripts/
    Makefile
    CLAUDE.md
    README.md                       short subtree pointer during the L0-only monorepo phase
    README-WINDOWS.md
    CONTRIBUTING.md
    SECURITY.md
    LICENSE-MIT
    LICENSE-APACHE
    pyproject.toml
    ...
  tools/
    m.css/                          vendor (language-agnostic)
    m.css.L0-PATCHES.md
  .github/
    workflows/
      l0-ci.yml                     L0 CI (paths: l0/** plus shared root inputs)
      l0-release.yml                L0 release (tag-triggered)
      l0-snapshot.yml               L0 snapshot (manual dispatch)
      l0-docs-validate.yml
      l0-docs-publish.yml
      copyright-headers.yml
  .pre-commit-config.yaml           monorepo-wide hook policy
  .venv/                            shared repo-local Python environment
  Makefile                          root monorepo orchestration (`help`, `venv`, `clean`)
  README.md                         canonical public landing page during the L0-only phase
  MONOREPO.md                       monorepo structure and root-workflow guidance
  CLAUDE.md                         root-level AI guidance
  AGENTS.md
  THIRD_PARTY_NOTICES               vendor license manifest
  .gitignore
```

When L1 is created:

```
dea/
  l0/                               unchanged ownership model
  l1/
    compiler/
      stage1_l0/                    L1 compiler written in L0
      stage2_l1/                    L1 self-hosting compiler
      shared/
      docgen/
    docs/
    examples/
    tests/
    scripts/
    Makefile
    CLAUDE.md
    README.md
  tools/
    m.css/                          shared
  .venv/                            still shared unless future incompatibilities require a new model
  ...
```

## Design Decisions

### D1: Everything language-specific moves inside `l0/`

All current content moves into `l0/`, including docs, scripts, examples, tests, and Python tooling configuration. Shared
extraction happens only when a second consumer exists.

### D2: Vendor tools live at the monorepo root

`tools/m.css/`, `tools/m.css.L0-PATCHES.md`, and `THIRD_PARTY_NOTICES` live at the root. `m.css` is language-agnostic
and will be reused by future levels.

### D3: Root Makefile is monorepo orchestration only

The root `Makefile` owns only:

- `help`
- `venv`
- `clean`

It does not expose `l0-*` dispatcher aliases. `DEA_LEVEL_DIRS` is the explicit registry of available language levels.
Level-specific workflows remain `cd <level> && make ...`.

### D4: Root `.venv` is shared across levels

The repository uses one shared repo-local Python virtual environment at `/.venv`. Level-local `make venv` targets
populate or reuse that environment instead of creating `l0/.venv`, `l1/.venv`, and so on.

### D5: Root `.pre-commit-config.yaml` is monorepo policy

Pre-commit configuration is owned at the repository root and applies across levels and root-owned docs/tooling. Hook
paths resolve from the monorepo root, and vendored content such as `tools/m.css/**` is excluded from authored-Markdown
formatting.

### D6: Root README remains the public landing page during the L0-only phase

While Dea is still effectively an L0-only repository, the root `README.md` remains the canonical project overview and
quickstart. It carries a short monorepo note near the top and links to `MONOREPO.md` for repository-structure and
root-only workflow guidance.

### D7: `l0/README.md` is intentionally a short pointer for now

During the L0-only monorepo phase, `l0/README.md` is a short local note that points readers back to the root `README.md`
and to nearby subtree docs such as `README-WINDOWS.md` and `CONTRIBUTING.md`. When L1 becomes the primary root
narrative, the full L0 README can return under `l0/`.

### D8: CI workflows live under root `.github/workflows/`

GitHub Actions requires workflows under the repository root `.github/workflows/`. Per-level path filters ensure each
workflow triggers on the level subtree plus any shared root-owned inputs it consumes.

## Implementation Phases

### Phase 1: Prepare (pre-migration)

1. Audit all hardcoded paths in CI workflows, scripts, Makefile, docs, and pre-commit hooks.
2. List every file that references `tools/m.css` and will need a path update after the move.
3. Ensure all tests pass on the current layout (`make test-all`).
4. Tag the L0 1.0 release on the current flat layout.

### Phase 2: Drill migration in a disposable local clone

1. Create a fresh local clone of the repository outside the main working tree.
2. Perform the full planned monorepo migration in the clone, including:

- moving the current tree under `l0/`
- promoting shared root-owned assets such as `tools/m.css` and `THIRD_PARTY_NOTICES`
- adding the root `Makefile`, root `README.md`, `MONOREPO.md`, and root `CLAUDE.md`
- updating workflow triggers, working directories, path-sensitive scripts, and root-owned policy files

3. Run the full post-migration verification suite in the clone:

- `cd l0 && make test-all`
- `cd l0 && make dist`
- `cd l0 && make docs`
- `make help`
- `make venv`

4. Validate local operational behavior in the clone:

- docs generation still finds root `tools/m.css`
- Stage 1 and Stage 2 helpers resolve Python from `../.venv`
- pre-commit runs from the root config and excludes vendored Markdown
- release, snapshot, and docs workflows still resolve the correct paths
- shared-input workflow triggers are configured for `l0/**`, `tools/**`, `.github/workflows/**`, and relevant root files

5. Record every path correction, workflow fix, and unexpected breakage found during the drill, then fold those findings
   back into the real migration checklist.

### Phase 3: Hosted workflow rehearsal in a disposable GitHub repository

1. Push the migrated drill clone to a disposable GitHub repository created only for migration validation.
2. Enable GitHub Actions in the disposable repository and configure the minimum required repository settings,
   permissions, and secrets for the workflows under test.
3. Trigger the migrated workflows in the disposable repository:

- normal CI on `l0/**` changes
- CI and docs validation on shared-input changes such as `tools/**`, `.github/workflows/**`, and relevant root files
- manual `workflow_dispatch` flows for snapshot, release, and docs publishing where applicable

4. Verify hosted behavior, not just local command success:

- workflow path filters fire when expected
- `working-directory` and relative paths resolve under the new `l0/` layout
- reusable workflow calls still resolve correctly
- uploaded artifacts, release assets, and docs artifacts have the expected names and contents

5. Capture every GitHub-only issue found in the rehearsal, especially trigger gaps, missing permissions, broken artifact
   paths, or release and docs publishing regressions.
6. Treat successful hosted rehearsal in the disposable repository as a gate for the real migration. Do not perform the
   migration in the primary repository until this rehearsal passes or any remaining failures are explicitly documented
   and accepted.

### Phase 4: Structural move (single commit)

1. Create `l0/`.
2. `git mv` all current top-level content into `l0/`, except:

- `.git/`
- `.github/` (rewritten at root)
- `tools/m.css/` and `tools/m.css.L0-PATCHES.md` (promoted to root)
- `THIRD_PARTY_NOTICES` (promoted to root)
- `.gitignore` (rewritten at root)
- future root-owned monorepo policy files such as `.pre-commit-config.yaml`, `Makefile`, and `README.md`

3. Keep `tools/` at root level.
4. Promote `THIRD_PARTY_NOTICES` to root.
5. Create root `.gitignore` for root-owned artifacts, including shared `.venv`, while still covering moved level-local
   artifacts under `l0/`.

### Phase 5: Operational rewiring (same tranche as the move)

1. Update all moved scripts, docs, config files, and workflows that currently assume the flat layout.
2. Treat workflow triggers, working directories, release packaging, docs generation, pre-commit hooks, and Python env
   resolution as behavioral surfaces, not incidental path churn.
3. Keep the tree move and the rewiring changes reviewable, but do not land an intermediate broken state.

### Phase 6: Path and ownership updates

1. Update `l0/scripts/gen-docs.sh` to reference `../../tools/m.css` instead of `../tools/m.css`.

2. Update `l0/compiler/docgen/` paths if they reference `tools/m.css` directly.

3. Update `l0/Makefile` to use the shared `../.venv` and to stop assuming a level-local `.venv`.

4. Update Stage 1 / Stage 2 wrappers and helper scripts to resolve Python from the root `.venv`.

5. Move pre-commit configuration ownership to the root `.pre-commit-config.yaml`.

6. Update `l0/CLAUDE.md`, `l0/README.md`, `l0/README-WINDOWS.md`, and `l0/CONTRIBUTING.md` for the new nesting and
   shared tooling model.

7. Add `MONOREPO.md` and update the root `README.md` / `l0/README.md` split for the L0-only monorepo phase.

8. Grep for any remaining broken path references:

   ```bash
   rg -n "tools/m\\.css" l0/
   rg -n "\\.venv" l0/
   rg -n "l0-.*help|l0-test-all|root dispatcher" .
   ```

### Phase 7: Root files

1. Create root `Makefile` with:

   ```makefile
   DEA_LEVEL_DIRS := l0

   .DEFAULT_GOAL := help

   help:
   	@echo "Monorepo targets:"
   	@echo "  help   Show root-only monorepo targets"
   	@echo "  venv   Populate the shared .venv using registered levels"
   	@echo "  clean  Clean all registered levels and root caches"
   	@echo ""
   	@echo "Registered levels: $(DEA_LEVEL_DIRS)"
   	@echo "Run level-specific commands with: cd <level> && make <target>"

   venv:
   	@for level in $(DEA_LEVEL_DIRS); do $(MAKE) -C $$level venv; done

   clean:
   	@for level in $(DEA_LEVEL_DIRS); do $(MAKE) -C $$level clean; done
   ```

2. Create root `CLAUDE.md` and `AGENTS.md` for monorepo-level AI guidance.

3. Create root `README.md` as the canonical public landing page for the L0-only monorepo phase.

4. Create `MONOREPO.md` for structure, root-only workflow, and registered-level guidance.

### Phase 8: Workflow migration

1. Move `.github/workflows/ci.yml` content into `.github/workflows/l0-ci.yml` with path filters covering `l0/**`,
   `tools/**`, `.github/workflows/**`, and relevant root-owned files.
2. Update all `working-directory` and path references in workflows to include the new `l0/` layout.
3. Move `release.yml` to `l0-release.yml` with analogous path and artifact adjustments.
4. Move `snapshot.yml` to `l0-snapshot.yml` with analogous adjustments.
5. Migrate docs workflows as L0-owned workflows with shared-input path filters.
6. Keep copyright checking as root-owned policy tooling, but update paths and trigger rules to cover both `l0/**` and
   future level subtrees.
7. Verify that workflow filters no longer depend on a root dispatcher model and instead trigger on the actual shared
   inputs they consume.

### Phase 9: Verification

1. `cd l0 && make test-all` — full L0 suite passes.
2. `cd l0 && make dist` — distribution archive builds correctly.
3. `cd l0 && make docs` — documentation generates with the correct `m.css` path.
4. `make help` at the repo root — only `help`, `venv`, and `clean` are exposed.
5. `make venv` at the repo root — shared `.venv` is created or updated without recreating `l0/.venv`.
6. `uv run --directory l0 --group dev pre-commit run --all-files -c .pre-commit-config.yaml` — root pre-commit policy
   passes.
7. `git log --follow l0/compiler/stage1_py/l0_parser.py` — history is preserved after the committed rename.
8. L0 CI/docs workflows trigger on both `l0/**` changes and shared-input changes such as `tools/**`,
   `.github/workflows/**`, and relevant root-owned files.
9. Release workflow produces correct archive naming and layout.

## Path Update Checklist

Files known to require path or ownership updates after the move:

| File                           | Reference                            | Update                                  |
| ------------------------------ | ------------------------------------ | --------------------------------------- |
| `scripts/gen-docs.sh`          | `tools/m.css`                        | `../../tools/m.css`                     |
| `compiler/docgen/l0_docgen.py` | vendored m.css paths                 | verify and update                       |
| `Makefile`                     | `.venv`, root orchestration          | use `../.venv`; root file is separate   |
| `.pre-commit-config.yaml`      | copyright hook path / Markdown scope | promote to root and update exclusions   |
| `.github/workflows/*.yml`      | all path references                  | add `l0/` prefix and shared-input paths |
| `CLAUDE.md`                    | repo layout / root guidance          | update for monorepo nesting             |
| `CONTRIBUTING.md`              | project structure / tooling setup    | update paths and shared `.venv`         |
| `README.md`                    | canonical landing-page ownership     | keep full L0 overview at root for now   |
| `MONOREPO.md`                  | new root monorepo structure guidance | create                                  |
| `l0/README.md`                 | subtree README role                  | convert to short pointer                |
| `README-WINDOWS.md`            | build/install paths                  | update to canonical root README links   |
| `pyproject.toml`               | source paths (if any)                | verify                                  |
| `Dockerfile` / `.dockerignore` | context paths                        | verify if present                       |

## Risk Mitigation

1. **History continuity.** Use `git mv` for structural moves and verify `git log --follow` after the committed rename.
2. **Operational rewiring is real work.** Path filters, workflow call graphs, release packaging, docs entrypoints,
   pre-commit hooks, and Python env resolution all change behavior if migrated incorrectly.
3. **Single migration tranche.** The structural move and operational rewiring land together. No intermediate broken
   state.
4. **Root workflow surface stays minimal.** Do not reintroduce a misleading root dispatcher namespace for level-local
   commands.
5. **Shared tooling can drift if undocumented.** Root `.venv`, root `.pre-commit-config.yaml`, and the temporary
   README/MONOREPO ownership split must be recorded explicitly so future levels follow the same model intentionally.
6. **Rollback.** If anything breaks, `git revert` of the migration commit restores the flat layout.
7. **Hosted rehearsal gate.** The migration is not ready for the primary repository until the disposable GitHub
   repository validates workflow triggers, artifact paths, and release/docs behavior under the new layout.

## Future Extensions (not part of this plan)

- `l1/` directory creation and L1 Stage 1 scaffold.
- Revisit root README ownership once L1 becomes the primary root narrative.
- `tools/docgen-common/` extraction if L1 docgen shares significant logic with L0.
- `dist_tools_lib.py` extraction to a shared `tools/` module if L1 uses the same packaging model.
- Root-level license file promotion when L1 adopts the same dual license.
- Cross-level CI dependency (`l1-ci.yml` consuming L0 release artifacts).
