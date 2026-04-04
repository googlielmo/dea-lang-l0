# Feature Plan

## Shared diagnostic-code catalog

- Date: 2026-04-03
- Status: Closed (implemented)
- Title: Add a shared Dea compiler diagnostic-code catalog
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: Documentation
- Modules: `docs/specs/compiler/diagnostic-code-catalog.md`, `l0/compiler/stage1_py/l0_diagnostics.py`,
  `l0/compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py`
- Test modules: None

## Summary

Add a shared compiler document that catalogs the currently registered diagnostic codes independently of any specific
level or compiler stage.

The catalog is intended to support:

1. Stage 2 parity audits against the current L0 diagnostic oracle.
2. Future L1 bootstrap work that needs a neutral diagnostic-code reference.
3. Ongoing documentation maintenance as new compiler rules introduce or reuse codes.

## Root Cause

The repository already had the authoritative L0 code register in `l0/compiler/stage1_py/l0_diagnostics.py`, plus the
trigger matrix in `l0/compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py`, but there was no shared document
that surfaced the inventory in one place for broader compiler work.

That made parity review reactive and forced code-audit work to rediscover the same registry structure repeatedly.

## Scope of This Feature

1. Add a shared compiler diagnostic-code catalog under the repo-root `docs/specs/compiler/` tree.
2. Present the catalog as per-family tables with one row per registered code.
3. Make the document general to Dea compiler implementations rather than tying it to a specific level or stage.
4. Record that Python Stage 1 is the current oracle inventory for L0 diagnostic codes.

## Approach

- Create `docs/specs/compiler/diagnostic-code-catalog.md`.
- Populate it from the current registered families in `DIAGNOSTIC_CODE_FAMILIES`.
- Link it to the existing policy and trigger-matrix sources rather than duplicating all semantic detail immediately.
- Structure the document so future changes can add richer per-code descriptions without replacing the shared catalog.

## Verification

1. Confirm every currently registered family appears in the shared catalog.
2. Confirm each registered code is represented as a table row.
3. Confirm the catalog links back to the existing policy and oracle sources.

## Assumptions

- Python Stage 1 remains the current oracle for L0 diagnostic-code inventory and meaning.
- `ICE-xxxx` tracking can stay outside this catalog until a separate shared register is introduced.
