# Documentation Layout

This directory is organized by document intent first, then subsystem.

## Folders

- `reference/`: stable current-state documentation for language and compiler.
- `specs/`: normative contracts and behavioral specifications.
- `implementation/`: implementation-oriented specs and design notes.
- `proposals/`: planned or in-discussion changes and new features.
- `plans/`: execution plans, especially bug-fix plans.
- `attic/`: superseded or obsolete documents.

## Placement Guide

- Use `reference/` when documenting how the system currently works.
- Use `specs/` when defining canonical behavior/contracts.
- Use `implementation/` for build strategy details (for example Stage 2 parser internals).
- Use `proposals/` for future changes not yet accepted as canonical.
- Use `plans/` for execution plans and operational work tracking.
- Move a document to `attic/` only when it is superseded or obsolete.

## Naming Conventions

- Use lowercase kebab-case file names.
- Avoid duplicating type in file names when path already encodes it.
- Keep names concise and domain-focused.

### Bug-Fix Plans

Use:

`YYYY-MM-DD-<area>-<slug>-<tracker>.md`

Examples:

- `2026-02-15-arc-retain-cycle-leak-noref.md`
- `2026-03-02-arc-double-release-on-error-path-ref-gh-128.md`

Tracker values:

- `noref` when no tracking system item exists yet.
- `ref-gh-<number>`, `ref-jira-<key>`, or equivalent when available.

## Attic Policy

- `attic/` mirrors the live tree (`reference`, `specs`, `implementation`, `proposals`, `plans`).
- Do not use `attic/` as per-change version history; git already provides history.
- Archive only superseded/obsolete docs.

Archived file naming pattern:

`<original-name>-archived-YYYY-MM-DD-ref-<replacement-or-none>.md`

Archived document header should include:

- `Status: Archived`
- `Archived on: YYYY-MM-DD`
- `Reason: superseded | obsolete`
- `Replaced by: <path | none>`
- `Scope note: <short context>`
