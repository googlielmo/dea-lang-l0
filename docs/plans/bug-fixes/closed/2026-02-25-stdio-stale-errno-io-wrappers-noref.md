# Bug Fix Plan

## Stale `errno` causing false failures in `std.io` wrappers

- Date: 2026-02-25
- Status: Closed (fixed)
- Title: Remove stale-`errno` gating from `std.io` success/failure classification
- Kind: Bug Fix
- Severity: High (valid I/O paths could fail after unrelated syscalls)
- Stage: Shared stdlib (affects Stage 1 and Stage 2)
- Subsystem: Standard Library I/O
- Modules: `compiler/shared/l0/stdlib/std/io.l0`
- Repro:
  - Stage 1 runtime regression: `test_std_io_stale_errno_does_not_cause_false_failures`
  - Stage 2 regression: `compiler/stage2_l0/tests/io_errno_test.l0`

## Summary

`std.io` wrapper functions previously treated `rt_errno() != 0` as a hard failure signal in addition to direct runtime
return values. Since `errno` is process-global and can remain stale from earlier unrelated failures, valid I/O
operations could be misclassified as failures.

This affected `read_file`, `write_file`, `read_line`, `read_char`, and `read_char_or_eof`.

## Root Cause

In `compiler/shared/l0/stdlib/std/io.l0`, wrapper conditionals used:

- direct return-value checks (optional null, bool false, `-1` sentinel), and
- an additional `rt_errno() != 0` gate.

Runtime helpers in `l0_runtime.h` do not guarantee errno reset on every successful call path, so the extra gate could
observe stale values and produce false negatives.

## Scope of This Fix

1. Remove `rt_errno()` gating from all affected `std.io` wrappers.
2. Keep wrapper APIs and signatures unchanged.
3. Preserve behavior based on runtime return values only.
4. Add regressions in both Stage 1 and Stage 2 test suites.
5. Update reference documentation for `std.io` behavior.

## Approach

### A. Patch `std.io` wrappers

File: `compiler/shared/l0/stdlib/std/io.l0`

- `read_file`: fail only when `rt_read_file_all(path)` returns null.
- `write_file`: fail only when `rt_write_file_all(path, data)` returns false.
- `read_line`: fail only when `rt_read_line()` returns null.
- `read_char`: fail only when `rt_read_char()` returns `-1`.
- `read_char_or_eof`: return raw `rt_read_char()` sentinel semantics.

### B. Stage 1 regression

File: `compiler/stage1_py/tests/backend/test_string_runtime.py`

Add `test_std_io_stale_errno_does_not_cause_false_failures`:

1. Seed stale errno by probing a guaranteed-missing file via `sys.rt::rt_file_exists`.
2. Call `write_file` on a valid path and require non-null success.
3. Call `read_file` on that path and require non-null + exact content.
4. Assert program output marker `ok`.

### C. Stage 2 regression

File: `compiler/stage2_l0/tests/io_errno_test.l0`

- Same stale-errno setup + write/read assertions via `std.assert`.
- Cleanup created file with `rt_delete_file`.
- Emit pass marker: `io_errno_test: all tests passed`.

### D. Documentation update

File: `docs/reference/standard-library.md`

- Add note in `std.io` section: wrappers classify success/failure from direct runtime return semantics.

## Verification

```bash
cd compiler/stage1_py
../../.venv/bin/pytest -q tests/backend/test_string_runtime.py -k "stale_errno or string_search_helpers_runtime or string_byte_conversions_runtime"

./l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/io_errno_test.l0
./compiler/stage2_l0/run_tests.sh
```

Optional trace gate (shared-stdlib impact):

```bash
./compiler/stage2_l0/run_trace_tests.sh
```

## Assumptions

- Runtime return values are the authoritative error/success channel for these wrappers.
- `errno` remains process-global and may be stale between independent operations.
- No ABI or signature changes are required.
