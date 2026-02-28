# Bug Fix Plan

## Stage 1 backend releases uninitialized ARC local after `continue` in lowered loop

- Date: 2026-02-28
- Status: Closed (fixed)
- Title: Fix Stage 1 loop lowering that emits ARC cleanup for a local not initialized on `continue` paths
- Kind: Bug Fix
- Severity: Critical (valid program can compile to UB and crash at runtime)
- Stage: 1
- Subsystem: Backend Codegen
- Modules:
  - `compiler/stage1_py/l0_backend.py`
  - `compiler/stage1_py/tests/backend/test_codegen_semantics.py`
  - `compiler/stage1_py/tests/backend/test_trace_arc.py`
- Repro:
  - Observed through Stage 2 semantic analysis in `compiler/stage2_l0/src/name_resolver.l0`
  - Current Stage 2 workaround rewrites the loop shape in `compiler/stage2_l0/src/name_resolver.l0`

## Summary

Stage 1 currently mis-lowers a loop pattern where:

1. an iteration may `continue` before an ARC-managed local is declared and initialized, and
2. that local appears later in the loop body.

The generated C still emits `rt_string_release(...)` for that local at loop-iteration end, even on the early
`continue` path where the local was never initialized.

This is a Stage 1 backend defect. The Stage 2 semantic fix only works around it by restructuring the source loop to
avoid the problematic lowering shape.

## Root cause

In the affected lowering, loop-scope ARC cleanup is emitted at the end of the generated loop iteration without being
guarded by whether the corresponding local declaration/initializer actually executed on that path.

Observed generated shape from the original `nr_open_imports_one(...)` loop:

```c
if (!spm_slot_occupied(imported_env->locals, i)) {
    goto __lcont_320;
}
l0_string name = l0_std_hashmap_spm_slot_key(imported_env->locals, i);
...
__lcont_320:;
i = (_rt_iadd(i, 1));
rt_string_release(name);
```

On iterations where `spm_slot_occupied(...)` is false, control jumps directly to `__lcont_320`, but `name` is still
released afterward despite being uninitialized.

That is invalid C-level behavior and can manifest as:

1. release of garbage pointer values,
2. double-free-like trace corruption,
3. non-deterministic crashes in otherwise valid programs.

## Concrete repro

Original Stage 2 source shape before workaround:

```l0
for (let i = 0; i < spm_capacity(imported_env.locals); i = i + 1) {
    if (!spm_slot_occupied(imported_env.locals, i)) {
        continue;
    }

    let name = spm_slot_key(imported_env.locals, i);
    let sym = spm_slot_value(imported_env.locals, i) as Symbol*;
    ...
}
```

The issue was observed while tracing:

```bash
./l0c --trace-memory --trace-arc -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/analysis_trace_test.l0
```

Before the Stage 2 workaround, the generated trace showed corrupted releases originating from
`compiler/stage2_l0/src/name_resolver.l0:271`.

## Scope of this fix

1. Fix Stage 1 loop lowering so ARC cleanup is emitted only for locals definitely initialized on the current path.
2. Add a direct Stage 1 backend regression for the `continue-before-ARC-local` loop shape.
3. Add regressions for multi-resource loop bodies where ARC locals are initialized at different steps and control may
   exit between acquisitions.
4. Add trace regressions that would fail if an uninitialized ARC local is released or if an early exit skips required
   cleanup for already-acquired locals.
5. Keep language semantics unchanged.
6. Keep the Stage 2 workaround in place until the Stage 1 fix is validated, then decide separately whether to simplify it.

## Fix implemented

### A. Split loop cleanup targets for `break` vs `continue`

File: `compiler/stage1_py/l0_backend.py`

The backend previously used one loop-cleanup path for both `break` and `continue`.
That was wrong for `for` loops because:

1. `continue` should clean only the current iteration body scope, then run the update step,
2. `break` should clean both the current iteration body scope and the `for` header scope before leaving the loop.

The fix changes `_emit_cleanup_for_loop_exit(...)` to accept `is_break: bool` and replaces the single
`_loop_scope_stack` with a `_loop_cleanup_scope_stack` of `(continue_cleanup_scope, break_cleanup_scope)` pairs.

This makes cleanup target selection path-sensitive:

1. `while`: `continue` and `break` both clean to the loop body scope.
2. `for`: `continue` cleans only to the loop body scope, while `break` cleans through the outer `for` scope.

### B. Move `for` body cleanup before the shared `continue` epilogue

File: `compiler/stage1_py/l0_backend.py`

`for` lowering previously emitted:

1. body statements,
2. `continue` label,
3. update statement,
4. loop-body cleanup.

That allowed `continue` to jump past local initialization and still reach cleanup that released those locals.

The fix restructures `for` lowering so it emits:

1. nested body block and body-scope cleanup,
2. close body scope,
3. `continue` label,
4. update statement,
5. outer `for` scope cleanup at loop exit.

This preserves normal `continue` semantics while removing the invalid ARC cleanup path.

### C. Add a backend codegen regression

File: `compiler/stage1_py/tests/backend/test_codegen_semantics.py`

Added `test_codegen_loop_continue_does_not_release_uninitialized_arc_local`.

The test builds the failing loop shape and asserts the generated C no longer contains a `continue` jump to a shared
label that later unconditionally releases an ARC local declared after the `continue`.

Follow-up coverage added:

1. `test_codegen_loop_continue_cleans_only_acquired_arc_locals`
2. `test_codegen_loop_break_cleans_only_acquired_arc_locals`
3. `test_codegen_loop_return_cleans_only_acquired_arc_locals`

These tests cover loop bodies where multiple ARC locals are initialized at different points and verify the generated C
cleans only the locals acquired on the active control-flow path:

1. early `continue`/`break`/`return` before any ARC local emits no cleanup for later locals,
2. mid-body exits after acquiring only `a` release only `a`,
3. later exits after acquiring both `a` and `b` release both in reverse order.

### D. Add a runtime trace regression

File: `compiler/stage1_py/tests/backend/test_trace_arc.py`

Added `test_trace_arc_loop_continue_skips_uninitialized_arc_cleanup`.

The test executes the problematic loop shape under ARC tracing, takes the early `continue` path, asserts the program
runs successfully, and checks that heap ARC refcount values stay in a sane range.

Follow-up coverage added:

1. `test_trace_arc_loop_continue_cleans_only_acquired_arc_locals`
2. `test_trace_arc_loop_break_after_single_arc_local_cleans_that_local`
3. `test_trace_arc_loop_return_after_single_arc_local_cleans_that_local`

These trace tests validate the runtime behavior of the lowered control flow:

1. multi-`continue` paths in a loop with two ARC locals do not produce corrupted refcounts and free the expected heap
   values,
2. `break` after one ARC acquisition frees that value before leaving the loop,
3. `return` after one ARC acquisition frees that value before returning from the function.

## Verification

Executed:

```bash
pytest -q compiler/stage1_py/tests/backend/test_codegen_semantics.py -k "loop_continue_does_not_release_uninitialized_arc_local"
pytest -q compiler/stage1_py/tests/backend/test_codegen_semantics.py -k "loop_continue_cleans_only_acquired_arc_locals"
pytest -q compiler/stage1_py/tests/backend/test_codegen_semantics.py -k "loop_break_cleans_only_acquired_arc_locals or loop_return_cleans_only_acquired_arc_locals"
pytest -q compiler/stage1_py/tests/backend/test_trace_arc.py -k "loop_continue_skips_uninitialized_arc_cleanup"
pytest -q compiler/stage1_py/tests/backend/test_trace_arc.py -k "loop_continue_cleans_only_acquired_arc_locals"
pytest -q compiler/stage1_py/tests/backend/test_trace_arc.py -k "loop_break_after_single_arc_local_cleans_that_local or loop_return_after_single_arc_local_cleans_that_local"
pytest -q compiler/stage1_py/tests/integration/test_case_statement.py -k "continue_inside_while or break_inside_for"
pytest -n auto compiler/stage1_py
./compiler/stage2_l0/run_trace_tests.sh
```

Observed:

1. the original `continue-before-ARC-local` regressions pass,
2. the new multi-resource `continue` codegen and trace regressions pass,
3. the new `break` and `return` cleanup regressions pass,
4. existing loop control-flow regressions pass,
5. full Stage 1 test suite passes (`1017 passed`),
6. Stage 2 trace suite still passes,
7. no generated C path releases an ARC local before initialization or skips cleanup for already-acquired loop-body ARC locals on `continue`, `break`, or `return`.

## Current workaround

`compiler/stage2_l0/src/name_resolver.l0` was rewritten from:

1. `if (!occupied) { continue; }`
2. followed by `let name = ...`

to:

1. `if (occupied) { let name = ...; ... }`

This avoids the buggy lowering pattern without changing Stage 2 behavior. After the Stage 1 fix, the workaround is no
longer required for correctness, but it remains a valid source-level shape and can be simplified separately if desired.

## Assumptions

1. The defect is in Stage 1 backend control-flow/cleanup lowering, not in the runtime ARC primitives.
2. The defect is broader than `name_resolver.l0`; any similar loop shape with a post-`continue` ARC local may be affected.
3. No external tracker item exists yet (`noref`).
