# Feature Plan

## Diagnostic-code catalog meanings

- Date: 2026-04-03
- Status: Closed (implemented)
- Title: Expand the shared compiler diagnostic-code catalog with semantic meanings
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: Documentation
- Modules: `docs/specs/compiler/diagnostic-code-catalog.md`, `l0/compiler/stage1_py/l0_diagnostics.py`,
  `l0/compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py`
- Test modules: None

## Summary

Upgrade the shared Dea compiler diagnostic catalog from an inventory-only register into a per-code reference that
records a curated semantic meaning for every registered code.

The expansion keeps the catalog Dea-compiler-wide while treating L0 Python Stage 1 as the current oracle for registered
code meaning and trigger classification.

## Root Cause

The shared catalog already listed all registered families and codes, but it still required readers to jump into the
Stage 1 trigger matrix to understand what each code represented in practice.

That made parity audits and future compiler-port work slower than necessary because the central catalog did not yet
surface the actual issue each code represents in stable documentation language.

## Scope of This Feature

1. Replace the inventory-only two-column tables with per-code tables containing `Code` and `Meaning`.
2. Populate every registered row from the Stage 1 oracle inventory, implementation sources, and trigger classifications.
3. Preserve the family ordering and Dea-compiler-wide framing of the shared catalog.
4. Record how CLI-only, warning-only, and internal/unreachable registered codes are represented in the shared tables.

## Approach

- Keep `l0/compiler/stage1_py/l0_diagnostics.py` as the ordering and completeness source.
- Use `l0/compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py` as the trigger and classification source.
- Derive `Meaning` from the actual Stage 1 issue represented by each code rather than repeating generic family labels,
  placeholder-stripped message fragments, or copied rendered diagnostics.
- Use the Stage 1 implementation files to recover the real semantic meaning for driver, CLI, and internal codes whose
  trigger matrix alone is not descriptive enough.
- Keep reproducers and detailed trigger scenarios in the linked Stage 1 oracle sources instead of duplicating weaker
  trigger paraphrases in the shared catalog.
- Use compact category-plus-example wording for intentionally broad umbrella codes such as driver failures.

## Verification

1. Confirm every registered code still appears exactly once in the catalog.
2. Confirm every row now includes a non-empty `Meaning` cell.
3. Confirm the catalog still preserves the registered family ordering from `DIAGNOSTIC_CODE_FAMILIES`.
4. Confirm no table retains the removed `Status` or `Canonical trigger` columns.
5. Confirm the document still points readers back to the Stage 1 inventory and trigger-matrix oracle sources.

## Assumptions

- Python Stage 1 remains the current oracle for registered compiler diagnostic meanings and trigger classifications.
- The shared catalog should favor semantic issue descriptions and leave detailed reproducers to the linked Stage 1
  oracle sources.
