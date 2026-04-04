# Refactor Plan

## Move stage-local Python runner helpers under `scripts/`

- Date: 2026-04-04
- Status: Closed
- Title: Move Stage 2 and L1 Stage 1 Python runner helpers into stage-local `scripts/` subdirectories
- Kind: Refactor
- Scope: Shared
- Severity: Low
- Stage: Shared
- Targets:
  - `l0/compiler/stage2_l0/`
  - `l1/compiler/stage1_l0/`
- Origin: Stage-local compiler subtree layout
- Porting rule: Apply the same `scripts/` subdirectory layout to both stage-local helper sets and update all references
  together
- Target status:
  - `l0/compiler/stage2_l0/`: Implemented
  - `l1/compiler/stage1_l0/`: Implemented
- Subsystem: Test/trace runner layout
- Modules:
  - `l0/compiler/stage2_l0/scripts/`
  - `l1/compiler/stage1_l0/scripts/`
  - `l0/Makefile`
  - `l1/Makefile`
  - stage-local READMEs and reference docs
  - affected tests and historical work references
- Test modules:
  - `l0/tests/test_make_dea_build_workflow.py`
  - `l0/compiler/stage1_py/tests/cli/test_docgen_source_scope.py`

## Summary

The Stage 2 and L1 Stage 1 Python helpers for test execution and trace analysis had been living directly under the stage
directory even though they are support scripts rather than compiler sources.

This refactor moves those helpers under stage-local `scripts/` subdirectories:

- `l0/compiler/stage2_l0/scripts/`
- `l1/compiler/stage1_l0/scripts/`

## Decisions

1. Move each helper set as one unit so sibling imports keep working without introducing package boilerplate.
2. Update the shared path-derivation helpers together with the move so `tests/`, repo roots, and monorepo roots still
   resolve correctly from the new script location.
3. Rewrite Makefile, docs, tests, and plan references in the same change so the old flat layout stops appearing in live
   guidance.

## Work Completed

1. Moved `check_trace_log.py`, `run_test_trace.py`, `run_tests.py`, `run_trace_tests.py`, and `test_runner_common.py`
   into `scripts/` under both stage trees.
2. Updated the common runner helpers to derive the stage directory from the new script location.
3. Updated direct invocations in Makefiles, READMEs, reference docs, tests, and existing work-plan records.

## Verification

1. No live repo references remain to the old flat script paths.
2. Stage-local helper imports still resolve after the move.
3. Stage-local tests/trace helpers continue to point at the correct `tests/` tree and repo roots.
