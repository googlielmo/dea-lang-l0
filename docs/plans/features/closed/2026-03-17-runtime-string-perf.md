# Feature Plan

## Runtime and string performance optimizations

- Date: 2026-03-17
- Status: Closed (implemented)
- Title: Fix memory/string performance bottlenecks causing Stage 2 slowness
- Kind: Feature
- Severity: Critical
- Stage: Shared
- Subsystem: Runtime / stdlib / codegen
- Modules:
  - `compiler/shared/runtime/l0_runtime.h`
  - `compiler/shared/l0/stdlib/sys/rt.l0`
  - `compiler/shared/l0/stdlib/std/vector.l0`
  - `compiler/shared/l0/stdlib/std/text.l0`
  - `compiler/stage2_l0/src/c_emitter.l0`
- Test modules:
  - `compiler/stage1_py/tests/` (full suite)
  - `compiler/stage2_l0/tests/` (full suite + trace + triple-test)

## Summary

The Stage 2 self-hosting compiler was slower than necessary due to three compounding algorithmic bottlenecks on hot
paths.

## Changes

### 1. `_rt_drop` hash set (critical)

Replaced the `_rt_alloc_list` singly-linked list with an open-addressing hash table (`void*` slots, power-of-2 capacity,
linear probing, tombstone deletion, 70% load growth). Every `drop` was O(n) list walk; now O(1) amortized.

### 2. Bulk `cb_append_s` / `cb_append_slice`

Added `rt_string_bytes_ptr` (runtime, exposed via `sys.rt`) and `vec_push_bytes` (`std.vector`) to enable bulk memcpy
into `CharBuffer`. Replaced byte-by-byte loops in `cb_append_s` and `cb_append_slice` with single reserve + memcpy.

### 3. Cached indentation prefix in `CCodeBuilder`

Added `cached_prefix` / `cached_level` fields. `ccb_prefix` returns the cached string when indent level is unchanged,
avoiding StringBuffer allocation on every emitted line.

## Results

Triple-bootstrap wall time: **~168s -> ~7.8s** (21.5x speedup, median of 3 runs each).
