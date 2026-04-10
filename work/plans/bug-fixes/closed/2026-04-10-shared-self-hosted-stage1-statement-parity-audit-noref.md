# Bug Fix Plan

## Shared self-hosted Stage 1 statement parity audit

- Date: 2026-04-10
- Status: Closed
- Title: Audit remaining self-hosted statement and control-flow parity drift against L0 Stage 1
- Kind: Bug Fix
- Scope: Shared
- Severity: High
- Stage: Shared
- Targets:
  - L0 Stage 2
  - L1 Stage 1
- Origin: L0 Stage 2, using Python Stage 1 as the behavioral oracle
- Porting rule: Audit and settle homologous Stage 2 behavior first, then port confirmed mechanical fixes into L1 Stage 1
  while the code paths remain aligned
- Target status:
  - L0 Stage 2: Implemented
  - L1 Stage 1: Implemented
- Subsystem: Statement analysis / Control Flow / Diagnostics
- Modules: `l0/compiler/stage2_l0/src/expr_types.l0`, `l1/compiler/stage1_l0/src/expr_types.l0`,
  `l0/compiler/stage1_py/l0_expr_types.py`, `l0/compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py`,
  `docs/specs/compiler/diagnostic-code-catalog.md`
- Test modules: `l0/compiler/stage2_l0/tests/expr_types_test.l0`, `l1/compiler/stage1_l0/tests/expr_types_test.l0`
- Repro: `make -C l0 test-stage2 TESTS="expr_types_test"` and `make -C l1 test-stage1 TESTS="expr_types_test"`

## Summary

The missing `TYP-0104` check exposed a broader truth: the self-hosted compilers still do not have full statement-level
and control-flow parity with Python Stage 1.

That remaining work is too large and too open-ended to hide inside one `match` bug fix. It needs a dedicated shared
audit plan that inventories the remaining gaps, prioritizes them, and spins confirmed defects into focused follow-up
shared bug-fix plans.

## Scope of This Audit

1. Audit statement-level and control-flow-sensitive behavior in `L0 Stage 2` against Python Stage 1.
2. Confirm which gaps are inherited mechanically by `L1 Stage 1`.
3. Prioritize behavior-changing acceptance differences ahead of warning-only or message-only differences.
4. Convert confirmed gaps into focused shared bug-fix plans rather than implementing everything under this audit file.
5. Keep the audit centered on statement analysis and control flow, not unrelated expression-typing parity that already
   has narrower plans.

## Audit Areas

### Return-path parity

- Confirm the full set of non-void function fallthrough cases still missing after the primary `match` plan lands.
- Check `if` / `else`, nested blocks, loops, `with`, and combinations of those constructs against Python Stage 1.

### Statement diagnostics

- Compare statement-only diagnostics emitted from the self-hosted checker against their Stage 1 equivalents.
- Focus on missing codes, merged conditions, and silent acceptance where Stage 1 rejects the program.

### Flow-sensitive behavior

- Compare whether self-hosted accepts programs that Stage 1 rejects because of control-flow-sensitive reasoning.
- Record each confirmed difference with:
  - the Stage 1 oracle behavior,
  - the self-hosted current behavior,
  - the target files involved,
  - the narrowest test fixture needed to lock the regression.

## Deliverables

1. A concrete backlog of confirmed parity gaps grouped by behavior area.
2. A priority order separating:
   - correctness bugs that change compile success,
   - diagnostic-code drift,
   - warning-only parity.
3. One or more focused shared bug-fix plans for the highest-priority confirmed gaps.

## Confirmed Gaps

### Active child plans

- None currently recorded.

### Closed child plans

- `work/plans/bug-fixes/closed/2026-04-10-shared-condition-diagnostic-code-parity-noref.md`

  - confirmed gap: `L0 Stage 2` emitted legacy condition codes `TYP-0313` / `TYP-0314` where Python Stage 1 and
    `L1 Stage 1` used `TYP-0070` / `TYP-0080` / `TYP-0090`
  - priority: diagnostic-code parity
  - implemented with L0 Stage 2 code alignment plus focused loop-condition fixtures

- `work/plans/bug-fixes/closed/2026-04-10-shared-let-diagnostic-tail-parity-noref.md`

  - confirmed gap: self-hosted `L0 Stage 2` and `L1 Stage 1` missed Python Stage 1 follow-on `let` diagnostics
    `TYP-0040` and `TYP-0051`
  - priority: diagnostic-tail parity on already-failing programs
  - implemented with supplemental `ST_LET` diagnostics plus focused typing fixtures

- `work/plans/bug-fixes/closed/2026-04-10-shared-match-qualified-pattern-parity-noref.md`

  - confirmed gap: self-hosted `L0 Stage 2` and `L1 Stage 1` accepted module-qualified `match` arm patterns that Python
    Stage 1 rejects as invalid enum variants with `TYP-0102`
  - priority: correctness bug that changes compile success
  - implemented with Stage 1-equivalent `pattern.module_path` resolution in the self-hosted `match` validator

- `work/plans/bug-fixes/closed/2026-04-10-shared-match-pattern-parity-noref.md`

  - confirmed gap: self-hosted `L0 Stage 2` and `L1 Stage 1` accepted non-enum `match` scrutinees, unknown enum variants
    in arm patterns, and payload arity mismatch while Python Stage 1 rejects them with `TYP-0100`, `TYP-0101`, and
    `TYP-0102`
  - priority: correctness bug that changes compile success
  - implemented with Stage 1-equivalent `ST_MATCH` arm validation plus focused typing fixtures

- `work/plans/bug-fixes/closed/2026-04-10-shared-let-initializer-parity-noref.md`

  - confirmed gap: self-hosted `L0 Stage 2` and `L1 Stage 1` accepted explicit `void` locals, inferred `null`
    initializers, and inferred `void` initializers while Python Stage 1 rejects them with `TYP-0050`, `TYP-0052`, and
    `TYP-0053`
  - priority: correctness bug that changes compile success
  - implemented with Stage 1-equivalent `ST_LET` rejection plus focused typing fixtures

- `work/plans/bug-fixes/closed/2026-04-10-shared-with-cleanup-header-guard-parity-noref.md`

  - confirmed gap: self-hosted `L0 Stage 2` and `L1 Stage 1` accepted cleanup-block references to non-nullable `with`
    header variables that may be uninitialized on `?` header-failure paths, while Python Stage 1 rejects them with
    `TYP-0156`
  - priority: correctness bug that changes compile success
  - implemented with header `EX_TRY` detection, temporary cleanup-header guards, and focused typing fixtures

- `work/plans/bug-fixes/closed/2026-04-10-shared-case-diagnostic-parity-noref.md`

  - confirmed gap: self-hosted `L0 Stage 2` and `L1 Stage 1` accepted invalid `case` scrutinees, mismatched arm
    literals, and duplicate literal values while Python Stage 1 rejects them with `TYP-0106` / `TYP-0107` / `TYP-0108`
  - priority: correctness bug that changes compile success
  - implemented with self-hosted `ST_CASE` validation and focused typing fixtures

- `work/plans/bug-fixes/closed/2026-04-10-shared-unreachable-warning-parity-noref.md`

  - confirmed gap: self-hosted `L0 Stage 2` and `L1 Stage 1` did not emit `TYP-0030` / `TYP-0031` unreachable-code
    warnings that Python Stage 1 reports after `break` / `continue` and guaranteed return paths
  - priority: warning-only parity with control-flow sensitivity
  - implemented with checker-local next-statement-unreachable tracking plus focused warning fixtures

- `work/plans/bug-fixes/closed/2026-04-10-shared-loop-control-statement-parity-noref.md`

  - confirmed gap: self-hosted `L0 Stage 2` and `L1 Stage 1` accepted `break` / `continue` outside loops while Python
    Stage 1 rejects them with `TYP-0110` / `TYP-0120`
  - priority: correctness bug that changes compile success
  - implemented with checker-local loop-depth tracking plus focused typing fixtures

## Approach

- Use Python Stage 1 source and diagnostic trigger tests as the oracle.
- Start in `l0/compiler/stage2_l0/src/expr_types.l0`, then map each confirmed gap to
  `l1/compiler/stage1_l0/src/expr_types.l0`.
- Reuse the shared diagnostic-code catalog as the cross-check for registered meanings.
- Prefer fixture-backed reproducers over ad hoc command transcripts so each confirmed gap becomes an executable
  regression target.

## Verification

The audit itself is complete when:

1. every confirmed statement/control-flow parity gap is recorded with a minimal reproducer,
2. each high-priority gap has either:
   - a focused shared bug-fix plan, or
   - an explicit defer reason,
3. the remaining work is no longer described as a vague "full parity" bucket.

## Outcome

- Confirmed and fixed the statement/control-flow parity gaps found during the audit as focused child plans.
- Left no active child plans under this audit.
- Reached parity for the audited statement/control-flow behaviors between Python Stage 1 and the self-hosted
  `L0 Stage 2` / `L1 Stage 1` checkers.

## Related Work

- `work/plans/bug-fixes/2026-04-10-shared-match-exhaustiveness-return-path-parity-noref.md`
- `work/plans/bug-fixes/2026-04-10-shared-match-diagnostic-tail-parity-noref.md`
- `l0/work/plans/bug-fixes/closed/2026-04-03-stage2-diagnostic-code-parity-audit-noref.md`

## Assumptions

- L0 Stage 2 remains the upstream implementation template for the current L1 Stage 1 checker.
- The best way to reach "full L0 Stage 1 parity" is a shared audited backlog of focused fixes, not one oversized
  implementation tranche.
