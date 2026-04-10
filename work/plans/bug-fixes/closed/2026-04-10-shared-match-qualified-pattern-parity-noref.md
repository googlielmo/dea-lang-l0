# Bug Fix Plan

## Shared match-qualified-pattern parity

- Date: 2026-04-10
- Status: Closed
- Title: Restore shared module-qualified `match` pattern parity in self-hosted statement checking
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
- Subsystem: Statement analysis / Match typing
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l0/compiler/stage2_l0/tests/expr_types_test.l0`,
  `l0/compiler/stage2_l0/tests/fixtures/typing/*.l0`, `l1/compiler/stage1_l0/src/expr_types.l0`,
  `l1/compiler/stage1_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/fixtures/typing/*.l1`,
  `l0/compiler/stage1_py/l0_expr_types.py`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: direct `--check` smoke tests on `Color::Red`-style `match` arm patterns

## Summary

Python Stage 1 rejects module-qualified `match` arm patterns that do not resolve to a valid variant of the matched enum,
while the self-hosted compilers currently accept those patterns silently.

This fix restores the Stage 1 pattern-resolution checks for module-qualified `match` patterns in both self-hosted
checkers.

## Root Cause

The self-hosted `match` arm validator currently checks only the unqualified variant name against enum metadata. It
ignores `pattern.module_path` and therefore never rejects qualified paths that resolve to the wrong module or to no
imported module at all.

## Scope of This Fix

1. Reject invalid module-qualified `match` patterns with Stage 1-equivalent `TYP-0102`.
2. Preserve the already-landed unqualified `TYP-0100` / `TYP-0101` / `TYP-0102` behavior.
3. Keep scope limited to qualified pattern-path handling in `match`.

## Approach

- Extend the self-hosted match-pattern validator to inspect `pattern.module_path`.
- Mirror Python Stage 1’s imported-module, unknown-module, and wrong-symbol checks for qualified patterns.
- Add one focused fixture per target covering a qualified pattern that Python rejects and the self-hosted compilers
  currently accept.

## Tests

Minimum coverage to add in both trees:

1. `Color::Red`-style qualified patterns that do not resolve for the matched enum report `TYP-0102`,
2. existing `match` diagnostic tests continue to pass.

## Verification

```bash
make -C l0 test-stage2 TESTS="expr_types_test"
make -C l1 test-stage1 TESTS="expr_types_test"
./l0/build/dea/bin/l0c-stage2 --check -P l0/compiler/stage2_l0/tests/fixtures/typing typing_match_qualified_pattern_err
./l1/build/dea/bin/l1c-stage1 --check -P l1/compiler/stage1_l0/tests/fixtures/typing typing_match_qualified_pattern_err
```

## Outcome

- Implemented Stage 1-equivalent module-qualified pattern resolution in both self-hosted `match` validators.
- Added focused `typing_match_qualified_pattern_err` fixtures plus explicit assertions in both `expr_types_test.l0`
  suites.
- Verified both self-hosted CLIs now reject the focused fixture with `TYP-0102`.

## Related Work

- `work/plans/bug-fixes/2026-04-10-shared-self-hosted-stage1-statement-parity-audit-noref.md`

## Assumptions

- Python Stage 1 remains the behavioral oracle for qualified `match` pattern resolution.
