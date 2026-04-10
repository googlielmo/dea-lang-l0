# Bug Fix Plan

## Shared unreachable warning parity

- Date: 2026-04-10
- Status: Closed
- Title: Restore shared unreachable-code warning parity in self-hosted statement checking
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
- Subsystem: Statement analysis / Control Flow / Warnings
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l0/compiler/stage2_l0/tests/fixtures/typing/*.l0`, `l1/compiler/stage1_l0/src/expr_types.l0`,
  `l1/compiler/stage1_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/fixtures/typing/*.l1`,
  `l0/compiler/stage1_py/l0_expr_types.py`, `docs/specs/compiler/diagnostic-code-catalog.md`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: `make -C l0 test-stage2 TESTS="expr_types_test"` and `make -C l1 test-stage1 TESTS="expr_types_test"`

## Summary

Python Stage 1 emits control-flow warnings for unreachable statements, but the self-hosted compilers currently stay
silent.

The confirmed gaps are:

- `TYP-0031` after a statement that definitely returns,
- `TYP-0030` after `break` / `continue` make the next statement unreachable.

This fix restores those warnings in the shared self-hosted statement checker without widening scope into a broader
dead-code analysis project.

Implemented outcome:

- both self-hosted compilers now emit `TYP-0031` for the first unreachable statement after a guaranteed return path,
- both self-hosted compilers now emit `TYP-0030` for the first unreachable statement after `break` / `continue`,
- focused warning-only fixtures and `expr_types_test` coverage now lock the regression in both trees.

## Root Cause

The self-hosted checker already computes a minimal definite-return summary for statements, but it does not retain any
block-local reachability state while iterating later statements in the same block.

As a result:

- statements after guaranteed return paths are still type-checked but never warned as unreachable,
- statements after `break` / `continue` are still type-checked but never warned as unreachable.

## Scope of This Fix

1. Add Stage 1-equivalent unreachable warnings to the self-hosted block walker.
2. Emit:
   - `TYP-0031` for the first unreachable statement after a guaranteed return path,
   - `TYP-0030` for the first unreachable statement after `break` / `continue`.
3. Preserve the Stage 1 behavior that conditional loop control does not incorrectly mark following statements
   unreachable.
4. Keep the fix limited to the current statement checker; do not expand into new optimizer-style reachability analysis.

## Approach

### Block-local reachability tracking

- Extend the checker state with a small `next statement unreachable` flag.
- In block iteration:
  - warn once with `TYP-0031` when an earlier statement guarantees return,
  - otherwise warn once with `TYP-0030` when the flag is set.
- Continue type-checking unreachable statements so existing diagnostics are still reported.

### Statement propagation

- Set the `next statement unreachable` flag for `break` and `continue`.
- Keep return-path tracking separate so direct and structural returns still drive `TYP-0031`.
- Mirror the Python Stage 1 `if` propagation shape closely enough to avoid false unreachable warnings after conditional
  `continue`.

### Porting

- Stabilize the behavior and tests in `l0/compiler/stage2_l0` first.
- Port mechanically into `l1/compiler/stage1_l0`.

## Tests

Minimum coverage to add in both trees:

1. A warning-only fixture with code after `return` reports `TYP-0031`.
2. A warning-only fixture with code after `break` reports `TYP-0030`.
3. A loop fixture with conditional `continue` does not report `TYP-0030`.

## Verification

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_unreachable_warn_ok
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_unreachable_warn_ok
```

Verification completed for this fix:

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_unreachable_warn_ok
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_unreachable_warn_ok
```

## Related Work

- `work/plans/bug-fixes/2026-04-10-shared-self-hosted-stage1-statement-parity-audit-noref.md`

## Assumptions

- Python Stage 1 remains the behavioral oracle for `TYP-0030` / `TYP-0031`.
- Existing self-hosted return-flow tracking is sufficient; this fix should only add the missing warning surface and the
  minimum propagation state needed to make it correct.
