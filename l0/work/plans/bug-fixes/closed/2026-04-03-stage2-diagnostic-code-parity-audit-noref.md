# Bug Fix Plan

## Stage 2 diagnostic-code parity audit

- Date: 2026-04-03
- Status: Closed (fixed)
- Title: Audit and fix remaining Stage 2 diagnostic-code parity drift against Stage 1
- Kind: Bug Fix
- Severity: High
- Stage: 2
- Subsystem: Diagnostics / Type Checker
- Modules: `compiler/stage2_l0/src/expr_types.l0`, `compiler/stage2_l0/tests/expr_types_test.l0`,
  `compiler/stage1_py/l0_diagnostics.py`, `compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py`,
  `docs/specs/compiler/diagnostic-code-catalog.md`
- Test modules: `compiler/stage2_l0/tests/expr_types_test.l0`
- Repro: `make DEA_BUILD_DIR=build/dev-dea test-stage2 TESTS="expr_types_test"`

## Summary

The immediate trigger is function-call argument mismatch in Stage 2:

- Python Stage 1 uses `TYP-0312` for function-call argument type mismatch.
- Stage 2 currently emits `TYP-0321` for the equivalent condition in `compiler/stage2_l0/src/expr_types.l0`.

Recent fixes for explicit casts and the `TYP-0310`/`TYP-0311` split showed that this is not an isolated issue. Stage 2
still has remaining code-level parity drift against the Stage 1 diagnostic oracle, and point-fixing one code at a time
risks missing nearby mismatches.

This plan broadens the work from the single function-call case into a targeted audit of remaining Stage 2
diagnostic-code drift, starting with the Stage 2 type checker and using the Stage 1 register plus Stage 1 diagnostic
trigger tests as the source of truth.

## Root Cause

Stage 2 ports have reused Stage 1 behavior incrementally, but the codebase does not yet have a shared compiler-wide
catalog of registered diagnostic codes and their parity expectations. That has allowed some Stage 2 call sites to keep
Stage 2-local numbering such as `TYP-0320`/`TYP-0321` even when Stage 1 already defines exact equivalents.

The existing Stage 1 register is split across:

- `compiler/stage1_py/l0_diagnostics.py` for the family/code inventory
- `compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py` for code triggers and expected meanings

Without a neutral shared reference, parity review has remained reactive and local to the subsystem being edited.

## Scope of This Fix

1. Fix Stage 2 function-call argument type mismatch to reuse Stage 1 `TYP-0312`.
2. Audit remaining Stage 2 diagnostic-code drift in the type checker and adjacent Stage 2 analysis paths, not just the
   single `TYP-0312` call site.
3. Add or update Stage 2 fixture-backed tests so each corrected drift has explicit regression coverage.
4. Use the shared diagnostic-code catalog document under the repo-root `docs/` tree as the inventory reference for this
   audit.
5. Keep this plan focused on diagnostic-code parity, not message-text normalization or unrelated semantic changes.

## Approach

### Shared diagnostic-code catalog

- Use `docs/specs/compiler/diagnostic-code-catalog.md` as the shared inventory reference.
- Continue treating `compiler/stage1_py/l0_diagnostics.py` as the registered family/code source of truth for L0 parity.
- Treat the catalog as an inventory reference, not as a replacement for the normative parity policy in
  `l0/docs/specs/compiler/diagnostic-code-policy.md`.

### Stage 2 audit and fixes

- Start from `compiler/stage2_l0/src/expr_types.l0`, where the known remaining drift is:
  - argument-count mismatch uses `TYP-0320` instead of the Stage 1 equivalent `TYP-0183`
  - argument-type mismatch uses `TYP-0321` instead of the Stage 1 equivalent `TYP-0312`
- Audit the rest of the Stage 2 type checker for any other user-facing diagnostic codes whose semantic meaning matches
  an existing Stage 1 code but whose number differs.
- For each confirmed drift:
  - map the Stage 2 condition to the Stage 1 equivalent condition,
  - update the Stage 2 call site to reuse the exact Stage 1 code,
  - add or update a Stage 2 fixture-backed assertion that proves the corrected code.
- Use the Stage 1 trigger matrix in `compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py` as the meaning-level
  oracle when deciding equivalence.

Audit result for this fix:

- the remaining confirmed drift in `compiler/stage2_l0/src/expr_types.l0` was limited to the function-call arity and
  argument-type diagnostics
- no additional Stage 1-equivalent user-facing `TYP-*` numbering drift was found in the adjacent Stage 2 expression
  checker paths covered by this audit

### Test coverage

- Extend `compiler/stage2_l0/tests/expr_types_test.l0` with focused checks for:
  - function-call argument count mismatch using the Stage 1 code,
  - function-call argument type mismatch using the Stage 1 code,
  - absence of the legacy Stage 2-only substitute codes `TYP-0320` and `TYP-0321`.
- Add new Stage 2 typing fixtures only where the existing fixture set does not already isolate the corrected condition.

## Tests

Minimum verification:

```bash
make DEA_BUILD_DIR=build/dev-dea test-stage2 TESTS="expr_types_test"
```

Final verification after the audit/fix pass:

```bash
make DEA_BUILD_DIR=build/dev-dea test-stage2
make DEA_BUILD_DIR=build/dev-dea test-stage2-trace
```

Specific acceptance checks:

1. Stage 2 function-call arity mismatch reuses Stage 1 `TYP-0183`.
2. Stage 2 function-call argument type mismatch reuses Stage 1 `TYP-0312`.
3. No corrected condition regresses to a Stage 2-only substitute code.
4. The shared catalog document matches the current registered Stage 1 family inventory.

Verification completed for this fix:

```bash
make DEA_BUILD_DIR=build/dev-dea test-stage2 TESTS="expr_types_test"
```

## Related Docs

- `l0/docs/specs/compiler/diagnostic-code-policy.md`
- `docs/specs/compiler/diagnostic-code-catalog.md`
- `l0/work/plans/bug-fixes/closed/2026-04-03-stage2-0310-0311-diagnostic-parity-noref.md`
- `l0/work/plans/bug-fixes/closed/2026-04-03-stage2-pointer-cast-parity-noref.md`

## Assumptions

- Stage 1 Python remains the canonical oracle for diagnostic-code meaning.
- The registered family inventory in `compiler/stage1_py/l0_diagnostics.py` is complete for user-facing compiler codes.
- Internal `ICE-xxxx` tracking can remain search-based for now; this audit only requires the shared catalog of the
  centrally registered compiler diagnostic families.
