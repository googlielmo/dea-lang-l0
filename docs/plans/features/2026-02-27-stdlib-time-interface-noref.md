# Feature Plan

## Add `std.time` wall/monotonic clocks and calendar conversion (`std.time` + `sys.rt` + runtime)

- Date: 2026-02-27
- Status: Implemented (2026-02-27)
- Title: Add one-call time snapshots, UTC/local date breakdown, and monotonic duration helpers
- Kind: Feature
- Severity: Medium (new stdlib surface + runtime FFI additions)
- Stage: Shared stdlib/runtime (affects Stage 1 and Stage 2 users)
- Subsystem: Standard Library and Runtime (`std.time`, `sys.rt`, `l0_runtime.h`)
- Modules:
    - `compiler/shared/l0/stdlib/std/time.l0`
    - `compiler/shared/l0/stdlib/sys/rt.l0`
    - `compiler/shared/runtime/l0_runtime.h`
    - `compiler/stage2_l0/tests/time_test.l0`
    - `compiler/stage1_py/tests/backend/test_time_runtime.py`
    - `docs/reference/standard-library.md`
    - `docs/reference/project-status.md`

## Summary

This change introduces a new `std.time` module and extends runtime FFI for coherent one-call time snapshots:

1. Add `std.time` value types (`WallTime`, `MonotonicTime`, `Duration`, `DateTime`).
2. Add wall/monotonic capture APIs with optional failure returns.
3. Add UTC/local date-time conversion from unix seconds (`sec + nsec`).
4. Add `sys.rt::RtTimeParts` and time externs using out-pointer snapshots.
5. Add runtime implementations for wall/monotonic snapshots and local offset/DST metadata.
6. Add Stage 2 and Stage 1 runtime tests.
7. Update stdlib and project status reference docs.

## Public API Changes

### Added module: `std.time`

1. `struct WallTime { sec: int; nsec: int; }`
2. `struct MonotonicTime { sec: int; nsec: int; }`
3. `struct Duration { sec: int; nsec: int; }`
4. `struct DateTime { year, month, day, hour, minute, second, nanosecond, weekday, yearday, utc_offset_sec, is_dst }`
5. `wall_now() -> WallTime?`
6. `monotonic_supported() -> bool`
7. `monotonic_now() -> MonotonicTime?`
8. `monotonic_diff(start: MonotonicTime, end: MonotonicTime) -> Duration?`
9. `wall_to_utc_datetime(t: WallTime) -> DateTime?`
10. `wall_to_local_datetime(t: WallTime) -> DateTime?`
11. `utc_now_datetime() -> DateTime?`
12. `local_now_datetime() -> DateTime?`

### Added to `sys.rt`

1. `struct RtTimeParts { sec: int; nsec: int; }`
2. `rt_time_unix(out: RtTimeParts*) -> bool`
3. `rt_time_monotonic(out: RtTimeParts*) -> bool`
4. `rt_time_monotonic_supported() -> bool`
5. `rt_time_local_offset_sec(unix_sec: int) -> int?`
6. `rt_time_local_is_dst(unix_sec: int) -> bool?`

## Behavior and Design Decisions

1. Time snapshots use one runtime call per reading to avoid torn sec/nsec pairs.
2. `std.time` wraps snapshot out-pointer calls with `new` plus `with ... cleanup { drop ... }`.
3. Fallible calls return optionals (`null`) instead of panic/sentinel in public APIs.
4. Monotonic unsupported platforms return `false`/`null` (no wall-clock fallback).
5. Calendar conversion uses integer-only UTC civil date math in L0.
6. Local conversion uses runtime-provided UTC offset and DST flag at the source unix second.
7. Nanoseconds are validated and normalized (`0 <= nsec < 1_000_000_000`).

## Verification

Executed:

```bash
./l0c -P compiler/stage2_l0/tests --check time_test
./l0c -P compiler/stage2_l0/tests --run time_test
cd compiler/stage1_py && pytest tests/backend/test_time_runtime.py
```

Observed:

1. Stage 2 time test compiles and runs.
2. Stage 1 backend time runtime tests pass.

## Assumptions and Defaults

1. `int` remains 32-bit; no 64-bit timestamp expansion in this change.
2. No formatting/parsing helper API is added in `std.time` v1.
3. No sleep API is added in `std.time` v1.
4. Leap-second modeling is not introduced (`second` remains `0..59` in conversions).
5. Local offset/DST metadata are delegated to C runtime time facilities.
