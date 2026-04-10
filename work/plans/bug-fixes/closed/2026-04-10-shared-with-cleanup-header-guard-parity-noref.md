# Bug Fix Plan

## Shared with-cleanup header guard parity

- Date: 2026-04-10
- Status: Closed
- Title: Restore shared `with` cleanup header-failure guard parity in self-hosted statement checking
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
- Subsystem: Statement analysis / Flow-sensitive diagnostics
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l0/compiler/stage2_l0/tests/fixtures/typing/*.l0`, `l1/compiler/stage1_l0/src/expr_types.l0`,
  `l1/compiler/stage1_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/fixtures/typing/*.l1`,
  `l0/compiler/stage1_py/l0_expr_types.py`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: `make -C l0 test-stage2 TESTS="expr_types_test"` and `make -C l1 test-stage1 TESTS="expr_types_test"`

## Summary

Python Stage 1 rejects references in a `cleanup` block to non-nullable `with` header variables that may be uninitialized
when a `?` header item fails, but the self-hosted compilers currently accept those programs silently.

This fix restores `TYP-0156` in the shared self-hosted checker while keeping scope limited to the confirmed cleanup
header-failure path.

## Root Cause

The self-hosted `ST_WITH` path checks header items, body, inline cleanups, and cleanup blocks, but it does not retain
any state about header items that may be skipped by `?` short-circuiting.

As a result, cleanup-block variable references are resolved as ordinary locals even when the referenced header binding
may not exist along a failure path.

## Scope of This Fix

1. Detect `?` within `with` header item initialization statements.
2. Track non-nullable header `let` bindings that may be uninitialized on a header-failure path.
3. Emit `TYP-0156` when a cleanup block references one of those guarded header bindings.
4. Keep the fix limited to cleanup-block references; do not broaden it into a full definite-initialization project.

## Approach

- Add a small helper to detect whether a header-init statement contains `EX_TRY`.
- During `ST_WITH`, collect the specific header `let` declarations that become maybe-uninitialized once any header item
  can short-circuit via `?`.
- While checking the cleanup block, guard those declarations through a temporary cleanup-header guard stack keyed by the
  visible non-nullable header names.
- Reuse the Stage 1 `TYP-0156` message family rather than introducing new wording.

## Tests

Minimum coverage to add in both trees:

1. cleanup block references to guarded non-nullable header variables report `TYP-0156`,
2. a cleanup block that references only the safe subset still type-checks,
3. existing `with` tests continue to pass.

## Verification

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_with_cleanup_guard_err
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_with_cleanup_guard_ok
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_with_cleanup_guard_err
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_with_cleanup_guard_ok
```

## Outcome

- Implemented `TYP-0156` parity in both self-hosted checkers by detecting header `?` reachability and guarding
  non-nullable `with` header locals while checking cleanup blocks.
- Added focused `typing_with_cleanup_guard_err` and `typing_with_cleanup_guard_ok` fixtures plus explicit assertions in
  both `expr_types_test.l0` suites.
- Verified the self-hosted CLIs reject the guarded-error fixtures and accept the nullable safe-subset fixtures.

## Related Work

- `work/plans/bug-fixes/2026-04-10-shared-self-hosted-stage1-statement-parity-audit-noref.md`

## Assumptions

- Python Stage 1 remains the behavioral oracle for `TYP-0156`.
- The confirmed reachable self-hosted gap is limited to cleanup-block references after `?` in the `with` header.
