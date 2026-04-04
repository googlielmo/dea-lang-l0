# Refactor Plan

## Collapse path-based file helpers into `std.fs` and remove redundant `rt_file_exists`

- Date: 2026-03-13
- Status: Closed (implemented)
- Title: Move path-based file helpers out of `std.io`, add `std.fs::exists`, and remove redundant `rt_file_exists`
- Kind: Refactor
- Severity: Medium (public stdlib API cleanup and in-tree call-site migration)
- Stage: Shared
- Subsystem: Standard Library + Runtime
- Modules:
  - `compiler/shared/l0/stdlib/std/fs.l0`
  - `compiler/shared/l0/stdlib/std/io.l0`
  - `compiler/shared/l0/stdlib/sys/rt.l0`
  - `compiler/shared/runtime/l0_runtime.h`
  - `compiler/stage2_l0/src/{build_driver.l0,diag_print.l0,driver.l0,l0c_lib.l0}`
  - `docs/reference/standard-library.md`
- Test modules:
  - `compiler/stage1_py/tests/backend/test_stdlib_fs_path_raw_io.py`
  - `compiler/stage1_py/tests/backend/test_string_runtime.py`
  - `compiler/stage2_l0/tests/fs_path_test.l0`
  - `compiler/stage2_l0/tests/io_errno_test.l0`
  - `compiler/stage2_l0/tests/l0c_lib_test.l0`

## Summary

Refactor the shared stdlib so all path-based filesystem operations live in `std.fs`, while `std.io` is reserved for
standard streams, byte-stream helpers, flushing, and printing.

As part of the cleanup, replace `std.io::file_exists` with a generic `std.fs::exists(path)` helper and remove the
redundant runtime fast-path `rt_file_exists`. Generic existence should derive from file metadata (`rt_file_info` /
`stat`) instead of a separate runtime extern.

## Public API and Type Interface

1. `std.fs` final surface for path-based file operations:
   - `exists(path: string) -> bool`
   - `stat(path: string) -> FileInfo`
   - `is_file(path: string) -> bool`
   - `is_dir(path: string) -> bool`
   - `file_size(path: string) -> int?`
   - `mtime_sec(path: string) -> int?`
   - `delete_file(path: string) -> Unit?`
   - `read_file(path: string) -> string?`
   - `write_file(path: string, data: string) -> Unit?`
2. `std.io` drops all path-based file helpers:
   - remove `file_exists`
   - remove `delete_file`
   - remove `read_file`
   - remove `write_file`
3. `sys.rt` drops:
   - `rt_file_exists(path: string) -> bool`
4. No new runtime externs are added.
   - `std.fs::exists` is implemented from `rt_file_info(path).exists` or the existing `stat(path).exists` wrapper.
   - `delete_file`, `read_file`, and `write_file` continue to use `rt_delete_file`, `rt_read_file_all`, and
     `rt_write_file_all`.

## Implementation Sequence

1. Extend `std.fs` with `exists(path)` and move the existing `delete_file`, `read_file`, and `write_file` wrappers
   there.
2. Update `std.fs` imports as needed so moved functions keep their current nullable return contracts.
3. Hard-cut all in-tree callers from `std.io` file helpers to `std.fs`.
   - Use `exists(path)` for generic existence checks.
   - Keep `is_file(path)` only where regular-file semantics are intended.
4. Remove the obsolete path-based helpers from `std.io` so the module is stream-only.
5. Remove `rt_file_exists` from `sys.rt` and from `compiler/shared/runtime/l0_runtime.h`.
6. Update `docs/reference/standard-library.md` so the module split and FFI inventory match the refactor.

## Test Cases and Scenarios

1. `std.fs::exists` returns:
   - `false` for a missing path,
   - `true` for a regular file,
   - `true` for a directory.
2. File lifecycle coverage continues to pass through `std.fs` only:
   - create with `write_file`,
   - read with `read_file`,
   - inspect with `stat`, `file_size`, `mtime_sec`,
   - remove with `delete_file`.
3. Stage 2 driver and CLI-support flows keep working after import migration:
   - temp-file probing in `build_driver`
   - source loading in `driver` / `l0c_lib`
   - diagnostic source reads in `diag_print`
4. Negative/public-surface regressions:
   - old `std.io::{file_exists, delete_file, read_file, write_file}` references no longer resolve,
   - `sys.rt::rt_file_exists` no longer resolves.
5. Docs/runtime inventory checks:
   - no `rt_file_exists` declaration remains in `sys.rt` docs or headers,
   - `std.io` documentation no longer advertises path-based file helpers.

## Assumptions and Defaults

1. This is a clean break, not a deprecation phase. No forwarding aliases remain in `std.io`.
2. `exists(path)` means generic path existence, not “regular file exists”.
3. `delete_file(path)` keeps its current `Unit?` contract and still fails on runtime removal errors.
4. This refactor changes module ownership and removes redundant API surface; it does not expand filesystem capabilities
   beyond the new `exists` helper.
