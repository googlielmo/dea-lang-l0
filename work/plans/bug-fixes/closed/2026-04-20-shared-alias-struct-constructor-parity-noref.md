# Bug Fix Plan

## Shared alias-to-struct constructor parity

- Date: 2026-04-20
- Status: Closed
- Title: Restore shared alias-to-struct constructor parity in self-hosted expression typing and L1 `const` lowering
- Kind: Bug Fix
- Scope: Shared
- Severity: High
- Stage: Shared
- Targets:
  - L0 Python Stage 1
  - L0 Stage 2
  - L1 Stage 1
- Origin: L0 Python Stage 1, which already accepts type-alias-to-struct constructor calls in ordinary expressions and
  lowers them through the underlying struct-constructor path
- Porting rule: Treat Python Stage 1 as the oracle; settle the self-hosted ordinary-expression behavior in L0 Stage 2
  first, then port the aligned logic mechanically into L1 Stage 1 while extending the L1-only top-level `const` lowering
  path to match the same accepted constructor surface
- Target status:
  - L0 Python Stage 1: Implemented
  - L0 Stage 2: Implemented
  - L1 Stage 1: Implemented
- Subsystem: Expression typing, constant-initializer checking, and top-level let lowering for type-alias-to-struct
  constructors
- Modules:
  - `l0/compiler/stage1_py/l0_expr_types.py`
  - `l0/compiler/stage2_l0/src/expr_types.l0`
  - `l0/compiler/stage2_l0/src/backend.l0`
  - `l1/compiler/stage1_l0/src/expr_types.l0`
  - `l1/compiler/stage1_l0/src/signatures.l0`
  - `l1/compiler/stage1_l0/src/backend.l0`
- Test modules:
  - `l0/compiler/stage1_py/tests/type_checker/test_expr_typechecker_calls.py`
  - `l0/compiler/stage1_py/tests/backend/test_codegen_constructors.py`
  - `l0/compiler/stage2_l0/tests/expr_types_test.l0`
  - `l0/compiler/stage2_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/expr_types_test.l0`
  - `l1/compiler/stage1_l0/tests/backend_test.l0`
  - `l1/compiler/stage1_l0/tests/c_emitter_test.l0`
- Related:
  - `work/plans/bug-fixes/closed/2026-04-20-shared-top-level-arc-cleanup-and-drop-diagnostic-parity-noref.md`
- Repro: `build/dea/bin/l1c-stage1 --check /tmp/local_alias.l1` on a local
  `type Alias = Box; let b: Alias = Alias("hi");` program, compared with successful
  `PYTHONPATH=compiler/stage1_py ../.venv/bin/python compiler/stage1_py/l0c.py --gen` on the equivalent L0 source

## Summary

Python L0 Stage 1 already treats `Alias(...)` as a valid struct-constructor surface when `Alias` resolves to a struct
type alias. The self-hosted implementations currently do not match that behavior:

1. L0 Stage 2 rejects ordinary local alias-constructor calls with `TYP-0151`.
2. L1 Stage 1 rejects the same ordinary calls with `TYP-0151`.
3. L1 top-level `const` checking partially special-cases alias-to-struct constructors, but backend constant-initializer
   emission still does not support them, which currently leads to `[ICE-1181] unsupported top-level let initializer`.

This plan restores Python Stage 1 parity for alias-to-struct constructor calls in the self-hosted compilers and removes
the L1 `const`-initializer mismatch that surfaced while auditing top-level `const` strings.

## Current State

- In Python L0 Stage 1, ordinary call typing explicitly routes `SYM_TYPE_ALIAS` whose resolved type is `StructType`
  through the same constructor path as direct struct names.
- A focused Python Stage 1 codegen probe for `let b: Alias = Alias("hi");` emits the underlying struct initializer as
  expected.
- In L0 Stage 2 and L1 Stage 1, ordinary value-position resolution still treats `SYM_TYPE_ALIAS` as a type-only name, so
  `Alias("hi")` fails before constructor typing can reuse the resolved struct type.
- L0 currently has no top-level `const`, so the constant-initializer surface of this bug is L1-only.
- In L1, the top-level `const` checker already treats alias-to-struct constructors as compile-time-constant candidates,
  but backend constant-constructor emission still recognizes only direct `SYM_STRUCT` and `SYM_ENUM_VARIANT` callees.

## Root Cause

The implementations disagree about whether a type alias that resolves to a struct may participate in constructor-call
syntax.

- Python Stage 1 says yes, but only for call expressions, by resolving the alias target and reusing struct-constructor
  semantics.
- L0 Stage 2 and L1 Stage 1 say no in ordinary expression typing because `EX_VAR_REF` on a type alias still falls
  through the generic "type name cannot be used as a value" path before the call logic can reinterpret the callee as a
  constructor.
- L1 `const` checking independently says yes for alias-to-struct constructors, but backend top-level constant lowering
  still says no, which creates the current checker/backend split and the observed ICE.

## Scope of This Fix

1. Restore Python Stage 1-equivalent alias-to-struct constructor behavior in ordinary expressions for L0 Stage 2.
2. Port the same ordinary-expression behavior into L1 Stage 1.
3. Align the L1 top-level `const` path so alias-to-struct constant constructors either lower successfully or no longer
   diverge from the settled ordinary-expression surface.
4. Add explicit regression coverage that locks in the Python Stage 1 oracle and the self-hosted parity behavior.

## Approach

- Reuse the self-hosted struct-constructor typing path when a call callee resolves to `SYM_TYPE_ALIAS` whose resolved
  type is `TY_STRUCT`.
- Keep bare alias value references invalid: `Alias` on its own should still report `TYP-0151`; only the constructor-call
  surface should change.
- Extend the L1 constant-initializer path to resolve alias-backed struct constructors through the same underlying struct
  metadata and initializer emission used for direct struct constructors.
- Add one focused local ordinary-expression regression per target plus one focused L1 top-level `const` regression for
  the current ICE surface.

## Non-goals

- No change to non-struct type aliases in value position.
- No change to enum-type aliases unless Python Stage 1 already defines an equivalent constructor surface there.
- No new diagnostic-code family; the intended fix is behavioral parity, not new error taxonomy.

## Tests

Minimum coverage for the implementation:

1. Python Stage 1 keeps accepting `let b: Alias = Alias("hi");` when `Alias` resolves to a struct.
2. L0 Stage 2 and L1 Stage 1 accept the same local constructor call and lower it like the direct struct-name form.
3. Bare `Alias` in value position still reports `TYP-0151`.
4. L1 top-level `const b: Alias = Alias("hi");` lowers through the static initializer path instead of reaching
   `[ICE-1181]`.

## Verification

```bash
cd l0 && ../.venv/bin/python -m pytest -n0 compiler/stage1_py/tests/type_checker/test_expr_typechecker_calls.py compiler/stage1_py/tests/backend/test_codegen_constructors.py
cd l0 && make test-stage2 TESTS="expr_types_test backend_test"
cd l1 && make test-stage1 TESTS="expr_types_test backend_test c_emitter_test"
```

## Outcome

- Implemented alias-to-struct constructor typing parity in self-hosted `l0` Stage 2 and `l1` Stage 1.
- Extended self-hosted backend constructor lowering so `Alias(...)` reuses the underlying struct-constructor path while
  bare alias values remain invalid.
- Closed the L1 checker/backend split by teaching top-level `const` lowering to accept alias-backed struct constructors.
- Added focused Python Stage 1, `l0` Stage 2, and `l1` Stage 1 regressions for accepted alias constructors and rejected
  bare alias values.

## Assumptions

- Python L0 Stage 1 remains the behavioral oracle for shared alias-to-struct constructor semantics.
- The desired parity change is limited to constructor-call syntax, not to bare alias values in arbitrary expression
  position.
