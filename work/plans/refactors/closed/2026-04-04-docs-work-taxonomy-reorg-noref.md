# Refactor Plan

## Split stable docs from lifecycle work across the monorepo

- Date: 2026-04-04
- Status: Closed
- Title: Separate stable documentation from lifecycle work artifacts across root, L0, and L1
- Kind: Refactor
- Scope: Shared
- Severity: Medium
- Stage: Shared
- Targets:
  - Root monorepo docs/work layout
  - L0 docs/work layout
  - L1 docs/work layout
- Origin: Root monorepo documentation policy
- Porting rule: Apply the same taxonomy consistently at root and in each level subtree without changing stable document
  intent
- Target status:
  - Root monorepo docs/work layout: Implemented
  - L0 docs/work layout: Implemented
  - L1 docs/work layout: Implemented
- Subsystem: Documentation taxonomy / work tracking
- Modules:
  - `CLAUDE.md`
  - `docs/README.md`
  - `docs/reference/project-status.md`
  - `work/`
  - `l0/docs/README.md`
  - `l0/work/`
  - `l1/docs/README.md`
  - `l1/work/`
- Test modules: None

## Summary

The repository had begun to mix two different document intents under `docs/`:

- stable reference/spec material
- lifecycle-bound plans and proposals

That made path meaning less obvious and also made shared L0/L1 work harder to track consistently.

This refactor introduced a repo-wide split:

- `docs/` for stable current-state and normative material
- `work/` for plans, proposals, and closed execution history

## Decisions

1. Root, `l0/`, and `l1/` now share the same top-level mental model: stable docs in `docs/`, lifecycle artifacts in
   `work/`.
2. Shared cross-level fixes and refactors should default to one root-owned shared plan with explicit targets and target
   status instead of spawning mechanical follow-up plans in downstream subtrees.
3. Accepted design intent should graduate from `work/` into `docs/reference/`, `docs/specs/`, or other stable-doc
   locations rather than remaining under `work/`.

## Work Completed

1. Moved root plans from `docs/plans/` to `work/plans/`.
2. Moved L0 plans and proposals from `l0/docs/` to `l0/work/`.
3. Moved L1 plans from `l1/docs/` to `l1/work/`.
4. Added `work/README.md`, `l0/work/README.md`, and `l1/work/README.md`.
5. Updated repo guidance and internal links to reflect the new taxonomy.
6. Added shared-plan metadata guidance and applied it to representative shared root plans.

## Verification

1. `docs/` now contains only stable documentation trees at root, `l0/`, and `l1/`.
2. Lifecycle artifacts now live under the corresponding `work/` tree.
3. Guidance files and plan cross-references point at the new paths.
