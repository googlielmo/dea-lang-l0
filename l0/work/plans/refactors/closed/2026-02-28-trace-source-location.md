# Refactor Plan

## Log L0 source location in memory and ARC traces

- Date: 2026-02-28
- Status: Closed (implemented)
- Title: Enhance ARC and Memory tracing with L0 call-site location reporting
- Kind: Refactor / Feature
- Severity: Medium (Diagnostic improvements)
- Stage: Runtime / Compiler Shared
- Subsystem: Runtime, C Emitter, Trace Analysis
- Modules:
  - `compiler/shared/runtime/l0_runtime.h`
  - `compiler/stage1_py/l0_c_emitter.py`
  - `compiler/stage2_l0/scripts/check_trace_log.py`
  - `docs/specs/runtime/trace.md`
- Test modules:
  - `compiler/stage1_py/tests/backend/test_trace_location.py`
  - `compiler/stage1_py/tests/backend/test_codegen_advanced.py`
  - `compiler/stage1_py/tests/backend/test_codegen_basic.py`

## Summary

Enhance the L0 runtime tracing infrastructure to report the original L0 source file and line number for memory
allocations, deallocations, and reference count operations. This is achieved by refactoring the public `rt_*` runtime
API into C preprocessor macros that capture `__FILE__` and `__LINE__` at the call site in generated C code. Since the L0
compiler emits `#line` directives, these C macros correctly resolve to L0 source coordinates.

The work also includes hardening the C emitter to prevent accidental macro expansion in forward declarations and
updating the `check_trace_log.py` tool to surface this location data in leak triage reports.

## Changes

1. **`l0_runtime.h`**:
   - Refactored `rt_alloc`, `rt_free`, `rt_realloc`, `rt_calloc`, `rt_string_retain`, and `rt_string_release` into
     macro-wrapped `_impl` variants.
   - Updated internal `_rt_alloc_obj`, `_rt_drop`, `_rt_alloc_string`, and `rt_string_concat` to also capture and report
     L0 locations.
   - Added `_RT_TRACE_MEM_LOC` and `_RT_TRACE_ARC_LOC` helper macros to append `loc="file":line` to trace output when
     tracing is enabled.
   - Suppressed GCC 12+ strict `-Wuse-after-free` warnings during realloc by explicitly laundering the pre-realloc
     pointer address through a `volatile uintptr_t` cast. This safely tracks the pointer value for tracing without
     relying on compiler-specific pragmas.
2. **`l0_c_emitter.py`**:
   - Updated `emit_function_declaration` to wrap `extern func` names in parentheses (e.g.,
     `void (rt_alloc)(l0_int bytes);`). This prevents the preprocessor from expanding the runtime's new `rt_*` macros
     inside forward declarations, which would cause compilation errors.
3. **`check_trace_log.py`**:
   - Enhanced the trace parser to extract the `loc` field from log lines.
   - Updated the leak triage logic to store and display the allocation location for leaked objects and strings.
4. **`trace.md`**:
   - Formally documented the `loc` field in the trace specification.
   - Moved source-location reporting from "Non-goals" to the implemented feature set.

## Verification

### Automated Tests

- Added `compiler/stage1_py/tests/backend/test_trace_location.py` with 5 new test cases verifying:
  - Correct `loc` reporting for `rt_alloc`, `rt_free`, `rt_realloc`, `rt_calloc`.
  - Correct `loc` reporting for string ARC operations.
  - End-to-end verification that `check_trace_log.py --triage` correctly surfaces the L0 source location for intentional
    leaks.
- Verified existing Stage 2 trace checks pass (`./compiler/stage2_l0/run_trace_tests.sh`).
- Verified Stage 1 backend tests pass (`pytest compiler/stage1_py/tests/backend/`).

### Manual Verification

- Compiled and ran L0 programs with `--trace-memory` and confirmed that `stderr` output contains valid
  `loc=".../file.l0":line` entries mapping back to the L0 source.
- Confirmed that generated C code compiles without warnings using `clang` and `gcc`.

## Assumptions and Defaults

- C99/C11 `__FILE__` and `__LINE__` are used; column information is not currently reported as there is no standard
  `__COLUMN__` macro.
- Parentheses wrapping in C declarations is applied to all `extern` functions to ensure safety against any runtime macro
  definitions.
