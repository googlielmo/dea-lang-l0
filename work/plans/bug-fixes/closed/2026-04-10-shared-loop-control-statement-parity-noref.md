# Bug Fix Plan

## Shared loop-control statement parity

- Date: 2026-04-10
- Status: Closed
- Title: Restore shared `break` / `continue` statement parity in self-hosted statement checking
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
- Subsystem: Statement analysis / Control Flow / Diagnostics
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l0/compiler/stage2_l0/tests/fixtures/typing/*.l0`, `l1/compiler/stage1_l0/src/expr_types.l0`,
  `l1/compiler/stage1_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/fixtures/typing/*.l1`,
  `l0/compiler/stage1_py/l0_expr_types.py`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: `make -C l0 test-stage2 TESTS="expr_types_test"` and `make -C l1 test-stage1 TESTS="expr_types_test"`

## Summary

Python Stage 1 rejects `break` and `continue` statements that appear outside a loop, but the self-hosted compilers
currently accept them silently.

That is a behavior-changing parity gap: invalid programs compile successfully instead of reporting the Stage 1
diagnostics `TYP-0110` and `TYP-0120`.

This plan restores the missing shared loop-control validation without expanding into a larger reachability analysis
project.

Implemented outcome:

- both self-hosted compilers now reject `break` outside loops with `TYP-0110`,
- both self-hosted compilers now reject `continue` outside loops with `TYP-0120`,
- focused typing fixtures and `expr_types_test` coverage now lock the regression in both trees.

## Root Cause

The self-hosted statement checker walks `ST_BREAK` and `ST_CONTINUE`, but it has no notion of whether the current
statement is nested inside a breakable loop.

As a result:

- `break` never validates that it appears inside `while` or `for`,
- `continue` never validates that it appears inside `while` or `for`,
- invalid loop-control statements are accepted in both self-hosted trees.

## Scope of This Fix

1. Add loop-depth tracking to the self-hosted statement checker.
2. Emit Stage 1-equivalent diagnostics for invalid loop control:
   - `TYP-0110` for `break` outside a loop,
   - `TYP-0120` for `continue` outside a loop.
3. Treat `while` and `for` bodies as breakable regions.
4. Keep the fix limited to statement validation for loop-control placement; do not broaden it into unreachable-code or
   dead-code diagnostics.

## Approach

### Loop-depth tracking

- Extend the checker state with a small loop-depth counter.
- Increment before checking a `while` body and decrement after it finishes.
- For `for`, keep Stage 1 behavior:
  - check init, condition, and update outside loop depth,
  - check only the loop body under loop depth.

### Statement diagnostics

- In `ST_BREAK`, emit `TYP-0110` when loop depth is zero.
- In `ST_CONTINUE`, emit `TYP-0120` when loop depth is zero.
- Reuse the existing Stage 1 message text family rather than introducing new self-hosted-only wording.

### Porting

- Stabilize the behavior and tests in `l0/compiler/stage2_l0` first.
- Port mechanically into `l1/compiler/stage1_l0`.

## Tests

Minimum coverage to add in both trees:

1. A fixture with `break` outside a loop reports `TYP-0110`.
2. A fixture with `continue` outside a loop reports `TYP-0120`.
3. Existing valid `while` / `for` usage continues to type-check.

## Verification

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_loop_control_err
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_loop_control_err
```

Verification completed for this fix:

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_loop_control_err
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_loop_control_err
```

## Related Work

- `work/plans/bug-fixes/2026-04-10-shared-self-hosted-stage1-statement-parity-audit-noref.md`

## Assumptions

- Python Stage 1 remains the behavioral oracle for loop-control placement diagnostics.
- `while` and `for` are the only current breakable statements that need to participate in this parity fix.
