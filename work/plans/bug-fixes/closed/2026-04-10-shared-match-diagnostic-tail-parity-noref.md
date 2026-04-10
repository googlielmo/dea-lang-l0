# Bug Fix Plan

## Shared enum match diagnostic tail parity

- Date: 2026-04-10
- Status: Closed
- Title: Audit and restore remaining shared enum `match` diagnostic parity after `TYP-0104`
- Kind: Bug Fix
- Scope: Shared
- Severity: Medium
- Stage: Shared
- Targets:
  - L0 Stage 2
  - L1 Stage 1
- Origin: L0 Stage 2, using Python Stage 1 as the behavioral oracle
- Porting rule: Fix the homologous Stage 2 path first, then port the settled logic mechanically into L1 Stage 1 while
  the code paths remain aligned
- Target status:
  - L0 Stage 2: Implemented
  - L1 Stage 1: Implemented
- Subsystem: Type Checker / Diagnostics
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l1/compiler/stage1_l0/src/expr_types.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`,
  `docs/specs/compiler/diagnostic-code-catalog.md`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: `make -C l0 test-stage2 TESTS="expr_types_test"` and `make -C l1 test-stage1 TESTS="expr_types_test"`

## Summary

`TYP-0104` is the highest-impact missing enum-`match` parity bug, but it is not the entire Stage 1 `match` diagnostic
surface.

After the primary exhaustiveness fix lands, both self-hosted trees still need a focused audit of the remaining
Stage-1-equivalent enum `match` diagnostics so shared parity does not stop halfway through the same subsystem.

Implemented outcome:

- `TYP-0103` remained present in the self-hosted enum-`match` path from the primary tranche.
- `TYP-0105` is now emitted when a wildcard arm follows already exhaustive explicit enum-variant coverage.
- focused warning-only fixtures and `expr_types_test` assertions now cover the shared unreachable-wildcard behavior in
  both self-hosted trees.

## Scope of This Fix

1. Audit Stage 1 enum `match` diagnostics adjacent to `TYP-0104`.
2. Start with:
   - `TYP-0103` no type information for enum,
   - `TYP-0105` unreachable wildcard pattern in an already exhaustive match.
3. Confirm whether any additional Stage 1 enum `match` diagnostics remain absent or meaning-drifted in the self-hosted
   trees once `TYP-0104` is implemented.
4. Add focused fixture-backed regression coverage for every adopted diagnostic in both trees.
5. Keep this plan limited to enum-`match` diagnostic parity; do not fold in broader return-flow or statement analysis.

## Approach

### Oracle and audit method

- Use `l0/compiler/stage1_py/l0_expr_types.py` as the behavior oracle.
- Use `l0/compiler/stage1_py/l0_diagnostics.py` and `l0/compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py`
  as the registered code and trigger oracle.
- Compare the settled self-hosted `ST_MATCH` implementation against the Stage 1 behavior after the primary plan lands.

### Expected targets

- `TYP-0103`: if self-hosted can observe a match over an enum scrutinee whose enum info is unavailable, emit the Stage 1
  code instead of silently returning.
- `TYP-0105`: if a wildcard arm is redundant because the prior variant coverage is already exhaustive, emit the Stage 1
  warning-equivalent condition rather than accepting the wildcard silently.

### Boundaries

- Only adopt a diagnostic when the self-hosted condition is meaning-equivalent to Stage 1.
- If a Stage 1 condition depends on self-hosted infrastructure that does not yet exist, mark it as deferred explicitly
  inside this plan rather than quietly omitting it.
- Update the shared catalog only if the final implementation exposes a shared-inventory inconsistency.

## Tests

Minimum new coverage to add in both trees:

1. A constructed enum-info-missing path reports `TYP-0103` if the condition is reachable in self-hosted.
2. A fully covered enum match followed by `_` reports `TYP-0105`.
3. The `TYP-0104` tests from the primary plan keep passing after the additional diagnostics are added.

## Verification

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
```

If warning assertions require a broader harness than `expr_types_test`, extend the narrowest existing self-hosted test
surface rather than introducing a duplicate suite.

Verification completed for this fix:

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
```

## Related Work

- `work/plans/bug-fixes/closed/2026-04-10-shared-match-exhaustiveness-return-path-parity-noref.md`

## Assumptions

- `TYP-0104` lands first; this plan is intentionally a follow-up rather than a prerequisite.
- The remaining enum-`match` parity drift is localized enough to stay in the same checker files without broader parser
  or AST changes.
