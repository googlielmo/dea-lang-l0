# Feature Plan

## Expand shared stdlib/runtime bootstrap APIs for filesystem, path, metadata, and safe raw byte stdio

- Date: 2026-03-09
- Status: Closed (implemented)
- Title: Add shared stdlib/runtime bootstrap APIs for filesystem helpers, path utilities, file metadata, and safe raw
  byte stdio
- Kind: Feature
- Severity: High
- Stage: Shared
- Subsystem: Standard library and runtime
- Modules:
    - `compiler/shared/l0/stdlib/std/array.l0`
    - `compiler/shared/l0/stdlib/std/io.l0`
    - `compiler/shared/l0/stdlib/std/fs.l0`
    - `compiler/shared/l0/stdlib/std/path.l0`
    - `compiler/shared/l0/stdlib/sys/rt.l0`
    - `compiler/shared/l0/stdlib/sys/unsafe.l0`
    - `compiler/shared/runtime/l0_runtime.h`
    - `compiler/stage2_l0/src/source_paths.l0`
    - `compiler/stage2_l0/src/util/path.l0`
- Test modules:
    - `compiler/stage1_py/tests/backend/test_stdlib_fs_path_raw_io.py`
    - `compiler/stage2_l0/tests/fs_path_test.l0`
    - `compiler/stage2_l0/tests/byte_array_test.l0`
    - `compiler/stage2_l0/tests/source_paths_test.l0`

## Summary

This plan keeps the landed shared filesystem and path work, but reopens the byte-stdio portion to restore a clearer
safe/unsafe boundary.

`std.fs`, `std.path`, and `RtFileInfo` remain part of the public shared surface. The change in direction is that raw
`byte*` stream entrypoints should not remain exposed through `std.io`. Pointer-based stdin/stdout/stderr operations move
to `sys.unsafe`, while `std.io` is rebuilt on a bounds-checked fixed `ByteArray` abstraction in `std.array`.

The portability model stays the same: public L0 APIs remain portable, platform-specific details remain inside the C
runtime, and richer traversal/process/watch helpers remain deferred.

The pending stdlib boundary cleanup in
`docs/plans/refactors/closed/2026-03-13-stdlib-fs-io-boundary-cleanup-noref.md` is part of the landing criteria for this
feature. The safe byte-stdio surface and the `std.fs` / `std.io` path-helper split must ship together.

## Public Interfaces / Types

1. Shared modules that remain public:
    - `std.fs`
    - `std.path`
2. Shared metadata type that remains public:
   `sys.rt::RtFileInfo { exists: bool; is_file: bool; is_dir: bool; size: int?; mtime_sec: int?; mtime_nsec: int?; }`
3. New shared fixed-size buffer type:
   `std.array::ByteArray { storage: ArrayBase*; }`
4. New `std.array` API:
    - `ba_create(length: int) -> ByteArray*`
    - `ba_capacity(self: ByteArray*) -> int`
    - `ba_get(self: ByteArray*, index: int) -> byte`
    - `ba_set(self: ByteArray*, index: int, value: byte) -> void`
    - `ba_zap(self: ByteArray*, index: int) -> void`
    - `ba_free(self: ByteArray*) -> void`
5. Raw byte stream APIs move to `sys.unsafe` only:
    - `rt_stdin_read(buf: byte*, capacity: int) -> int`
    - `rt_stdout_write(buf: byte*, len: int) -> int`
    - `rt_stderr_write(buf: byte*, len: int) -> int`
6. `std.io` safe byte API becomes:
    - `read_stdin_some(buf: ByteArray*, start: int, count: int) -> int?`
    - `write_stdout_some(buf: ByteArray*, start: int, count: int) -> int?`
    - `write_stderr_some(buf: ByteArray*, start: int, count: int) -> int?`
    - `write_stdout_all(buf: ByteArray*, start: int, count: int) -> Unit?`
    - `write_stderr_all(buf: ByteArray*, start: int, count: int) -> Unit?`

## Detailed Behavior

### 1. Filesystem and path helpers

1. Keep the current `std.fs`, `std.path`, and `RtFileInfo` design.
2. Do not reopen the scope of this plan to add traversal, URI conversion, file watching, or subprocess APIs.
3. Keep the current Stage 2 migration to shared `std.path`, including the narrow `util.path` compatibility shim.

### 2. Unsafe boundary for raw byte stdio

1. Raw stream APIs remain runtime-backed C entrypoints, but their L0 declarations move from `sys.rt` to `sys.unsafe`.
2. `std.io` must not expose any `byte*`-taking stream API after this refactor.
3. The raw transfer contract stays unchanged:
    - positive value: bytes transferred,
    - `0`: EOF for stdin or zero-length transfer,
    - `-1`: error.
4. Keep support for partial transfers at the runtime level.

### 3. `ByteArray`

1. `ByteArray` is fixed-size in this phase. It is not a growable buffer and does not track a logical used-length.
2. Implement `ByteArray` as a byte-specialized wrapper over `ArrayBase`, not as a type alias.
3. `ba_get`, `ba_set`, and `ba_zap` use the existing `std.array` bounds checks.
4. `ByteArray` owns its backing `ArrayBase*` and `ba_free` frees both wrapper and storage.
5. Do not add generic byte conversions, slicing helpers, append APIs, or dynamic byte-buffer behavior in this phase.

### 4. Safe `std.io` byte API

1. `std.io` byte operations accept `ByteArray*` plus explicit `start` and `count`.
2. `std.io` validates ranges with assertion-style programmer-error checks, not nullable runtime-style failures:
    - `start >= 0`
    - `count >= 0`
    - `start <= ba_capacity(buf)`
    - `count <= ba_capacity(buf) - start`
3. `read_stdin_some` returns:
    - positive count on success,
    - `0` on EOF,
    - `null` on I/O error.
4. `write_*_some` return:
    - positive or zero count on success,
    - `null` on I/O error.
5. `write_*_all` loop on `*_some` until all requested bytes are written, and return `null` on I/O error or
   zero-progress write.
6. Zero-length `std.io` operations remain valid.

## Implementation Sequence

1. Add `ByteArray` plus `ba_*` helpers to `std.array`.
2. Move the raw byte stream declarations from `sys.rt` to `sys.unsafe`.
3. Rewrite `std.io` byte operations around `ByteArray` range-checked wrappers.
4. Update Stage 1 and Stage 2 tests to use the safe `std.io` surface and to validate direct unsafe raw access where
   needed.
5. Update the standard-library docs to reflect the new safe/unsafe split and `ByteArray` API.
6. Land the pending `std.fs` / `std.io` path-helper refactor in
   `docs/plans/refactors/closed/2026-03-13-stdlib-fs-io-boundary-cleanup-noref.md` in the same change set.
7. Keep this plan document in sync with the reopened design while the refactor is landing.

## Test Cases and Scenarios

1. Filesystem/path regression:
    - existing `std.fs` and `std.path` behavior still passes unchanged.
2. `ByteArray`:
    - create fixed-size byte array,
    - get/set/zap bytes within bounds,
    - free buffer cleanly.
3. Safe `std.io`:
    - stdin byte read into `ByteArray` handles EOF correctly,
    - stdout/stderr writes through `ByteArray` preserve exact byte sequences, including `\\0`,
    - zero-length reads/writes succeed,
    - partial-write paths are handled by `write_*_all`.
4. Unsafe raw APIs:
    - direct `sys.unsafe` raw byte stream calls still compile and work.
5. Negative/public-surface checks:
    - old `std.io` raw-pointer call sites no longer type-check.

## Documentation Updates

1. Update `docs/reference/standard-library.md` with the new `std.array`, `std.io`, `sys.rt`, and `sys.unsafe` APIs.
2. Do not describe `std.io` as exposing raw `byte*` stream operations after this refactor.
3. Keep the historical Stage 2 milestone references pointing at this reopened plan path.

## Definition of Done

1. `ByteArray`, safe raw byte stdio, shared `std.fs`, and shared `std.path` are all implemented and documented.
2. The `std.fs` / `std.io` boundary cleanup in
   `docs/plans/refactors/closed/2026-03-13-stdlib-fs-io-boundary-cleanup-noref.md` is implemented in the same landing.
3. No raw `byte*` APIs remain public in `std.io`, and no path-based file helpers remain public in `std.io`.
4. Stage 1 and Stage 2 tests cover the final safe/unsafe byte-stdio split and the final `std.fs` filesystem API.

## Assumptions and Defaults

1. The safe public binary-I/O surface should use `ByteArray`, not raw pointers.
2. `sys.unsafe` is the correct public home for pointer-based stream I/O because the caller must supply valid raw
   buffers.
3. A fixed-size buffer is sufficient for this phase; callers track the meaningful byte count separately.
4. L0 does not provide hard field privacy, so `ByteArray` is a safer public abstraction rather than a perfect
   encapsulation barrier.
