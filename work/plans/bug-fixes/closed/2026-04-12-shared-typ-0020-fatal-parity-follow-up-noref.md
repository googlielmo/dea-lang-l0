# Bug Fix Plan

## Restore fatal `TYP-0020` parity after native source cleanup

- Date: 2026-04-12
- Status: Closed
- Title: Restore fatal `TYP-0020` parity after native source cleanup
- Kind: Bug Fix
- Scope: Shared
- Severity: High
- Stage: Shared
- Targets:
  - L0 Stage 2
  - L1 Stage 1
- Origin: L0 Stage 2, using Python L0 Stage 1 as the canonical diagnostic-code oracle
- Porting rule: Clean the L0 Stage 2 native sources first, then keep the homologous L1 Stage 1 sources and checker path
  mechanically aligned
- Target status:
  - L0 Stage 2: Implemented
  - L1 Stage 1: Implemented
- Subsystem: Diagnostics / Type checking / Bootstrap sources
- Modules: `l0/compiler/stage2_l0/src/{ast,expr_types,source_paths}.l0`,
  `l1/compiler/stage1_l0/src/{ast,expr_types,source_paths}.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l1/compiler/stage1_l0/tests/expr_types_test.l0`,
  `work/plans/bug-fixes/closed/2026-04-12-shared-typ-0020-fatal-parity-follow-up-noref.md`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`,
  `l0/compiler/stage2_l0/tests/diagnostic_code_parity_test.py`,
  `l1/compiler/stage1_l0/tests/diagnostic_code_parity_test.py`
- Repro: before this fix, self-hosted bootstrap paths reported native `TYP-0020` warnings from compiler sources and test
  sources that reused duplicate loop locals in one function scope

## Summary

`work/plans/bug-fixes/closed/2026-04-11-shared-diagnostic-code-parity-noref.md` restored the canonical `TYP-0020` code
but deliberately kept the native L0 Stage 2 and L1 Stage 1 path warning-shaped to avoid breaking existing self-hosted
compiler sources.

This follow-up resolves that deferred decision by removing the duplicate-local declarations from the native compiler
sources first, then promoting `TYP-0020` back to an error so L0 Stage 2 and L1 Stage 1 match the Python Stage 1 oracle.

## Scope of This Fix

1. Remove mirrored duplicate-local declarations from the native compiler sources.
2. Promote native `TYP-0020` emissions from warning to error in the self-hosted checker path.
3. Keep L0 Stage 2 and L1 Stage 1 mechanically aligned for the affected files.
4. Update focused tests and parity documentation to reflect the resolved severity.

## Non-Goals

- Do not change the Python L0 Stage 1 oracle.
- Do not change the warning severity of `TYP-0021` through `TYP-0025`.
- Do not refactor unrelated native warning sites that are outside the duplicate-local path.

## Approach

- Use the existing native `TYP-0020` warnings as a cleanup checklist for the self-hosted sources.
- Rename or narrow the duplicate loop bindings without changing behavior.
- Switch the duplicate-local diagnostic in native expression checking to `diag_error`.
- Re-run the targeted parity and bootstrap-oriented tests to confirm the native sources no longer rely on warning
  compatibility.

## Tests

Verification checks passing:

```bash
make -C l0 use-dev-stage2
make -C l1 use-dev-stage1
.venv/bin/python scripts/diagnostic_parity.py --stage l0 --compiler l0/build/dea/bin/l0c-stage2
.venv/bin/python scripts/diagnostic_parity.py --stage l1 --compiler l1/build/dea/bin/l1c-stage1
make -C l0 test-stage2 TESTS=expr_types_test
make -C l1 test-stage1 TESTS=expr_types_test
make -C l0 test-stage2
make -C l1 test-stage1
git diff --check
```

## Resolved Question

- `TYP-0020` should be fatal in native L0 Stage 2 and L1 Stage 1, matching the Python Stage 1 oracle, and the native
  compiler sources should be cleaned up instead of preserving warning-only compatibility.

## Current Outcome

- L0 Stage 2 compiler sources no longer depend on warning-only duplicate-local compatibility during self-hosted
  bootstrap, install-prefix, or triple-bootstrap flows.
- L1 Stage 1 compiler sources and affected runtime tests no longer reuse duplicate loop locals in one function scope.
- Native L0 Stage 2 and L1 Stage 1 now emit `TYP-0020` as an error through the native expression-checking path, matching
  the Python Stage 1 oracle.
- The shared diagnostic parity harness, focused expr-types checks, full L0 Stage 2 suite, full L1 Stage 1 suite, and
  `git diff --check` all pass.

## Related Work

- `work/plans/bug-fixes/closed/2026-04-11-shared-diagnostic-code-parity-noref.md`
