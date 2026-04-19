# Feature Plan

## Support non-constant initializers for top-level let declarations

- Date: 2026-04-17
- Status: Completed
- Title: Support non-constant initializers for top-level let declarations
- Kind: Feature
- Severity: Medium
- Stage: L1
- Subsystem: Backend / initialization / C emitter
- Modules:
  - `l1/compiler/stage1_l0/src/backend.l0`
  - `l1/compiler/stage1_l0/src/c_emitter.l0`
  - `l1/compiler/stage1_l0/tests/fixtures/driver/`
  - `l1/compiler/shared/l1/stdlib/std/real.l1`
- Test modules:
  - `l1/compiler/stage1_l0/tests/l0c_lib_test.l0`
- Related:
  - `l1/work/plans/features/closed/2026-04-14-l1-std-real-module-noref.md`
- Repro: `make -C l1 test-stage1 TESTS="c_emitter_test backend_test l0c_lib_test" && make -C l1 test-stage1`

## Summary

Currently, top-level `let` declarations in L1 only support constant initializers (like integer literals, float literals,
or specific constant constructors). This limitation prevents module-level constants from being initialized using
function calls or complex expressions, forcing workarounds such as exposing values through getter functions (e.g.,
`nan_f()` instead of a `NAN_F` constant).

This plan extends the compiler to support non-constant initializers for top-level `let` declarations. This involves
emitting a module-level initialization step that runs before the program's `main` function to execute these complex
initializers.

## Completion Notes

1. `backend.l0` and `c_emitter.l0` now split top-level bindings between direct C storage initializers and deferred
   module-init assignments, using hidden `_dea_init_<module>()` helpers plus a global `_dea_init_modules()` chain.
2. Deferred initialization order now follows the module dependency graph and import source order, and the generated C
   `main` wrapper runs the init chain before dispatching to user `main`.
3. `std.real` now exposes `NAN_F`, `NAN`, `INFINITY_F`, and `INFINITY` as module-level `let` constants backed by the
   existing `sys.real` runtime helpers.
4. Regression coverage now includes backend/emitter expectations and kept-C/runtime fixtures proving deferred top-level
   initialization works across imported modules, including imported floating-point runtime calls.

## Current State

1. Top-level `let` declarations are evaluated in `backend.l0` using `be_emit_let_initializer`.
2. If the initializer is a complex expression like a function call, the backend aborts with
   `[ICE-1034] call expression is not a supported constant constructor`.
3. The `std.real` module had to use `func nan_f() -> float` instead of `let NAN_F: float = rt_real_get_nan_f()` due to
   this restriction.

## Goal

1. Allow top-level `let` declarations to be initialized with arbitrary expressions, including function calls.
2. Implement a global initialization mechanism in the C backend to execute non-constant initializers before the main
   entry point.
3. Ensure that initialization order is deterministic, following the module dependency graph and source order.
4. Refactor `std.real` to use module-level `let` variables for `NAN` and `INFINITY` instead of temporary getter
   functions.

## Implementation Phases

### Phase 1: Backend Support for Module Initialization

1. **Relax Restriction**: Modify `backend.l0` to allow non-constant expressions for top-level `let`s. If an initializer
   is not a simple constant, defer its initialization.
2. **C Emitter Changes**:
   - For top-level `let`s with non-constant initializers, emit the C variable as zero-initialized (or uninitialized).
   - Generate a hidden module-level initialization function (e.g., `_dea_init_module_name()`) that contains the
     assignments for these complex `let` declarations.
   - Generate a global initialization function in the main translation unit (called from the C `main` wrapper before the
     L1 `main` function) that calls all module initialization functions in topological dependency order.

### Phase 2: Refactoring and Validation

1. **Refactor `std.real`**: Change `nan_f()`, `nan_d()`, `inf_f()`, and `inf_d()` back to module-level `let` constants
   (e.g., `let NAN_F: float = rt_real_get_nan_f();`).
2. **Testing**: Add a fixture that declares top-level `let`s initialized via function calls and ensures the values are
   correctly visible in `main`.
3. **Validation**: Ensure `make -C l1 test-stage1` passes and `std.real` usage continues to work identically.

## Verification Criteria

1. Top-level `let` declarations can be initialized with function calls without triggering ICEs.
2. The initialization occurs deterministically before `main()` begins execution.
3. `make -C l1 test-stage1` passes successfully.
4. `std.real` is simplified to use `let` constants for `NAN` and `INFINITY`.
