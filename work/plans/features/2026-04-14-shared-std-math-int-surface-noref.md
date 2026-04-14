# Feature Plan

## Expand `std.math` with a shared `int` helper surface for L0 and L1

- Date: 2026-04-14
- Status: Draft
- Title: Expand `std.math` with a shared `int` helper surface for L0 and L1
- Kind: Feature
- Scope: Shared
- Severity: Medium
- Stage: Shared
- Targets:
  - `l0` shared `std.math` `int` surface
  - `l1` shared `std.math` `int` surface
- Origin: Shared `std.math` API shape, with the common `int` surface settled once and kept aligned across `l0/` and
  `l1/`
- Porting rule: Keep the shared `int` API, semantics, and regression inventory mechanically aligned between `l0/` and
  `l1/`; L1-only wider integer helpers stay in the dedicated L1 follow-up plan
- Target status:
  - `l0` shared `std.math` `int` surface: Pending
  - `l1` shared `std.math` `int` surface: Pending
- Subsystem: stdlib / docs / tests
- Modules:
  - `l0/compiler/shared/l0/stdlib/std/math.l0`
  - `l0/compiler/shared/l0/stdlib/std/time.l0`
  - `l0/docs/reference/standard-library.md`
  - `l0/docs/reference/design-decisions.md`
  - `l0/docs/reference/project-status.md`
  - `l0/compiler/stage1_py/tests/backend/test_math_runtime.py`
  - `l0/compiler/stage2_l0/tests/math_test.l0`
  - `l1/compiler/shared/l1/stdlib/std/math.l1`
  - `l1/compiler/shared/l1/stdlib/std/time.l1`
  - `l1/docs/reference/standard-library.md`
  - `l1/docs/reference/design-decisions.md`
  - `l1/docs/reference/project-status.md`
  - `l1/compiler/stage1_l0/tests/math_test.l0`
- Test modules:
  - `l0/compiler/stage1_py/tests/backend/test_math_runtime.py`
  - `l0/compiler/stage2_l0/tests/math_test.l0`
  - `l1/compiler/stage1_l0/tests/math_test.l0`
- Related:
  - `l1/work/plans/features/2026-04-14-l1-std-real-module-noref.md`
  - `l1/work/plans/features/2026-04-14-l1-std-math-wide-integer-followup-noref.md`

## Summary

`std.math` is still a one-function module in both L0 and L1, even though both levels already need generic integer helper
logic beyond Euclidean modulo. At the same time, `std.time` currently owns generic signed-32 helper code such as
`int_max`, `int_min`, `floor_div`, and checked add/sub helpers that are not time-specific.

This plan turns `std.math` into the shared home for the common signed-32 helper surface and keeps that surface aligned
across L0 and L1. It intentionally stops at the shared `int` API; the L1-only `uint`, `long`, and `ulong` extension is
tracked separately in `l1/work/plans/features/2026-04-14-l1-std-math-wide-integer-followup-noref.md`.

## Current State

1. `l0/compiler/shared/l0/stdlib/std/math.l0` and `l1/compiler/shared/l1/stdlib/std/math.l1` currently export only
   `emod`.
2. `l0/docs/reference/standard-library.md` and `l1/docs/reference/standard-library.md` list only `emod` under
   `std.math`.
3. `l0/compiler/shared/l0/stdlib/std/time.l0` and `l1/compiler/shared/l1/stdlib/std/time.l1` already define generic
   integer helpers such as `int_max`, `int_min`, `floor_div`, `checked_add_int`, and `checked_sub_int`, which shows the
   current integer-helper ownership is split across modules.
4. The L0 and L1 runtimes already define `int` division, modulo, and overflow behavior at the runtime boundary rather
   than inheriting host-C undefined behavior.
5. There is no dedicated `std.math` regression coverage today in either L0 or L1.

## Scope Split

This shared plan covers only the common `int` (`s32`) surface that belongs in both L0 and L1. It stays root-owned
because the same public API, edge-case policy, docs shape, and regression inventory should land in both levels.

The L1-only typed follow-up is intentionally separate because `_ui`, `_l`, and `_ul` helpers are not a mechanical
downstream port of the shared `int` work.

## Defaults Chosen

1. `std.math` remains integer-focused; floating-point helpers stay in `std.real`, and bit-centric helpers remain out of
   scope.
2. Shared public names remain unsuffixed `int` names; this tranche does not introduce `_i` spellings.
3. Invalid caller preconditions use `assert`, consistent with current stdlib style. That applies to divisor, clamp, and
   alignment validity checks.
4. `div_floor` and `div_ceil` return plain `int`, but their contract must state that the mathematical result must be
   representable. In practice, that excludes the single signed overflow case `int_min() / -1`.
5. `abs`, `gcd`, `lcm`, `pow`, `isqrt`, `align_down`, and `align_up` are checked helpers that return `int?` when domain
   or representability fails.
6. `abs` uses the plain checked name `abs`, not `abs_checked`.
7. Signed `gcd` is checked `int?`, not plain `int`, because cases such as `gcd(int_min(), 0)` have a non-negative
   mathematical result that does not fit in signed 32-bit `int`.
8. `is_aligned` returns plain `bool`; invalid alignment is a precondition failure rather than a nullable result.
9. Existing generic integer helpers in `std.time` should move into `std.math` or delegate to it so `std.time` stops
   owning general-purpose arithmetic utilities.

## Goal

1. Make `std.math` a useful shared integer helper module in both L0 and L1.
2. Standardize the shared `int` surface around quotient variants, bounds helpers, divisibility helpers, alignment
   helpers, and a small checked algorithm set.
3. Consolidate generic signed-32 helper logic under `std.math` instead of leaving it split with `std.time`.
4. Add documentation and dedicated regression coverage so the shared surface is explicit and stable.

## Public API Shape

### Quotient and remainder

- `emod(a: int, b: int) -> int`
- `ediv(a: int, b: int) -> int`
- `div_floor(a: int, b: int) -> int`
- `div_ceil(a: int, b: int) -> int`

### Ordering and bounds

- `min(a: int, b: int) -> int`
- `max(a: int, b: int) -> int`
- `clamp(x: int, lo: int, hi: int) -> int`

### Sign and divisibility

- `sign(x: int) -> int`
- `is_even(x: int) -> bool`
- `is_odd(x: int) -> bool`
- `is_multiple(a: int, b: int) -> bool`

### Checked helpers

- `abs(x: int) -> int?`
- `gcd(a: int, b: int) -> int?`
- `lcm(a: int, b: int) -> int?`
- `pow(base: int, exp: int) -> int?`
- `isqrt(x: int) -> int?`

### Alignment

- `align_down(x: int, align: int) -> int?`
- `align_up(x: int, align: int) -> int?`
- `is_aligned(x: int, align: int) -> bool`

## Implementation Phases

### Phase 1: Establish the shared public surface and consolidate existing helper ownership

1. Expand `std.math` in both levels with the public quotient, ordering, clamp, sign, and divisibility helpers.
2. Factor the current generic `int` support logic out of `std.time` so `floor_div`, bounds helpers, and checked
   add/sub-style support code are no longer owned there directly.
3. Keep the L0 and L1 `std.math` source files mechanically aligned for the shared `int` API and contracts.

### Phase 2: Add the checked algorithm and alignment family

1. Add `abs`, `gcd`, `lcm`, `pow`, `isqrt`, `align_down`, `align_up`, and `is_aligned`.
2. Make the signed-minimum edge cases explicit rather than inheriting runtime traps accidentally.
3. Use nullable returns only where the mathematical domain or representability can fail, not for ordinary caller
   precondition violations.

### Phase 3: Update docs and add regression coverage in both levels

1. Update the L0 and L1 standard-library reference docs with the expanded `std.math` inventory and concise contract
   notes.
2. Update the L0 and L1 design/project-status docs so `std.math` is described as the integer helper module and the
   `std.real` split remains clear.
3. Add dedicated regression coverage for the new surface in L0 Stage 1, L0 Stage 2, and L1 Stage 1.

## Non-Goals

- adding L1-only `_ui`, `_l`, or `_ul` helpers in this shared plan
- introducing floating-point helpers into `std.math`
- adding bit operations such as popcount, clz, ctz, rotates, or power-of-two bit tricks
- adding saturating arithmetic
- changing L0 or L1 language syntax, typing rules, or core operator semantics
- introducing generic numeric overloading

## Verification Criteria

1. `l0/docs/reference/standard-library.md` and `l1/docs/reference/standard-library.md` list the same shared `std.math`
   `int` API with matching signatures and edge-case notes.
2. `std.time` no longer owns the generic shared integer helpers that belong in `std.math`, or any remaining internal
   helper is clearly delegated to the shared math logic rather than duplicated.
3. Dedicated math regression coverage exists in `l0/compiler/stage1_py/tests/backend/test_math_runtime.py`,
   `l0/compiler/stage2_l0/tests/math_test.l0`, and `l1/compiler/stage1_l0/tests/math_test.l0`.
4. Regression coverage includes negative quotient/remainder behavior, signed minimum edge cases, checked-overflow
   optionals, zero/divisor preconditions, and positive/negative alignment cases.
5. The shared L0/L1 `int` surface stays source-aligned; any further typed divergence is confined to the L1 follow-up
   plan.
6. `std.math` remains explicitly integer-focused and does not absorb floating-point or bit-centric helpers in this
   tranche.

## Open Design Constraints

1. Signed helper contracts must stay explicit about representability rather than quietly relying on runtime panics in
   pathological edge cases.
2. The public API should stay small enough to be obviously useful, not turn into an unstructured numeric grab bag.
3. Shared `int` behavior must remain aligned between L0 and L1 even though L1 has wider integer types available
   elsewhere.
4. The feature should reuse the existing stdlib precondition style (`assert` for invalid caller input, `?` for genuine
   domain/representability failure) instead of inventing a second policy for `std.math`.
