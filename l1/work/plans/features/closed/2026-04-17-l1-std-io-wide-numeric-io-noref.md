# Feature Plan

## Extend `std.io` with wide numeric I/O helpers

- Date: 2026-04-17
- Status: Completed
- Title: Extend `std.io` with wide numeric I/O helpers
- Kind: Feature
- Severity: Medium
- Stage: 1
- Subsystem: Stdlib / runtime / docs / tests
- Modules:
  - `compiler/shared/l1/stdlib/std/io.l1`
  - `compiler/shared/l1/stdlib/std/text.l1`
  - `compiler/shared/l1/stdlib/sys/rt.l1`
  - `compiler/shared/runtime/l1_runtime.h`
  - `compiler/stage1_l0/tests/io_runtime_test.py`
  - `compiler/stage1_l0/tests/fixtures/io_runtime/io_numeric_main.l1`
  - `docs/reference/standard-library.md`
  - `docs/reference/design-decisions.md`
  - `docs/project-status.md`
- Test modules:
  - `compiler/stage1_l0/tests/io_runtime_test.py`
- Related:
  - `l1/work/plans/features/closed/2026-04-13-l1-uint-long-ulong-bigint-builtins-noref.md`
  - `l1/work/plans/features/closed/2026-04-14-l1-std-math-wide-integer-followup-noref.md`
  - `l1/work/plans/features/closed/2026-04-14-l1-std-real-module-noref.md`
- Repro:
  - `make test-stage1 TESTS="util_text_test io_runtime_test.py"`
  - `make test-stage1`

## Summary

L1 already has implemented `uint`, `long`, `ulong`, `float`, and `double` builtin types, but `std.io` only exposed
string, `int`, and `bool` print helpers. This feature extends the standard I/O surface with typed one-value output
helpers for the wider numeric family and adds token-based integer reads that reuse shared string parsers.

The feature deliberately does not add `read_f` or `read_d`. Floating-point reads need a separate parsing contract and
should not be coupled to this integer-token and output-focused tranche.

## Outcome

1. `std.io` now exposes `_ui`, `_l`, `_ul`, `_f`, and `_d` stdout/stderr print and print-line helpers.
2. `std.io` now exposes `read_delim`, `read_delim_any`, `read_delim_ws`, `read_i`, `read_ui`, `read_l`, and `read_ul`.
3. `std.text` now exposes format and parse helpers for `uint`, `long`, and `ulong`.
4. `sys.rt` and `l1_runtime.h` now provide the runtime print boundary for `uint`, `long`, `ulong`, `float`, and
   `double`.
5. Focused runtime and text conversion coverage plus the live L1 stdlib docs were updated together.

## Defaults Chosen

1. `uint` uses `_ui`, matching the existing L1 `std.math` suffix policy.
2. `long`, `ulong`, `float`, and `double` use `_l`, `_ul`, `_f`, and `_d`.
3. Pair-print helper expansion is out of scope; labels can be composed with `print_s` and the typed one-value helpers.
4. Typed integer reads use whitespace-token extraction plus `std.text` parsing.
5. `read_delim` and `read_delim_any` consume and exclude the delimiter; EOF before any byte returns `null`, while EOF
   after bytes returns the accumulated string.
6. `read_delim_ws` skips leading ASCII whitespace and returns `null` only when EOF appears before a token.
7. Wide integer parsers accept bases `2..16`, allow leading zeros, reject `+`, reject prefixes such as `0x`, and return
   `null` on invalid input or out-of-range values.
8. Floating-point parsing remains deferred.

## Verification Criteria

1. `std.io` documents and exposes stdout/stderr helpers for `uint`, `long`, `ulong`, `float`, and `double`.
2. `std.io` documents and exposes delimiter-token reads plus typed integer reads.
3. `std.text` documents and exposes `uint`, `long`, and `ulong` format/parse helpers.
4. Runtime coverage verifies delimiter behavior, typed integer reads, stdout numeric output, and stderr numeric output.
5. Text coverage verifies wide integer min/max, base formatting/parsing, invalid input, unsigned negative rejection, and
   overflow/underflow.
6. The feature does not add `read_f`, `read_d`, or floating-point string parsers.
