# Bug Fix Plan

## Shared field/index diagnostic parity

- Date: 2026-04-03
- Status: Closed
- Title: Fix shared field-access and indexing diagnostic parity drift in L0 Stage 2 and L1 Stage 1
- Kind: Bug Fix
- Severity: High
- Stage: Shared
- Subsystem: Type Checker
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l0/compiler/stage2_l0/tests/fixtures/typing/typing_err.l0`, `l1/compiler/stage1_l0/src/expr_types.l0`,
  `l1/compiler/stage1_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/fixtures/typing/typing_err.l1`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: `make -C l0 test-stage2 TESTS="expr_types_test"` and `make -C l1 test-stage1 TESTS="expr_types_test"`

## Summary

L0 Stage 2 and L1 Stage 1 still share two older expression-checker drifts that were not covered by the earlier
function-call, constructor, cast, and mismatch-code parity fixes.

The current shared drift is:

- field access still collapses multiple distinct Stage 1 conditions into `TYP-0340`
- indexing still carries the old non-parity base-expression code `TYP-0350`

Both implementations are still homologous in these paths, so the intended fix should be designed once against the Stage
1 oracle and then applied to both trees together.

## Root Cause

L0 Stage 2 retained older coarse-grained diagnostics in its field and index helpers before the broader parity work was
finished.

L1 Stage 1 was bootstrapped from that earlier Stage 2 implementation and inherited the same call-site structure and
legacy numbering.

Because the previous parity work focused on cast validation, call arity/type mismatches, constructor mismatches, and the
`TYP-0310`/`TYP-0311` split, these remaining helper-local drifts were left behind in both trees.

## Scope of This Fix

1. Audit field-access diagnostics in both trees against Python Stage 1 `TYP-0220`, `TYP-0221`, and `TYP-0222`.
2. Audit indexing diagnostics in both trees against Python Stage 1 `TYP-0210`, `TYP-0211`, and `TYP-0212`.
3. Replace shared legacy codes only when the Stage 1 condition is meaning-equivalent.
4. Add fixture-backed regression coverage for each corrected field/index condition in both trees.
5. Keep this plan limited to the shared L0 Stage 2 and L1 Stage 1 parity drift above; do not fold in unrelated
   diagnostic cleanup.

## Approach

### Field access

- Use `l0/compiler/stage1_py/l0_expr_types.py` and `l0/compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py` as
  the meaning oracle.
- Split the current coarse `TYP-0340` path into the Stage 1-equivalent conditions:
  - `TYP-0220` for nullable-struct field access,
  - `TYP-0221` for missing field on a struct,
  - `TYP-0222` for field access on a non-struct type.
- Update existing `typing_err` coverage so missing-field cases assert the Stage 1-equivalent code rather than the shared
  legacy substitute.
- Add focused fixtures when the current suite does not yet isolate nullable-struct and non-struct field-access cases.

### Indexing

- Confirm the current intended operator contract for `[]` in L0 Stage 2 and L1 Stage 1 before changing behavior.
- If the existing pointer-indexing path is meant to match the Stage 1 expression contract, remap the diagnostics to the
  Stage 1-equivalent codes and remove `TYP-0350`.
- If pointer indexing is intentionally outside the Stage 1 contract, stop treating `TYP-0350` as a valid long-term
  substitute and choose one of:
  - reject the operation using existing Stage 1-equivalent diagnostics when the condition is equivalent, or
  - deliberately allocate/document a Dea-wide code only if the behavior is truly non-equivalent and intended to stay.
- Preserve the already-correct `TYP-0210` reuse for non-integer index expressions unless the contract audit shows that
  the entire indexing path should be restructured.

### Sequencing

- Fix L0 Stage 2 first because it is the upstream implementation template for the current L1 Stage 1 checker.
- Port the settled Stage 2 logic to L1 Stage 1 while the two code paths are still structurally aligned.
- Update shared docs only if the final resolution keeps any non-Stage-1-equivalent code as an intentional Dea-wide
  diagnostic.

## Tests

Minimum new coverage to add in both trees:

1. Missing field on a struct reports the Stage 1-equivalent field-missing code.
2. Field access on a non-struct reports the Stage 1-equivalent non-struct code.
3. Nullable-struct field access reports the Stage 1-equivalent nullable-field-access code.
4. Non-integer index expressions keep the correct Stage 1-equivalent index-type code.
5. Invalid index base expressions no longer rely on `TYP-0350` unless the audit explicitly justifies a retained Dea-wide
   code.

## Verification

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
```

After the implementation pass:

```bash
make -C l0 test-stage2
make -C l1 test-stage1
```

## Related Work

- `l0/docs/plans/bug-fixes/closed/2026-04-03-stage2-diagnostic-code-parity-audit-noref.md`
- `l1/docs/plans/bug-fixes/closed/2026-04-03-l1-stage1-pointer-cast-parity-noref.md`

## Assumptions

- Python Stage 1 remains the canonical oracle for diagnostic-code meaning.
- L0 Stage 2 and L1 Stage 1 should keep reusing the same user-facing codes when they represent the same condition.
- The remaining field/index drift is still localized enough to fix without broader parser or AST refactoring.
