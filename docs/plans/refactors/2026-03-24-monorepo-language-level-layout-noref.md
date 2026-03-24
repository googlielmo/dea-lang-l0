# Refactor Plan

## Monorepo restructuring for multi-level language development

- Date: 2026-03-24
- Status: Draft
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

Restructure the single-language repository into a monorepo where each language level (L0, L1, L2, ...) is a
self-contained subtree. The only shared assets promoted to the monorepo root are language-agnostic vendor tools and
top-level orchestration files.

## Goals

1. Each language level is an autonomous project with its own compiler, docs, tests, scripts, and Makefile.
2. The bootstrap chain between levels is explicit: L1 Stage 1 is compiled by L0 Stage 2, L2 Stage 1 by L1 Stage 2, etc.
3. Shared vendor tools (currently `tools/m.css`) live at the monorepo root and are referenced by all levels.
4. A root Makefile dispatches to per-level Makefiles.
5. CI workflows are per-level with explicit cross-level dependency when needed.
6. The tree move lands as a single rename-focused migration, with the required operational rewiring called out
   explicitly and validated in the same tranche.

## Non-Goals

- Extracting `dist_tools_lib.py` or docgen into shared libraries (deferred until L1 needs them).
- Designing L1 CI workflows (deferred until L1 exists).
- Changing any L0 functionality, semantics, or public interfaces.

## Target Layout

```
dea/
  l0/                               current repo contents (minus shared vendor tools)
    compiler/
      stage1_py/
      stage2_l0/
      shared/
      docgen/
    docs/
    examples/
    tests/
    scripts/
    .github/                         L0-specific workflow fragments (optional)
    Makefile
    CLAUDE.md
    README.md
    README-WINDOWS.md
    CONTRIBUTING.md
    SECURITY.md
    LICENSE-MIT
    LICENSE-APACHE
    pyproject.toml
    .pre-commit-config.yaml
    ...
  tools/
    m.css/                           vendor (language-agnostic)
    m.css.L0-PATCHES.md
  Makefile                           root dispatcher
  CLAUDE.md                          root-level AI guidance
  README.md                          monorepo overview
  THIRD_PARTY_NOTICES                vendor license manifest
  .github/
    workflows/
      l0-ci.yml                      L0 CI (paths: l0/**)
      l0-release.yml                 L0 release (tag-triggered)
      l0-snapshot.yml                L0 snapshot (manual dispatch)
  .gitignore
```

When L1 is created:

```
dea/
  l0/                               unchanged
  l1/
    compiler/
      stage1_l0/                     L1 compiler written in L0
      stage2_l1/                     L1 self-hosting compiler
      shared/                        L1 stdlib + runtime
      docgen/                        L1-specific doc filters
    docs/
    examples/
    tests/
    scripts/
    Makefile
    CLAUDE.md
    README.md
  tools/
    m.css/                           shared
  ...
```

## Design Decisions

### D1: Everything inside `l0/`

All current content moves into `l0/`, including docs, scripts, examples, tests, and Python tooling. Rationale: all of
these assets are L0-specific today. Shared extraction happens only when a second consumer exists.

### D2: Vendor tools at root

`tools/m.css/` and `THIRD_PARTY_NOTICES` move to the monorepo root. Rationale: m.css is language-agnostic and will be
reused by L1 and subsequent levels for Doxygen-based documentation.

### D3: Root Makefile is a thin dispatcher

The root Makefile delegates to per-level Makefiles. It does not duplicate build logic.

### D4: CI workflows move to root `.github/`

GitHub Actions requires workflows under the repository root `.github/workflows/`. Per-level path filters ensure each
workflow triggers on the level subtree plus any shared root-owned inputs it consumes. For L0, this includes `l0/**`,
`tools/**`, root workflow files, and any root orchestration files that can affect L0 builds, docs, packaging, or policy
checks.

### D5: License files stay inside `l0/`

License files remain in `l0/` for now. When L1 is created under the same license, they can be promoted to the root and
symlinked or referenced from each level.

### D6: Root README is navigational

The root README provides a project overview and a table of language levels. It does not duplicate build instructions
from `l0/README.md`.

## Implementation Phases

### Phase 1: Prepare (pre-migration)

1. Audit all hardcoded paths in CI workflows, scripts, Makefile, and docs.
2. List every file that references `tools/m.css` and will need a path update after the move.
3. Ensure all tests pass on the current layout (`make test-all`).
4. Tag the L0 1.0 release on the current flat layout.

### Phase 2: Drill migration in a disposable local clone

1. Create a fresh local clone of the repository outside the main working tree.
2. Perform the full planned monorepo migration in the clone, including:

- moving the current tree under `l0/`
- promoting shared root-owned assets such as `tools/m.css` and `THIRD_PARTY_NOTICES`
- adding the root `Makefile`, root `README.md`, and root `CLAUDE.md`
- updating workflow triggers, working directories, and root-owned policy/docs workflows

3. Run the full post-migration verification suite in the clone:

- `cd l0 && make test-all`
- `cd l0 && make dist`
- `cd l0 && make docs`
- root dispatcher checks such as `make l0-test-all`

4. Validate local operational behavior in the clone:

- docs generation still finds root `tools/m.css`
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

1. Create `l0/` directory.
2. `git mv` all current top-level content into `l0/`, except:

- `.git/`
- `.github/` (will be rewritten)
- `tools/m.css/` and `tools/m.css.L0-PATCHES.md` (promoted to root)
- `THIRD_PARTY_NOTICES` (promoted to root)
- `.gitignore` (rewritten at root)

3. Move `tools/` to root level (it is already at `tools/` today, so this is a no-op if the path is preserved; if it was
   inside the moved tree, extract it back to root).
4. Move `THIRD_PARTY_NOTICES` to root.
5. Create root `.gitignore` (merge of current `.gitignore` scoped under `l0/` plus root-level patterns).

### Phase 5: Operational rewiring (same tranche as the move)

1. Update all moved scripts, docs, config files, and workflows that currently assume the flat layout.
2. Treat workflow triggers, working directories, release packaging, docs generation, and pre-commit hooks as behavioral
   surfaces, not as incidental path churn.
3. Keep the tree move and the rewiring changes reviewable, but do not land an intermediate broken state.

### Phase 6: Path updates

1. Update `l0/scripts/gen-docs.sh` to reference `../../tools/m.css` instead of `../tools/m.css`.
2. Update `l0/compiler/docgen/` paths if they reference `tools/m.css` directly.
3. Update `l0/Makefile` if it references `tools/` paths.
4. Update `l0/.pre-commit-config.yaml` if it references root-relative paths.
5. Update `l0/CLAUDE.md` to reflect the new nesting.
6. Update `l0/README.md` to note it is inside the `dea/` monorepo.
7. Grep for any remaining broken path references:
   ```bash
   rg -n "tools/m\.css" l0/
   rg -n "\.\./tools" l0/
   ```

### Phase 7: Root files

1. Create root `Makefile`:

   ```makefile
   .DEFAULT_GOAL := help

   l0-%:
   	$(MAKE) -C l0 $*

   test-all: l0-test-all

   help:
   	@echo "Targets:"
   	@echo "  l0-<target>    Delegate <target> to l0/Makefile"
   	@echo "  test-all       Run all test suites"
   	@echo ""
   	@$(MAKE) -C l0 help
   ```

2. Create root `CLAUDE.md`:

   ```markdown
   # CLAUDE.md

   Guidance for Claude Code and AI agents working in this monorepo.

   ## Repository Structure

   This is a monorepo for the Dea language family. Each language level is a
   self-contained subtree.

   | Directory | Description                              |
   |-----------|------------------------------------------|
   | `l0/`     | L0 language, compiler, stdlib, docs      |
   | `tools/`  | Shared vendor dependencies (m.css)       |

   ## Per-Level Guidance

   For L0-specific guidance, read `l0/CLAUDE.md`.
   ```

3. Create root `README.md` (navigational, as discussed).

### Phase 8: Workflow migration

1. Move `.github/workflows/ci.yml` content into `.github/workflows/l0-ci.yml` with path filter:
   ```yaml
   on:
     push:
       paths: ['l0/**', 'tools/**', '.github/workflows/**', 'Makefile']
     pull_request:
       paths: ['l0/**', 'tools/**', '.github/workflows/**', 'Makefile']
   ```
2. Update all `working-directory` and path references in the workflow to include `l0/` prefix.
3. Move `release.yml` to `l0-release.yml` with analogous path/tag adjustments.
4. Move `snapshot.yml` to `l0-snapshot.yml` with analogous adjustments.
5. Migrate docs workflows as L0-owned workflows with shared-input path filters:

- `docs-build.yml`
- `docs-validate.yml`
- `docs-publish.yml`

6. Keep `copyright-headers.yml` and `.github/workflows/check_copyright_headers.py` as root-owned policy tooling, but
   update paths and trigger rules to cover both `l0/**` and any future level subtrees.
7. Verify: push to a branch and confirm CI/docs workflows trigger for both `l0/**` changes and shared-input changes such
   as `tools/**`.

### Phase 9: Verification

1. `cd l0 && make test-all` — full L0 suite passes.
2. `cd l0 && make dist` — distribution archive builds correctly.
3. `cd l0 && make docs` — documentation generates with correct m.css path.
4. Root `make l0-test-all` — dispatcher works.
5. `git log --follow l0/compiler/stage1_py/l0_parser.py` — history is preserved.
6. L0 CI/docs workflows trigger on both `l0/**` changes and shared-input changes such as `tools/**`,
   `.github/workflows/**`, and relevant root orchestration files.
7. Release workflow produces correct archive naming and layout.

## Path Update Checklist

Files known to require path updates after the move:

| File                           | Reference                                      | Update                   |
| ------------------------------ | ---------------------------------------------- | ------------------------ |
| `scripts/gen-docs.sh`          | `tools/m.css`                                  | `../../tools/m.css`      |
| `compiler/docgen/l0_docgen.py` | vendored m.css paths                           | verify and update        |
| `.pre-commit-config.yaml`      | `.github/workflows/check_copyright_headers.py` | update to `l0/` relative |
| `.github/workflows/*.yml`      | all path references                            | add `l0/` prefix         |
| `Makefile`                     | `tools/` references (if any)                   | update                   |
| `CLAUDE.md`                    | doc file paths                                 | update if absolute       |
| `CONTRIBUTING.md`              | project structure section                      | update paths             |
| `README.md`                    | build/install instructions                     | update paths             |
| `README-WINDOWS.md`            | build/install paths                            | update paths             |
| `pyproject.toml`               | source paths (if any)                          | update                   |
| `Dockerfile` / `.dockerignore` | context paths                                  | update                   |

## Risk Mitigation

1. **History continuity.** `git mv` preserves blame. `git log --follow` tracks renames. No rewrite.
2. **Operational rewiring is real work.** Path filters, workflow call graphs, release packaging, docs entrypoints, and
   pre-commit hooks all change behavior if migrated incorrectly. Treat them as first-class migration scope.
3. **Single migration tranche.** The structural move and operational rewiring land together. No intermediate broken
   state.
4. **Rollback.** If anything breaks, `git revert` the migration commit restores the flat layout.
5. **Existing clones.** Contributors `git pull` and get the new layout. Bookmarks and local branches need rebase.
6. **Hosted rehearsal gate.** The migration is not ready for the primary repository until the disposable GitHub
   repository validates workflow triggers, artifact paths, and release/docs behavior under the new layout.

## Future Extensions (not part of this plan)

- `l1/` directory creation and L1 Stage 1 scaffold.
- `tools/docgen-common/` extraction if L1 docgen shares significant logic with L0.
- `dist_tools_lib.py` extraction to a shared `tools/` module if L1 uses the same packaging model.
- Root-level license file promotion when L1 adopts the same dual license.
- Cross-level CI dependency (`l1-ci.yml` consuming L0 release artifacts).
