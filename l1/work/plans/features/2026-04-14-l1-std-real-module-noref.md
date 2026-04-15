# Feature Plan

## Add `std.real` floating-point standard library module

- Date: 2026-04-14
- Status: Draft
- Title: Add `std.real` floating-point standard library module
- Kind: Feature
- Severity: Medium
- Stage: 1
- Subsystem: Stdlib / runtime / build / docs / tests
- Modules:
  - `compiler/shared/l1/stdlib/std/real.l1`
  - `compiler/shared/l1/stdlib/sys/real.l1`
  - `compiler/shared/runtime/l1_runtime.h`
  - `compiler/shared/runtime/l1_real.h`
  - `compiler/stage1_l0/src/c_emitter.l0`
  - `compiler/stage1_l0/src/build_driver.l0`
  - `compiler/stage1_l0/src/sem_context.l0`
  - `compiler/stage1_l0/tests/c_emitter_test.l0`
  - `compiler/stage1_l0/tests/build_driver_test.l0`
  - `compiler/stage1_l0/tests/l0c_lib_test.l0`
  - `compiler/stage1_l0/tests/fixtures/driver/real_classify_main.l1`
  - `compiler/stage1_l0/tests/fixtures/driver/real_basic_main.l1`
  - `compiler/stage1_l0/tests/fixtures/driver/real_round_main.l1`
  - `compiler/stage1_l0/tests/fixtures/driver/real_decompose_main.l1`
  - `compiler/stage1_l0/tests/fixtures/driver/real_transcendental_main.l1`
  - `docs/reference/standard-library.md`
  - `docs/reference/design-decisions.md`
  - `docs/project-status.md`
- Test modules:
  - `compiler/stage1_l0/tests/c_emitter_test.l0`
  - `compiler/stage1_l0/tests/build_driver_test.l0`
  - `compiler/stage1_l0/tests/l0c_lib_test.l0`
- Related:
  - `l1/work/plans/features/closed/2026-04-04-l1-float-double-literals-noref.md`
  - `l1/work/plans/features/closed/2026-04-13-l1-float-backend-contract-followup-noref.md`
  - `l1/docs/reference/standard-library.md`
  - `l1/docs/reference/design-decisions.md`
  - `l1/docs/reference/c-backend-design.md`
- Repro: `make test-stage1 TESTS="build_driver_test l0c_lib_test"`

## Summary

L1 now has builtin `float` and `double`, real literals, narrow numeric conversion rules, direct C lowering, and an
explicit floating-point backend contract. What it still lacks is a standard library surface for floating-point work
beyond builtin operators.

This plan adds `std.real` as the public floating-point module and `sys.real` as the low-level runtime-binding module. It
keeps L1 syntax, numeric typing rules, and the existing floating-point backend contract unchanged while adding the
runtime boundary, build integration, docs, and Stage 1 coverage needed to make floating-point programming usable in
ordinary L1 code.

It also keeps the extra runtime-header and linker footprint scoped to programs that actually use `sys.real` /
`std.real`, rather than treating every float-using program as a real-helper user by default.

## Dependency

This plan depends on the completed floating-point language work in
`l1/work/plans/features/closed/2026-04-04-l1-float-double-literals-noref.md` and
`l1/work/plans/features/closed/2026-04-13-l1-float-backend-contract-followup-noref.md` landing first. It assumes:

1. builtin `float` and `double` already exist.
2. unsuffixed real literals already mean `double`, with `f` selecting `float`.
3. the current narrow conversion policy is already in force.
4. float-using programs are already constrained by the current L1 floating-point backend contract.

## Current State

1. The standard library is intentionally split into ergonomic `std.*` modules and low-level `sys.*` runtime bindings.
2. `std.math` currently contains only `emod` and remains intentionally integer-focused.
3. The floating-point contract is already defined at the language and backend level, including non-panicking arithmetic,
   defined floating division by zero, signed zero, infinities, NaNs, and target rejection when the floating-point
   contract is not satisfied.
4. The backend already assumes a conservative C99 host toolchain and already includes `math.h` in float-using generated
   C when validating the backend contract.
5. Stage 1 already computes `analysis_uses_floating_point(...)` to gate floating-point contract checks, but that signal
   is broader than "this program uses runtime real helpers".
6. There is no current stdlib surface for floating-point classification, rounding, remainder functions, roots,
   transcendental functions, decomposition helpers, or neighboring-value helpers.
7. Build-driver behavior for host math-library linkage is not yet part of an explicit, regression-covered L1 library
   feature.

## Defaults Chosen

01. The new public module is `std.real`, not `std.float`.
02. The new low-level runtime binding module is `sys.real`, not an expansion of `sys.rt`.
03. `std.math` remains integer-focused in this tranche.
04. This work is library-level only. It adds no syntax, no operators, and no compiler intrinsics.
05. Public APIs use explicit `_f` and `_d` suffixes rather than overloading.
06. The implementation should be thin wrappers over the runtime boundary, not backend special cases.
07. Where a C99 operation naturally returns more than one result, the public `std.real` surface may use small structs
    while `sys.real` uses raw output parameters internally.
08. Prefer factoring the runtime real-helper C surface into a separate `l1_real.h`, with `l1_runtime.h` including it
    only when emitted code actually uses `sys.real`-backed helpers.
09. Prefer reusing or refining the existing floating-point-usage analysis so plain `float` / `double` usage does not
    automatically pull in real-helper headers or linker flags.
10. Programs that use `sys.real` or `std.real` should link the host math library where required by the platform and
    toolchain (`-lm` or equivalent).
11. Existing floating-point typing and conversion rules remain unchanged.
12. This tranche does not expose floating-point environment control, trap flags, or rounding-mode management.

## Goal

1. Add a documented `std.real` module for floating-point library functionality.
2. Add a matching `sys.real` runtime FFI layer.
3. Cover the practical C99 floating-point math surface needed by ordinary L1 programs.
4. Keep the API consistent with the existing L1 floating-point contract rather than delegating behavior to undocumented
   host quirks.
5. Keep runtime-header and linker dependencies scoped to programs that actually use `std.real` / `sys.real`.
6. Add build and runtime validation so the new module works in the normal Stage 1 workflow.

## Public API Shape

### Public module: `std.real`

The public module should expose separate `float` and `double` entry points with explicit suffixes. Phase 1 only needs
the minimum useful subset; later phases fill out the broader agreed surface.

- Classification: `is_nan_f`, `is_nan_d`, `is_inf_f`, `is_inf_d`, `is_finite_f`, `is_finite_d`, `signbit_f`,
  `signbit_d`.
- Basic ops: `abs_f`, `abs_d`, `sqrt_f`, `sqrt_d`, `cbrt_f`, `cbrt_d`, `hypot_f`, `hypot_d`.
- Exponential and logarithmic: `exp_f`, `exp_d`, `exp2_f`, `exp2_d`, `log_f`, `log_d`, `log10_f`, `log10_d`, `log2_f`,
  `log2_d`, `pow_f`, `pow_d`.
- Trigonometric: `sin_f`, `sin_d`, `cos_f`, `cos_d`, `tan_f`, `tan_d`, `asin_f`, `asin_d`, `acos_f`, `acos_d`, `atan_f`,
  `atan_d`, `atan2_f`, `atan2_d`.
- Rounding: `floor_f`, `floor_d`, `ceil_f`, `ceil_d`, `trunc_f`, `trunc_d`, `round_f`, `round_d`.
- Remainder and decomposition: `fmod_f`, `fmod_d`, `remainder_f`, `remainder_d`, `modf_f`, `modf_d`, `frexp_f`,
  `frexp_d`, `ldexp_f`, `ldexp_d`.
- Sign and neighboring-value helpers: `copy_sign_f`, `copy_sign_d`, `next_after_f`, `next_after_d`.

### Low-level module: `sys.real`

`sys.real` should declare the corresponding runtime-backed `extern func` surface using explicit `rt_real_*` names. The
public `std.real` layer should absorb any wrapper-only shaping such as small return structs, while `sys.real` remains a
thin and C-oriented binding layer. Using `sys.real` should also be the trigger for any extra runtime-header inclusion
and host math-library linkage that the platform requires.

### Multi-result public types

Where the public API benefits from value-returning wrappers, define explicit structs in `std.real`, for example:

- `FracPartsF { int_part: float; frac_part: float; }`
- `FracPartsD { int_part: double; frac_part: double; }`
- `FrexpPartsF { significand: float; exp: int; }`
- `FrexpPartsD { significand: double; exp: int; }`

This keeps the public surface idiomatic for L1 while leaving `sys.real` free to use output-pointer FFI where that maps
naturally to C.

## Implementation Phases

### Phase 1: Establish `std.real` and the minimum usable runtime-backed surface

This phase creates the actual module boundary and makes the feature real rather than aspirational.

Work in this phase:

1. Add `compiler/shared/l1/stdlib/sys/real.l1` with the low-level `extern func` declarations.
2. Add `compiler/shared/l1/stdlib/std/real.l1` as the public wrapper module.
3. Add runtime real-helper wrappers in `compiler/shared/runtime/l1_real.h`, with `compiler/shared/runtime/l1_runtime.h`
   remaining the umbrella runtime header, for:
   - classification: `is_nan_*`, `is_inf_*`, `is_finite_*`, `signbit_*`
   - basic ops: `abs_*`, `sqrt_*`, `cbrt_*`, `hypot_*`
   - rounding: `floor_*`, `ceil_*`, `trunc_*`, `round_*`
   - remainder and decomposition: `fmod_*`, `remainder_*`, `modf_*`, `frexp_*`, `ldexp_*`
   - sign and neighboring-value helpers: `copy_sign_*`, `next_after_*`
4. Reuse or refine the existing floating-point-usage analysis so emitted code only pulls in `l1_real.h` when it actually
   needs `sys.real`-backed helpers, rather than when it merely uses builtin floating-point types.
5. Add the small public wrapper structs needed for `modf_*` and `frexp_*`.
6. Update `build_driver.l0` so programs that use `sys.real` or `std.real` link the host math library where required
   (`-lm` or equivalent), without broadening that dependency to unrelated float-only programs.
7. Update `docs/reference/standard-library.md`, `docs/reference/design-decisions.md`, and `docs/project-status.md` so
   `std.real` and `sys.real` are part of the documented L1 reference set.
8. Add Stage 1 build and smoke coverage for representative finite, infinite, NaN, and signed-zero cases, including the
   intended include/link trigger behavior.

### Phase 2: Expand `std.real` to the broader C99 floating-point math surface and lock the API

This phase fills out the module so it covers the broader floating-point math families expected from a serious standard
library surface.

Work in this phase:

1. Add the exponential and logarithmic family: `exp_*`, `exp2_*`, `log_*`, `log10_*`, `log2_*`, `pow_*`.
2. Add the trigonometric family: `sin_*`, `cos_*`, `tan_*`, `asin_*`, `acos_*`, `atan_*`, `atan2_*`.
3. Review whether any additional C99 helpers belong in this tranche and admit them only if their behavior can be stated
   clearly under the current L1 floating-point contract.
4. Expand `docs/reference/standard-library.md` with a complete `std.real` / `sys.real` inventory and concise behavior
   notes.
5. Update `docs/reference/design-decisions.md` and `docs/project-status.md` so the floating-point library surface is
   reflected in the reference set.
6. Add broader CLI smoke coverage and regression tests across ordinary values, non-finite values, and edge cases that
   matter to the documented contract.
7. Verify that no `std.real` API silently broadens implicit numeric conversions or smuggles floating-environment
   semantics into the language contract.

## Non-Goals

- changing L1 syntax, grammar, or operators
- changing the existing `float` / `double` typing rules
- adding numeric overloading or generic numeric abstractions
- renaming `std.math` into a mixed integer/real umbrella
- exposing floating exception flags, trap control, or rounding-mode APIs
- adding complex numbers
- adding decimal floating-point
- adding compiler intrinsics for math functions
- changing the current backend floating-point contract

## Verification Criteria

1. `l1/docs/reference/standard-library.md` documents both `std.real` and `sys.real`.
2. `l1/docs/reference/design-decisions.md` records the naming and layering decisions for the floating-point library
   surface.
3. `make -C l1 test-stage1 TESTS="c_emitter_test build_driver_test"` passes with coverage that `l1_real.h` inclusion and
   host math-library linkage are triggered for `sys.real` / `std.real` usage, not for unrelated float-only programs.
4. `make -C l1 test-stage1 TESTS="l0c_lib_test"` passes with smoke programs covering classification, roots, rounding,
   remainder, decomposition, and transcendental operations.
5. The public API remains explicit between `float` and `double`; no implicit library-level overloading is introduced.
6. The new stdlib surface remains consistent with the existing L1 floating-point contract on supported targets.
7. The runtime boundary, not ad hoc backend rewrites, owns the host-specific C99 math calls.

## Open Design Constraints

1. This plan must remain L1-local and belong under `l1/work/plans/features/`.
2. The current narrow floating-point typing rules must remain unchanged in this feature.
3. The runtime boundary must continue to own host-specific behavior, with real helpers factored into a separate
   `l1_real.h` if that can be done cleanly.
4. Existing floating-point-usage analysis may be reused or refined, but the plan should avoid treating every float-using
   program as a `sys.real` user.
5. The public naming scheme must stay simple, explicit, and bootstrap-friendly.
6. Functions whose behavior cannot be documented cleanly under the current L1 floating-point contract should be deferred
   rather than admitted vaguely.
7. The build path must remain explicit about platform-specific math-library linkage requirements and scope that linkage
   to `sys.real` / `std.real` usage.

## Future Surface, Deferred

The following are explicitly deferred unless a later pass justifies them with a clear contract:

- `erf_*`, `erfc_*`
- `tgamma_*`, `lgamma_*`
- `ilogb_*`, `logb_*`
- `scalbn_*`, `scalbln_*`
- `nearbyint_*`, `rint_*`, `lrint_*`, `llrint_*`
- `lround_*`, `llround_*`
- `fdim_*`, `fma_*`, `remquo_*`

These are not rejected permanently. They are outside the smallest coherent plan that can add a solid `std.real` module
without dragging floating-environment policy into Stage 1 by accident.
