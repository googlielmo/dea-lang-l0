# Refactor Plan

## Move backend-owned C fragments behind emitter helpers in both stages

- Date: 2026-03-22
- Status: Draft
- Title: Move backend-owned C fragments behind emitter helpers in Stage 1 and Stage 2
- Kind: Refactor
- Severity: Medium (internal backend/emitter boundary cleanup with parity-sensitive risk)
- Stage: Shared
- Subsystem: C Backend + C Emitter
- Modules:
  - `compiler/stage1_py/l0_backend.py`
  - `compiler/stage1_py/l0_c_emitter.py`
  - `compiler/stage2_l0/src/backend.l0`
  - `compiler/stage2_l0/src/c_emitter.l0`
  - `compiler/stage2_l0/tests/fixtures/backend_golden/`
  - `docs/reference/c-backend-design.md`
- Test modules:
  - `compiler/stage1_py/tests/backend/test_codegen_semantics.py`
  - `compiler/stage1_py/tests/integration/test_with_statement.py`
  - `compiler/stage2_l0/tests/backend_test.l0`
  - `compiler/stage2_l0/tests/c_emitter_test.l0`
  - `compiler/stage2_l0/tests/l0c_lib_test.l0`
  - `compiler/stage2_l0/tests/l0c_codegen_test.sh`
  - `compiler/stage2_l0/tests/fixtures/backend_golden/null_forms_and_with/`

## Summary

Both compiler backends still synthesize some C syntax directly instead of delegating all C spelling to the emitter
layer. The goal of this refactor is to tighten the backend/emitter boundary in both stages without changing external
behavior.

This is not a full “backend owns no strings” rewrite. Diagnostics, labels, symbol keys, helper selection, and
non-C-facing bookkeeping remain backend responsibilities. The focus is narrower: any string that directly encodes C
syntax or C field access should move behind emitter helpers, and Stage 2 should keep matching Stage 1 as the oracle.

Recent `null` cleanup work already produced one parity fixture that should become the first guardrail for this refactor:
`compiler/stage2_l0/tests/fixtures/backend_golden/null_forms_and_with/`.

## Scope and Non-Goals

### In scope

1. Introduce missing Stage 1/Stage 2 emitter helpers for recurring C fragments currently built in backend code.
2. Replace backend-side C fragment construction with emitter calls where the fragment is pure C spelling.
3. Keep Stage 1 and Stage 2 helper surfaces aligned so equivalent backend conditions use the same abstraction.
4. Add or refresh focused parity tests and Stage 2 backend goldens for each refactor tranche.

### Out of scope

1. Rewriting backend control-flow orchestration, ownership policy, or semantic decision-making.
2. Moving diagnostics, ICE message formatting, or module/type key construction into emitters.
3. Eliminating every string concatenation in backend code; only C-syntax fragments are targeted.
4. Large emitter API redesign unrelated to the currently repeated fragment families.

## Current Fragment Families

The existing leakage falls into a few repeatable groups:

1. Null/optional wrappers:
   - discard-as-statement wrappers such as `(void)(expr)`
   - nullable `has_value` tests
   - nullable `.value` extraction
   - pointer-null checks
   - statement-position no-op literals such as bare `null;`
2. Aggregate/member access:
   - enum `.tag`
   - value field access `(...).field`
   - enum payload field access `(...).data.Variant.field`
3. Condition wrappers and runtime-call spellings:
   - negated conditions `!(...)`
   - string equality helper calls such as `rt_string_equals(...)`
4. Dereference and pointer-form spellings in a few backend-only call sites.

## Target Boundary

After the refactor, the backend should continue deciding:

1. Which helper form to use.
2. Which semantic branch applies.
3. What types and expressions are being lowered.

The emitter should own:

1. The exact C spelling of discard wrappers.
2. The exact C spelling of nullable field access and tests.
3. The exact C spelling of enum-tag and payload-member access.
4. The exact C spelling of pointer-null comparisons and string equality helper calls.

## Implementation Sequence

### Phase 1: Null and optional helper family

1. Add mirrored emitter helpers in Stage 1 and Stage 2 for:
   - discard-as-statement
   - nullable `has_value` condition
   - nullable `value` projection
   - pointer-null condition
   - statement-position no-op literal comments where needed
2. Refactor backend uses of:
   - `(void)(...)`
   - `tmp == NULL`
   - `!tmp.has_value`
   - `(...).has_value`
   - `(...).value`
3. Keep the new `null_forms_and_with` backend-golden case as the tranche entry criterion.

### Phase 2: Aggregate/member access helper family

1. Add mirrored emitter helpers for:
   - enum tag access
   - value field access
   - enum payload field access
2. Refactor backend ownership-cleanup, pattern-binding, and `match` lowering to use those helpers.
3. Refresh or add a golden that exercises:
   - struct-by-value cleanup
   - enum tag switching
   - pattern binding from enum payloads

### Phase 3: Condition-wrapper and runtime-call family

1. Add mirrored emitter helpers for:
   - negated conditions
   - string equality runtime calls
2. Replace backend-built:
   - `!(cond)`
   - `rt_string_equals(...)`
3. Keep this tranche small and avoid coupling it with unrelated control-flow rewrites.

### Phase 4: Residual audit

1. Re-run the inventory search over both backends.
2. Classify remaining string construction as:
   - expected backend metadata/text
   - should still move into emitter
3. Either finish the remaining obvious cases or explicitly document why they remain backend-owned.

## Helper Design Rules

1. Every new Stage 1 emitter helper should have a Stage 2 counterpart with the same responsibility.
2. Helper names should describe C spelling, not semantic policy.
   - Example: “emit nullable has-value access” is better than “emit try success predicate”.
3. Emitters may call smaller emitter helpers internally.
4. Backends should stop open-coding a fragment once an emitter helper exists for it.
5. New helpers must not silently change formatting or grouping rules without a golden or targeted test proving parity.

## Test and Verification Strategy

### Per-phase checks

1. Stage 1 targeted tests for the touched lowering paths.
2. Stage 2 `backend_test.l0` and `c_emitter_test.l0` when helper semantics or direct emitter output changes.
3. Stage 2 `l0c_lib_test.l0` for end-to-end regressions.
4. Stage 2 backend golden parity via `compiler/stage2_l0/tests/l0c_codegen_test.sh`.

### Minimum commands

1. `./.venv/bin/python -m pytest compiler/stage1_py/tests/backend/test_codegen_semantics.py`
2. `./.venv/bin/python -m pytest compiler/stage1_py/tests/integration/test_with_statement.py`
3. `compiler/stage2_l0/tests/l0c_codegen_test.sh <affected-case>`
4. `source build/dea/bin/l0-env.sh && l0c --run -P compiler/stage2_l0/tests -P compiler/stage2_l0/src backend_test`
5. `source build/dea/bin/l0-env.sh && l0c --run -P compiler/stage2_l0/tests -P compiler/stage2_l0/src c_emitter_test`
6. `source build/dea/bin/l0-env.sh && l0c --run -P compiler/stage2_l0/tests -P compiler/stage2_l0/src l0c_lib_test`

## Risks and Constraints

1. The biggest risk is accidental Stage 1/Stage 2 formatting drift in generated C, even when runtime behavior stays
   correct.
2. Some helpers may expose awkward emitter API boundaries; that is acceptable as long as it removes repeated backend
   ownership of the same fragment family.
3. This work should be done in small, reviewable slices. Each slice should land with a golden or targeted parity test.
4. Stage 1 remains the backend oracle. If Stage 2 refactoring reveals a cleaner emitter helper shape, Stage 1 should be
   updated first or in lockstep.

## Exit Criteria

1. The known fragment families listed above are lowered via emitter helpers in both stages.
2. The Stage 2 curated backend goldens pass with no drift against Stage 1 for the affected cases.
3. The remaining backend string construction is limited to non-C metadata or explicitly documented exceptions.
