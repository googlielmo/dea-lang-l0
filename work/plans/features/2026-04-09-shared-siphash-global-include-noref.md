# Feature Plan

## Move SipHash to a monorepo-global shared include

- Date: 2026-04-09
- Status: Draft
- Title: Move SipHash to a monorepo-global shared include
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: Shared runtime headers / C backend includes / build layout
- Targets:
  - `l0`
  - `l1`

## Summary

L0 and L1 currently vendor their own level-local `l0_siphash.h` copies under each runtime tree and emit that include
path directly into generated C. This should be consolidated into one canonical monorepo-global shared header location
that both levels include through the same stable path.

This is shared cross-level maintenance work. It should not be implemented as a level-local downstream port.

## Goal

1. Create one canonical SipHash header location shared by at least L0 and L1.
2. Update both runtime headers and both C emitters to include the shared header path.
3. Remove duplicated level-local ownership of the SipHash header once both levels build against the shared location.

## Key Changes

### Shared header placement

- Choose one root-owned shared include location under the monorepo for the canonical SipHash header.
- Keep the header content single-sourced there rather than copied per level.

### Consumer updates

- Update L0 and L1 runtime headers to include the shared SipHash header path.
- Update L0 and L1 C emitters so generated C includes the same shared path.
- Refresh affected tests, backend goldens, and docs in both levels.

### Cleanup

- Remove or replace the duplicated level-local `l0_siphash.h` copies after both levels are switched over.
- Ensure the build/test flows for both levels continue to locate the shared header without relying on ad-hoc include
  paths.

## Test Plan

- Run the targeted backend/emitter test suites for both `l0` and `l1`.
- Verify generated C in both levels includes the shared SipHash header path.
- Verify both runtime headers include the shared header path and no longer depend on level-local SipHash copies.

## Assumptions

- The shared header path should remain compatible with current C99 single-header usage via `SIPHASH_IMPLEMENTATION`.
- The migration should be staged so L0 and L1 remain buildable throughout rather than requiring a flag day across
  unrelated work.
