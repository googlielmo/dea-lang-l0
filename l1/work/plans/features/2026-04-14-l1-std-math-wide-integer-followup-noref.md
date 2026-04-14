# Feature Plan

## Extend `std.math` with L1-only `uint`, `long`, and `ulong` helpers

- Date: 2026-04-14
- Status: Draft
- Title: Extend `std.math` with L1-only `uint`, `long`, and `ulong` helpers
- Kind: Feature
- Severity: Medium
- Stage: 1
- Subsystem: Stdlib / docs / tests
- Modules:
  - `compiler/shared/l1/stdlib/std/math.l1`
  - `compiler/stage1_l0/tests/math_test.l0`
  - `docs/reference/standard-library.md`
  - `docs/reference/design-decisions.md`
  - `docs/reference/project-status.md`
- Test modules:
  - `compiler/stage1_l0/tests/math_test.l0`
- Related:
  - `work/plans/features/closed/2026-04-14-shared-std-math-int-surface-noref.md`
  - `l1/work/plans/features/closed/2026-04-13-l1-uint-long-ulong-bigint-builtins-noref.md`
  - `l1/work/plans/features/2026-04-14-l1-std-real-module-noref.md`

## Summary

L1 already has implemented `uint`, `long`, and `ulong` builtin types plus checked runtime behavior for their arithmetic,
division, modulo, and casts, but `std.math` still exposes only the shared `emod` helper copied from the common surface.

This follow-up builds on the shared `int` plan by adding a typed L1-only `std.math` layer for the extra integer widths
that exist only in L1. It keeps the shared unsuffixed `int` API untouched, gives `uint` a direct 32-bit surface rather
than forcing callers through `ulong`, mirrors the signed shared surface for `long`, and keeps `ulong` deliberately
selective.

## Dependency

This plan depends on the shared `int` surface in
`work/plans/features/closed/2026-04-14-shared-std-math-int-surface-noref.md` settling first. The shared plan owns the
common module identity, precondition style, and signed-helper policy; this L1-local follow-up should extend that settled
shape rather than redefining it.

It also depends on the completed integer builtin work in
`l1/work/plans/features/closed/2026-04-13-l1-uint-long-ulong-bigint-builtins-noref.md`, which already made `uint`,
`long`, and `ulong` real L1 builtin types.

## Current State

1. `compiler/shared/l1/stdlib/std/math.l1` currently exports only `emod`.
2. L1 already implements `uint`, `long`, and `ulong` builtin types with fixed-width semantics documented in
   `l1/docs/reference/design-decisions.md`.
3. `compiler/shared/runtime/l1_runtime.h` already provides checked arithmetic, division, modulo, and cast helpers for
   `int`, `uint`, `long`, and `ulong`.
4. L1 currently has no public typed `std.math` helper surface for `uint`, `long`, or `ulong`.
5. There is no dedicated regression coverage today for wide-integer stdlib math helpers in L1.

## Defaults Chosen

1. The shared unsuffixed names remain reserved for `int`; L1-only typed variants use `_ui`, `_l`, and `_ul`.
2. `uint` gets a direct 32-bit helper family; callers should not be forced to widen to `ulong` for ordinary library
   math.
3. `long` mirrors the shared signed surface where the semantics still make sense.
4. `ulong` stays selective and unsigned-specific; this tranche does not add `sign_ul`, `abs_ul`, or signed-style
   `ediv_ul` / `emod_ul` spellings.
5. Unsigned quotient helpers use plain `div_*` / `mod_*` names because Euclidean and ordinary unsigned division
   coincide.
6. Invalid caller preconditions use `assert`, matching the shared `std.math` style. Checked nullable returns are used
   only where domain or representability can fail.
7. `div_ceil_ui`, `div_ceil_ul`, `isqrt_ui`, `isqrt_ul`, `align_down_ui`, `align_down_ul`, `is_aligned_ui`,
   `is_aligned_ul`, `gcd_ui`, and `gcd_ul` stay total and return plain values.
8. Signed `long` checked helpers follow the shared signed policy: `abs_l`, `gcd_l`, `lcm_l`, `pow_l`, `isqrt_l`,
   `align_down_l`, and `align_up_l` return `long?` where required.
9. Saturating arithmetic remains deferred.

## Goal

1. Add an L1-only typed `std.math` surface for `uint`, `long`, and `ulong`.
2. Keep the naming explicit and boring so the shared `int` surface stays ergonomic and the L1-only extension stays
   unambiguous.
3. Reuse the already implemented fixed-width integer semantics in L1 rather than inventing a second integer policy in
   the stdlib.
4. Add documentation and regression coverage for the wider integer helper families.

## Public API Shape

### `uint` (`u32`)

- `div_ui(a: uint, b: uint) -> uint`
- `mod_ui(a: uint, b: uint) -> uint`
- `div_ceil_ui(a: uint, b: uint) -> uint`
- `min_ui(a: uint, b: uint) -> uint`
- `max_ui(a: uint, b: uint) -> uint`
- `clamp_ui(x: uint, lo: uint, hi: uint) -> uint`
- `is_even_ui(x: uint) -> bool`
- `is_odd_ui(x: uint) -> bool`
- `is_multiple_ui(a: uint, b: uint) -> bool`
- `gcd_ui(a: uint, b: uint) -> uint`
- `lcm_ui(a: uint, b: uint) -> uint?`
- `pow_ui(base: uint, exp: int) -> uint?`
- `isqrt_ui(x: uint) -> uint`
- `align_down_ui(x: uint, align: uint) -> uint`
- `align_up_ui(x: uint, align: uint) -> uint?`
- `is_aligned_ui(x: uint, align: uint) -> bool`

### `long` (`s64`)

- `emod_l(a: long, b: long) -> long`
- `ediv_l(a: long, b: long) -> long`
- `div_floor_l(a: long, b: long) -> long`
- `div_ceil_l(a: long, b: long) -> long`
- `min_l(a: long, b: long) -> long`
- `max_l(a: long, b: long) -> long`
- `clamp_l(x: long, lo: long, hi: long) -> long`
- `sign_l(x: long) -> int`
- `is_even_l(x: long) -> bool`
- `is_odd_l(x: long) -> bool`
- `is_multiple_l(a: long, b: long) -> bool`
- `abs_l(x: long) -> long?`
- `gcd_l(a: long, b: long) -> long?`
- `lcm_l(a: long, b: long) -> long?`
- `pow_l(base: long, exp: int) -> long?`
- `isqrt_l(x: long) -> long?`
- `align_down_l(x: long, align: long) -> long?`
- `align_up_l(x: long, align: long) -> long?`
- `is_aligned_l(x: long, align: long) -> bool`

### `ulong` (`u64`)

- `div_ul(a: ulong, b: ulong) -> ulong`
- `mod_ul(a: ulong, b: ulong) -> ulong`
- `div_ceil_ul(a: ulong, b: ulong) -> ulong`
- `min_ul(a: ulong, b: ulong) -> ulong`
- `max_ul(a: ulong, b: ulong) -> ulong`
- `clamp_ul(x: ulong, lo: ulong, hi: ulong) -> ulong`
- `is_even_ul(x: ulong) -> bool`
- `is_odd_ul(x: ulong) -> bool`
- `is_multiple_ul(a: ulong, b: ulong) -> bool`
- `gcd_ul(a: ulong, b: ulong) -> ulong`
- `lcm_ul(a: ulong, b: ulong) -> ulong?`
- `pow_ul(base: ulong, exp: int) -> ulong?`
- `isqrt_ul(x: ulong) -> ulong`
- `align_down_ul(x: ulong, align: ulong) -> ulong`
- `align_up_ul(x: ulong, align: ulong) -> ulong?`
- `is_aligned_ul(x: ulong, align: ulong) -> bool`

## Implementation Phases

### Phase 1: Add the signed `long` mirror of the shared surface

1. Add the `_l` quotient, ordering, sign, divisibility, checked algorithm, and alignment helpers.
2. Keep the signed contracts aligned with the shared `int` policy, including the minimum-signed-value representability
   cases.
3. Reuse the shared naming and precondition style instead of creating an L1-only exception.

### Phase 2: Add direct unsigned `uint` and selective `ulong` families

1. Add the direct `uint` helper family with explicit `_ui` suffixes.
2. Add the selective `ulong` family with `_ul` suffixes and plain unsigned division naming.
3. Keep unsigned helpers total where the result is always representable, and reserve nullable returns for multiplicative
   overflow or alignment-round-up overflow.

### Phase 3: Update docs and add wide-integer regression coverage

1. Update `l1/docs/reference/standard-library.md` with the full `_ui`, `_l`, and `_ul` inventory and concise contract
   notes.
2. Update `l1/docs/reference/design-decisions.md` and `l1/docs/reference/project-status.md` so the L1-only wide-integer
   `std.math` extension is documented as part of the current fixed-width integer story.
3. Add dedicated tests covering zero, one, min/max, signed minimum, and rounding/alignment edges across the three typed
   families.

## Non-Goals

- changing the shared unsuffixed `int` API from the root plan
- adding `_i` spellings for `int`
- widening ordinary `uint` library calls through `ulong`
- adding floating-point helpers
- adding bit operations or number-theory extras beyond `gcd`, `lcm`, and integer square root
- adding saturating arithmetic
- changing L1 syntax, literal syntax, cast rules, or operator semantics

## Verification Criteria

1. `l1/docs/reference/standard-library.md` documents the `_ui`, `_l`, and `_ul` helpers separately from the shared
   unsuffixed `int` surface.
2. L1 regression coverage exists in `compiler/stage1_l0/tests/math_test.l0` for representative `uint`, `long`, and
   `ulong` cases.
3. Regression coverage includes boundary-value behavior for `0`, `1`, typed maxima, signed minima, checked overflow
   optionals, and alignment/division edge cases.
4. Unsigned helpers use the plain `div_*` / `mod_*` naming scheme and do not inherit signed-only terminology.
5. Signed `long` helpers follow the same checked-edge policy as the shared `int` surface rather than quietly diverging
   in the L1-only layer.
6. The L1-only extension does not change or shadow the shared unsuffixed `int` API.

## Open Design Constraints

1. This plan must stay L1-local because the `uint`, `long`, and `ulong` surfaces do not exist in L0.
2. The follow-up should extend the shared `std.math` identity, not reopen it.
3. Signed `long` helpers must stay explicit about the `LONG_MIN` representability edge cases.
4. Unsigned helpers should stay selective and avoid importing meaningless signed-only concepts.
5. The wider typed families must not blur the existing split between integer helpers in `std.math` and floating-point
   helpers in `std.real`.
