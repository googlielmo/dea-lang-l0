# Documentation Layout

This directory is organized by document intent first, then subsystem.

## Folders

- `reference/`: stable current-state documentation for language and compiler.
- `user/`: standalone end-user guides used as the source for shipped distribution docs.
- `specs/`: normative contracts and behavioral specifications.
- `implementation/`: implementation-oriented specs and design notes.
- `proposals/`: planned or in-discussion changes and new features.
- `plans/`: execution plans, especially bug-fix plans.
- `attic/`: superseded or obsolete documents when archival storage is needed.

Create subdirectories only when they are needed for real documents. Do not keep empty placeholders or `.gitkeep` entries
in `docs/`; recreate directories on demand.

Generated API documentation is not stored in this tree. The docs pipeline writes generated HTML, Markdown, Doxygen XML,
and Doxygen LaTeX under `build/docs/`. When `./scripts/gen-docs.sh --pdf` is used, the built PDF is copied to
`build/docs/pdf/` (also with `--pdf-fast`). After each successful docs run, generated artifacts are mirrored into a
stable preview tree under `build/preview/{html,markdown,pdf}` and overwritten by the next successful run. CI publishing
also produces a Chirpy-compatible export under `build/docs/blog-export/`, packaged as a release asset
(`blog-export.tar.gz`) for consumption by external blog repositories.

## Placement Guide

- Use `reference/` when documenting how the system currently works.
- Use `user/` for standalone end-user docs meant to ship in release archives.
- Use `specs/` when defining canonical behavior/contracts.
- Use `implementation/` for build strategy details (for example Stage 2 parser internals).
- Use `proposals/` for future changes not yet accepted as canonical.
- Use `plans/` for execution plans and operational work tracking.
- Move a document to `attic/` only when it is superseded or obsolete.

Plan category guidance:

- `plans/features/`: user-facing language, compiler, or standard-library features.
- `plans/tools/`: repository tooling and operational workflows, including CI, build/install packaging, release
  automation, docs pipelines, Docker workflows, launchers, and validation tooling.
- `plans/refactors/`: internal restructures that preserve the current external behavior.
- `plans/bug-fixes/`: defect fixes in any subsystem.

## Naming Conventions

- Use lowercase kebab-case file names.
- Avoid duplicating type in file names when path already encodes it.
- Keep names concise and domain-focused.

## Document Metadata & Templates

All documentation should follow these metadata standards to ensure consistency and discoverability.

### Reference and Specifications (`reference/`, `specs/`)

Stable or normative documents must include a version line immediately following the main header.

**Template:**

```markdown
# [Title]

Version: YYYY-MM-DD

[Introduction or summary of the document intent.]

## Related Docs

- [Link to related architecture/spec/reference doc]
```

### Plans (`plans/`)

Plans for bug fixes, features, refactors, or tooling follow a more detailed metadata block.

**Layout:** Each category (`features/`, `bug-fixes/`, `refactors/`, `tools/`) has a `closed/` subdirectory. Active plans
(`Draft`, `In Progress`) remain at the category root. Plans with status `Closed` or `Implemented` are moved into
`<category>/closed/`.

**Attachments:** Non-Markdown reference files associated with plans (workflows, configs, scripts, etc.) go in
`<category>/attachments/`. Attachments stay at the category level even after the referencing plan is closed, unless the
attachment itself is obsolete.

**Closing workflow:** When closing a plan, `git mv` it into the corresponding `closed/` subdirectory, then grep for its
filename across `docs/` and update any cross-references to reflect the new path.

**Template:**

```markdown
# [Bug Fix | Feature | Refactor | Tool] Plan

## [Short Title]

- Date: YYYY-MM-DD
- Status: [Draft | In Progress | Closed (fixed/implemented)]
- Title: [Full descriptive title]
- Kind: [Bug Fix | Feature | Refactor | Tooling]
- Severity: [Low | Medium | High | Critical]
- Stage: [1 | 2 | Shared]
- Subsystem: [Subsystem name]
- Modules:
    - `path/to/module.l0`
- Test modules:
    - `path/to/test_module.l0`
- Repro: [Reproduction command or path] (optional)

## Summary

...
```

## Core References

- [reference/architecture.md](reference/architecture.md): compiler pipeline and pass structure.
- [reference/c-backend-design.md](reference/c-backend-design.md): Stage 1 lowering/runtime interaction details.
- [reference/standard-library.md](reference/standard-library.md): `std.*` and `sys.*` API surface.
- [reference/ownership.md](reference/ownership.md): canonical ownership rules for `new`/`drop`, ARC strings, and
  container patterns.

### Bug-Fix Plans

Use:

`YYYY-MM-DD-<area>-<slug>-<tracker>.md`

Examples:

- `2026-02-15-arc-retain-cycle-leak-noref.md`
- `2026-03-02-arc-double-release-on-error-path-ref-gh-128.md`

Tracker values:

- `noref` when no tracking system item exists yet.
- `ref-gh-<number>`, `ref-jira-<key>`, or equivalent when available.

## Archived Documents

Use `docs/attic/` only for superseded or obsolete documents.

- Do not use `docs/attic/` as per-change version history; git already provides history.
- Archive only retired docs; routine edits stay in the live tree.
- When `docs/attic/` exists, keep any subdirectories aligned with the live docs tree (`reference/`, `specs/`,
  `implementation/`, `proposals/`, `plans/`).

Archived file naming pattern:

`<original-name>-archived-YYYY-MM-DD-ref-<replacement-or-none>.md`

Archived document header should include:

- `Status: Archived`
- `Archived on: YYYY-MM-DD`
- `Reason: superseded | obsolete`
- `Replaced by: <path | none>`
- `Scope note: <short context>`
