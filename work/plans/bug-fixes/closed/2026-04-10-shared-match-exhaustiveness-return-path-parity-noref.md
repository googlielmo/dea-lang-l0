# Bug Fix Plan

## Shared enum match exhaustiveness and return-path parity

- Date: 2026-04-10
- Status: Closed
- Title: Fix shared enum `match` exhaustiveness and return-path parity in L0 Stage 2 and L1 Stage 1
- Kind: Bug Fix
- Scope: Shared
- Severity: High
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
- Subsystem: Type Checker / Control Flow
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l0/compiler/stage2_l0/tests/fixtures/typing/*.l0`, `l1/compiler/stage1_l0/src/expr_types.l0`,
  `l1/compiler/stage1_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/fixtures/typing/*.l1`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: `make -C l0 test-stage2 TESTS="expr_types_test"` and `make -C l1 test-stage1 TESTS="expr_types_test"`

## Summary

L0 Stage 2 and L1 Stage 1 both accept non-exhaustive enum `match` statements that Python Stage 1 rejects with
`TYP-0104`.

The same self-hosted trees also lack the minimum return-path analysis needed to reject non-void functions whose bodies
can still fall through. As a result, a non-exhaustive `match` inside a non-void function is currently accepted even when
all present arms return.

This fix restores the missing Stage 1 behavior in the shared self-hosted checker without broadening into a general
dead-code or reachability project.

Implemented outcome:

- both self-hosted compilers now emit `TYP-0104` for non-exhaustive enum `match`,
- both self-hosted compilers now emit `TYP-0010` for non-void function fallthrough,
- enum `match` and `case ... else` now participate in definite-return analysis,
- focused typing fixtures and `expr_types_test` coverage now lock the regression in both trees.

## Root Cause

In both self-hosted trees, the `ST_MATCH` branch in `expr_types.l0` only:

- infers the scrutinee type,
- binds payload variables for variant patterns,
- type-checks each arm body.

It never:

- looks up enum coverage information,
- emits `TYP-0104`,
- computes whether the statement definitely returns.

Function checking also discards statement-level control-flow information after `etc_check_stmt(...)`, so there is no
self-hosted equivalent of Stage 1 `TYP-0010` missing-return validation.

## Scope of This Fix

1. Add enum `match` exhaustiveness checking in both self-hosted expression checkers.
2. Reuse Stage 1 `TYP-0104` for non-exhaustive enum matches.
3. Add the minimum statement return-flow tracking needed to decide whether a function body definitely returns.
4. Reuse the Stage 1 missing-return diagnostic for non-void functions whose body can still fall through.
5. Make enum `match` participate in definite-return analysis based on exhaustiveness and per-arm return behavior.
6. Keep this plan limited to enum `match` plus the minimum return-path machinery needed to make the behavior correct.

## Approach

### Return-flow model

- Change the self-hosted statement checker from a pure side-effect walker into a checker that also returns a compact
  flow result indicating whether the statement definitely returns.
- Thread that result through:
  - blocks,
  - `if` / `else`,
  - loops only as far as needed to preserve current behavior,
  - `match`,
  - `return`.
- Keep the model intentionally minimal: this plan only needs a yes/no definite-return summary, not full reachability,
  dead-code reporting, or break/continue-aware loop fixed-point analysis.

### Enum `match` exhaustiveness

- In the `ST_MATCH` path, after scrutinee typing and arm checking:
  - require enum metadata lookup for enum scrutinees,
  - collect explicitly covered variants,
  - detect whether `_` is present,
  - compare covered variants against the enum definition.
- If the match is non-exhaustive, emit `TYP-0104` naming the missing variants in the same Stage 1 condition family.
- Treat `_` as exhaustive coverage.
- Treat exhaustive explicit coverage as exhaustive only when all enum variants are covered exactly once.

### Function return validation

- In `etc_check_function(...)`, use the statement flow result for the function body after type checking.
- If the function return type is non-void and the body is not guaranteed to return, emit the Stage 1 missing-return
  diagnostic instead of accepting the function.
- Ensure a non-exhaustive enum `match` never counts as definitely returning even if every present arm returns.
- Ensure an exhaustive enum `match` counts as definitely returning only when every arm body definitely returns.

### Sequencing

- Implement and stabilize the behavior in `l0/compiler/stage2_l0/src/expr_types.l0` first.
- Add fixture-backed tests in `l0/compiler/stage2_l0/tests`.
- Port the settled logic mechanically into `l1/compiler/stage1_l0/src/expr_types.l0`.
- Mirror the focused fixtures and assertions in `l1/compiler/stage1_l0/tests`.

## Tests

Minimum new coverage to add in both trees:

1. A non-exhaustive enum `match` reports `TYP-0104`.
2. An exhaustive enum `match` covering all variants succeeds.
3. An exhaustive enum `match` using `_` succeeds.
4. A non-void function with a non-exhaustive returning `match` reports both `TYP-0104` and missing-return.
5. A non-void function with an incomplete `if`/fallthrough reports missing-return.
6. A non-void function with an exhaustive `match` whose arms all return does not report missing-return.

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

Add one direct smoke check per target using `--check` on a minimal non-exhaustive enum `match` source file to confirm
CLI-visible behavior.

Verification completed for this fix:

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_match_flow_err
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_match_flow_err
```

## Related Work

- `work/plans/bug-fixes/2026-04-10-shared-match-diagnostic-tail-parity-noref.md`
- `work/plans/bug-fixes/2026-04-10-shared-self-hosted-stage1-statement-parity-audit-noref.md`
- `work/plans/bug-fixes/closed/2026-04-03-shared-field-index-diagnostic-parity-noref.md`

## Assumptions

- Python Stage 1 remains the canonical oracle for diagnostic-code meaning and return-flow behavior.
- This fix should stay narrow and not expand into a full reachability or warning-parity project.
- The two self-hosted trees are still aligned closely enough that the L1 change should remain a mechanical port of the
  settled L0 Stage 2 logic.
