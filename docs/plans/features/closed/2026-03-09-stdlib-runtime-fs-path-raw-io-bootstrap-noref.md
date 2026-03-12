# Feature Plan

## Expand shared stdlib/runtime bootstrap APIs for filesystem, path, metadata, and raw byte stdio

- Date: 2026-03-09
- Status: Closed (implemented)
- Title: Add shared stdlib/runtime bootstrap APIs for filesystem helpers, path utilities, file metadata, and raw byte
  stdio
- Kind: Feature
- Severity: High
- Stage: Shared
- Subsystem: Standard library and runtime
- Modules:
    - `compiler/shared/l0/stdlib/std/io.l0`
    - `compiler/shared/l0/stdlib/std/fs.l0`
    - `compiler/shared/l0/stdlib/std/path.l0`
    - `compiler/shared/l0/stdlib/sys/rt.l0`
    - `compiler/shared/runtime/l0_runtime.h`
    - `compiler/stage2_l0/src/source_paths.l0`
    - `compiler/stage2_l0/src/util/path.l0`
- Test modules:
    - `compiler/stage1_py/tests/backend/test_stdlib_fs_path_raw_io.py`
    - `compiler/stage2_l0/tests/fs_path_test.l0`
    - `compiler/stage2_l0/tests/source_paths_test.l0`
    - `compiler/stage2_l0/tests/l0c_stage2_install_prefix_test.sh`

## Summary

Add a first shared-stdlib/runtime expansion phase focused on bootstrap-critical APIs:

- ergonomic filesystem wrappers at the `std.*` layer for primitives already exposed in `sys.rt`,
- a shared `std.path` module promoted from the Stage 2-only `util.path` helpers,
- file metadata/stat support,
- raw byte-oriented stdin/stdout/stderr APIs suitable for `Content-Length` framed LSP traffic.

This phase intentionally does not implement directory traversal, file watching, subprocess spawning, or URI/path
conversion helpers. Those are follow-on phases after the bootstrap-critical surface lands and stabilizes.

The portability model is locked as: public L0 APIs remain portable, while the runtime may use C stdlib where possible
and platform-specific POSIX/Windows shims where strict C99 is insufficient.

## Public Interfaces / Types

1. New shared module: `std.fs`.
2. New shared module: `std.path`.
3. New `sys.rt` struct:
   `RtFileInfo { exists: bool; is_file: bool; is_dir: bool; size: int?; mtime_sec: int?; mtime_nsec: int?; }`
4. New `sys.rt` functions:
    - `rt_file_info(path: string) -> RtFileInfo`
    - `rt_stdin_read(buf: byte*, capacity: int) -> int`
    - `rt_stdout_write(buf: byte*, len: int) -> int`
    - `rt_stderr_write(buf: byte*, len: int) -> int`
5. New `std.io` wrappers:
    - `file_exists(path: string) -> bool`
    - `delete_file(path: string) -> Unit?`
    - `read_stdin_some(buf: byte*, capacity: int) -> int?`
    - `write_stdout_some(buf: byte*, len: int) -> int?`
    - `write_stderr_some(buf: byte*, len: int) -> int?`
    - `write_stdout_all(buf: byte*, len: int) -> Unit?`
    - `write_stderr_all(buf: byte*, len: int) -> Unit?`
6. New `std.fs` wrappers:
    - `stat(path: string) -> FileInfo`
    - `is_file(path: string) -> bool`
    - `is_dir(path: string) -> bool`
    - `file_size(path: string) -> int?`
    - `mtime_sec(path: string) -> int?`
7. New `std.path` API:
    - `is_sep(c: byte) -> bool`
    - `is_absolute(path: string) -> bool`
    - `has_parent(path: string) -> bool`
    - `basename(path: string) -> string`
    - `parent(path: string) -> string`
    - `stem(path: string) -> string`
    - `join(root: string, rel: string) -> string`
    - `has_extension(path: string, ext: string) -> bool`

## Detailed Behavior

### 1. Filesystem and metadata

1. Add `rt_file_info` as the low-level metadata entrypoint instead of separate `sys.rt` calls for each field.
2. `RtFileInfo` must always return `exists`, `is_file`, and `is_dir`.
3. Size and modification time fields are nullable when unavailable or inapplicable.
4. First phase excludes symlink-specific APIs, permission bits, ownership fields, and directory-entry iteration.

### 2. Shared path module

1. Promote the Stage 2 `util.path` logic into shared stdlib as `std.path`.
2. Migrate Stage 2 callers, especially source-path resolution, to the shared module.
3. Preserve current cross-platform separator handling:
    - `/` and `\\` both count as separators,
    - POSIX absolute paths remain supported,
    - Windows drive-rooted absolute paths remain supported.
4. Do not add normalization, canonicalization, or cwd/realpath semantics in this phase.
5. After migration, either remove `compiler/stage2_l0/src/util/path.l0` or keep only a narrow compatibility shim until
   all Stage 2 imports are updated.

**Existing implementation base** (`compiler/stage2_l0/src/util/path.l0`):

| Planned `std.path` API                     | `util.path` function | Lift status                                         |
|--------------------------------------------|----------------------|-----------------------------------------------------|
| `is_sep(c: byte)`                          | `up_is_sep`          | Direct lift                                         |
| `is_absolute(path: string)`                | `up_is_absolute`     | Direct lift                                         |
| `has_parent(path: string)`                 | `up_has_parent`      | Direct lift                                         |
| `basename(path: string)`                   | `up_basename`        | Direct lift                                         |
| `parent(path: string)`                     | `up_parent`          | Direct lift                                         |
| `join(root: string, rel: string)`          | `up_join`            | Direct lift                                         |
| `stem(path: string)`                       | `up_stem`            | Generalize: currently hardcoded to strip `.l0` only |
| `has_extension(path: string, ext: string)` | `up_is_l0_file`      | Generalize: currently `.l0`-only check              |

6 of 8 planned functions are directly liftable. `up_stem` and `up_is_l0_file` need generalization to handle arbitrary
extensions. The helper `up_find_last_sep` is an internal utility that may or may not be promoted to public API.

### 3. Raw byte stdio

1. Raw stream APIs operate on `byte*` plus explicit lengths/counts.
2. Return contract for `sys.rt` byte APIs:
    - positive value: bytes transferred,
    - `0`: EOF for stdin,
    - `-1`: error.
3. The `sys.rt` byte APIs must support partial transfers; they are not all-or-nothing interfaces.
4. `std.io` should provide both `*_some` wrappers and `*_all` convenience functions for callers that need full writes.
5. Higher-level owned-buffer helpers may be layered above this later. Phase 1 should remain compatible with a future
   `CharBuffer`-style abstraction without requiring it now.

### 4. Runtime portability policy

1. Use standard C stream APIs for raw stdin/stdout/stderr where sufficient.
2. Implement file metadata in `l0_runtime.h` behind platform branches:
    - POSIX `stat` on POSIX hosts,
    - Windows filesystem APIs on Windows hosts.
3. Keep platform-specific logic quarantined inside the runtime boundary.
4. Do not constrain this feature to strict pure C99, because robust metadata and later traversal/process/watch APIs are
   not realistically supportable under that constraint alone.

### 5. Explicit deferrals

This phase does not implement:

- directory listing or recursive workspace traversal,
- URI/path conversion helpers,
- file watching,
- subprocess spawning with explicit stdin/stdout/stderr pipe control.

Record those as follow-on work:

1. Phase 2: directory listing and non-recursive traversal.
2. Phase 3: subprocess API with explicit pipe control.
3. Phase 4: file watching.
4. URI/path conversion after `std.path` semantics are stable enough to avoid premature policy lock-in.

## Implementation Sequence

1. Extend `sys.rt` declarations with `RtFileInfo` and raw byte stdio function signatures.
2. Implement the corresponding runtime functions in `l0_runtime.h`.
3. Add `std.path` in shared stdlib by promoting the current Stage 2 `util.path` behavior.
4. Update Stage 2 source-path consumers to import and use `std.path`.
5. Add `std.fs` for metadata wrappers and extend `std.io` with file existence/delete and raw byte I/O helpers.
6. Update standard-library reference docs and project-status docs.
7. Add targeted Stage 1 and Stage 2 tests for the shared runtime/stdlib behavior.

## Test Cases and Scenarios

1. File lifecycle:
    - missing path reports `file_exists == false`,
    - create file, verify `file_exists == true`,
    - delete file, verify removal through wrapper APIs.
2. Metadata:
    - missing file returns `exists == false`,
    - regular file reports `is_file == true`,
    - directory reports `is_dir == true`,
    - file size is populated for a known-size file,
    - modification time fields are either populated or null without crashing.
3. Path utilities:
    - separator recognition for `/` and `\\`,
    - basename/parent/stem behavior with trailing separators,
    - absolute-path detection for POSIX and Windows-drive forms,
    - join behavior with and without trailing root separator.
4. Raw stdio:
    - stdin byte read handles EOF correctly,
    - stdout/stderr byte writes preserve exact byte sequences including `\\0`,
    - partial-write paths are handled by `write_*_all`.
5. Integration:
    - Stage 2 source-path resolution still passes after migration to `std.path`,
    - an LSP-style framed I/O test can read headers/body using byte APIs.

## Documentation Updates

1. Update `docs/reference/standard-library.md` with the new `std.io`, `std.fs`, `std.path`, and `sys.rt` APIs.
2. Update `docs/reference/project-status.md` to list new shared modules.
3. Keep the plan document in sync with the actual landed API surface if naming changes during implementation review.

## Assumptions and Defaults

1. Shared stdlib is the correct home for promoted path helpers, not Stage 2-only utility modules.
2. `byte*` plus explicit lengths is the correct low-level I/O shape for LSP framing and other binary-safe stream use.
3. Rich traversal, process, watch, and URI-conversion APIs are intentionally deferred to keep the first phase small and
   bootstrap-focused.
4. Environment scripts should set only `L0_HOME`; `L0_SYSTEM` and `L0_RUNTIME_INCLUDE` are explicit user overrides and
   compiler defaults must derive stdlib/runtime paths from `L0_HOME` when those overrides are unset.
