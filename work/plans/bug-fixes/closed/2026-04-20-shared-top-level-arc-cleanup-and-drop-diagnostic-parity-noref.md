# Bug Fix Plan

## Shared top-level ARC cleanup and module-let drop diagnostic parity

- Date: 2026-04-20
- Status: Closed
- Title: Restore shared top-level ARC cleanup and dedicated module-let drop diagnostics across L0 and L1
- Kind: Bug Fix
- Scope: Shared
- Severity: High
- Stage: Shared
- Targets:
  - L0 Python Stage 1
  - L0 Stage 2
  - L1 Stage 1
- Origin: L0 top-level ARC follow-up, where new top-level string reassignment trace coverage exposed missing final
  wrapper cleanup and misleading module-let `drop` diagnostics
- Porting rule: Settle the cleanup and diagnostic behavior in L0 first, then port it mechanically into the homologous L0
  Stage 2 and L1 Stage 1 paths while keeping ARC/top-level regression coverage aligned
- Target status:
  - L0 Python Stage 1: Implemented
  - L0 Stage 2: Implemented
  - L1 Stage 1: Implemented
- Subsystem: Top-level let ARC cleanup, `drop` diagnostics, and ARC/top-level regression parity
- Modules:
  - `docs/specs/compiler/diagnostic-code-catalog.md`
  - `l0/compiler/stage1_py/l0_c_emitter.py`
  - `l0/compiler/stage1_py/l0_diagnostics.py`
  - `l0/compiler/stage1_py/l0_expr_types.py`
  - `l0/compiler/stage2_l0/src/c_emitter.l0`
  - `l0/compiler/stage2_l0/src/expr_types.l0`
  - `l1/compiler/stage1_l0/src/c_emitter.l0`
  - `l1/compiler/stage1_l0/src/expr_types.l0`
- Test modules:
  - `l0/compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py`
  - `l0/compiler/stage1_py/tests/integration/test_toplet.py`
  - `l0/compiler/stage2_l0/tests/c_emitter_test.l0`
  - `l0/compiler/stage2_l0/tests/expr_types_test.l0`
  - `l0/compiler/stage2_l0/tests/l0c_stage2_arc_trace_regression_test.py`
  - `l0/compiler/stage2_l0/tests/l0c_stage2_cleanup_policy_ice_test.py`
  - `l0/compiler/stage2_l0/tests/l0c_stage2_toplet_test.py`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/c_emitter_test.l0`
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`
  - `l1/compiler/stage1_l0/tests/l1c_stage1_arc_trace_regression_test.py`
  - `l1/compiler/stage1_l0/tests/l1c_stage1_cleanup_policy_ice_test.py`
  - `l1/compiler/stage1_l0/tests/l1c_stage1_toplet_test.py`
- Related:
  - `work/plans/bug-fixes/closed/2026-04-20-shared-casted-place-null-propagation-arc-noref.md`
  - `l0/docs/reference/ownership.md`
  - `l1/docs/reference/ownership.md`
- Repro: `cd l0 && make test-stage2 TESTS="l0c_stage2_toplet_test.py"` after adding a top-level string reassignment case
  and `drop gp;`

## Summary

Top-level ARC and `drop` follow-up work exposed two shared defects in the current compiler family:

1. ARC-managed module-level lets were cleaned up on reassignment but not during final process exit.
2. `drop` on a module-level let fell through the local-only path and reported `TYP-0060 unknown variable` even though
   the symbol existed.

The follow-up parity work also showed that L0 Stage 2 and L1 Stage 1 needed dedicated regression suites for this slice
instead of relying only on broader implementation tests.

## Root Cause

The generated C entry wrappers returned directly from user `main` after `_rt_init_args(...)` and optional hidden module
initialization. They never walked the analyzed module graph to release ARC-managed top-level lets that remained live at
process exit.

Separately, `drop` typing checked only the local scope before reporting an error. When the name resolved to a
module-level `let`, the implementation did not distinguish that case from a truly missing variable, so the diagnostic
wording was both misleading and too coarse.

## Scope of This Fix

1. Introduce a dedicated diagnostic for `drop` on module-level lets and wire it into the shared diagnostic surface.
2. Add final top-level ARC cleanup to the generated `main()` wrappers in every in-scope implementation.
3. Add explicit regression coverage for top-level string reassignment, module-let `drop`, ARC trace parity, and the
   cleanup-policy ICE paths that support the same ownership area.

## Approach

- Add `TYP-0063` for `cannot drop module-level let` where local lookup fails but symbol lookup resolves `SYM_LET`.
- Reuse the analyzed module list and signature tables in each emitter to walk root modules, find `TD_LET` declarations,
  and release only those whose types carry ARC data.
- Change the generated wrappers to compute an exit code first, run top-level cleanup, and then return the saved exit
  code so cleanup runs for `int`, `bool`, and `void` entry signatures.
- Mirror the new L0 Stage 2 top-level and ARC-trace coverage in L1 Stage 1 with dedicated Python regression suites, and
  keep the implementation-layer cleanup-policy ICE checks on the bootstrap compiler path where the compiler sources
  actually live.

## Tests

Minimum coverage for the landed fix:

1. shared diagnostic coverage includes the dedicated module-let `drop` code,
2. top-level string reassignment is leak-free and still releases overwritten heap values,
3. generated wrappers preserve the hidden global-init ordering and now clean up top-level ARC state before returning,
4. L0 Stage 2 and L1 Stage 1 carry explicit ARC trace regressions for the parity slice audited in this follow-up,
5. emitter cleanup helpers still raise the expected ICEs when struct/enum cleanup metadata is missing.

## Verification

```bash
cd l0 && ../.venv/bin/python -m pytest -n0 compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py compiler/stage1_py/tests/integration/test_toplet.py
cd l0 && make test-stage2 TESTS="c_emitter_test expr_types_test diagnostic_code_parity_test.py diagnostic_message_parity_test.py l0c_stage2_arc_trace_regression_test.py l0c_stage2_cleanup_policy_ice_test.py l0c_stage2_toplet_test.py"
cd l1 && make test-stage1 TESTS="expr_types_test c_emitter_test backend_test l0c_lib_test diagnostic_code_parity_test.py diagnostic_message_parity_test.py l1c_stage1_cleanup_policy_ice_test.py l1c_stage1_toplet_test.py l1c_stage1_arc_trace_regression_test.py"
```

## Outcome

- Added shared `TYP-0063` coverage for `drop` on module-level lets and retired the misleading `TYP-0060` wording for
  that case.
- Fixed final ARC cleanup for module-level lets in the L0 Python, L0 Stage 2, and L1 Stage 1 emitters.
- Added dedicated top-level and ARC-trace regression coverage in L0 Stage 2 and L1 Stage 1, plus implementation-layer
  cleanup-policy ICE coverage for the self-hosted emitters.
