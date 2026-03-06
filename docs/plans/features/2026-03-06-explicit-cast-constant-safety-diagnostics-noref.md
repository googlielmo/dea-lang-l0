# Feature Plan

## Explicit cast constant-safety diagnostics in Stage 1

- Date: 2026-03-06
- Status: Draft
- Title: Add compile-time diagnostics for provably-invalid explicit casts (`int -> byte` overflow and constant-null pointer unwrap)
- Kind: Feature
- Severity: Medium
- Stage: 1
- Subsystem: Type checking (`l0_expr_types.py`), diagnostics, cast semantics
- Modules:
    - `compiler/stage1_py/l0_expr_types.py`
    - `compiler/stage1_py/l0_diagnostics.py`
    - `compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py`
    - `compiler/stage1_py/tests/type_checker/test_expr_typechecker_casts_and_nullability.py`
    - `compiler/stage1_py/tests/integration/test_byte_type.py`
- Test modules:
    - `compiler/stage1_py/tests/diagnostics/test_diagnostic_codes.py`
    - `compiler/stage1_py/tests/type_checker/test_expr_typechecker_casts_and_nullability.py`
    - `compiler/stage1_py/tests/integration/test_byte_type.py`

## Summary

Stage 1 currently accepts some explicit casts that are already known to fail at runtime.
This plan introduces front-end diagnostics for compile-time-provable failures while preserving runtime checks for dynamic values.

Scope in this iteration:

1. Add `TYP-0700` for explicit `int -> byte` casts when the cast operand is compile-time-known and out of range.
2. Add `TYP-0701` for explicit casts from nullable pointer to non-null pointer when the operand is compile-time-known `null`.
3. Keep checks explicit-cast only (`as`); do not introduce implicit narrowing.
4. Keep constant analysis intentionally narrow (literals and literal-preserving wrappers) but structured for later extension.

## Behavior Changes

### `TYP-0700` explicit int-to-byte constant overflow

- Trigger: `expr as byte` where `expr` is provably an integer constant and value is outside `0..255`.
- Diagnostic message includes:
  - cast direction (`int` to `byte`),
  - concrete value,
  - accepted range (`0..255`).
- Examples:
  - `300 as byte` -> error
  - `(-1) as byte` -> error
  - `x as byte` (unknown at compile time) -> allowed, runtime checked in backend/runtime.

### `TYP-0701` explicit constant-null pointer unwrap

- Trigger: explicit cast `T*? as T*` where operand is provably `null` at compile time.
- Example: `(null as int*?) as int*` -> error.
- Non-constant values of type `T*?` remain allowed for explicit cast and are checked at runtime.

## Implementation Plan

1. Reserve diagnostic codes in `DIAGNOSTIC_CODE_FAMILIES["TYP"]`.
2. Extend `ExpressionTypeChecker._infer_cast` with two explicit-cast compile-time guardrails:
   - constant int range check for `int -> byte`,
   - constant-null detection for `T*? -> T*`.
3. Add helper functions in `l0_expr_types.py`:
   - integer constant extractor for cast operands,
   - compile-time null detector for cast operands.
4. Keep backend runtime checks unchanged (`_rt_narrow_*`, optional unwrap path) as safety net for non-constant casts.
5. Add diagnostic trigger coverage and focused semantic tests.

## Extensibility Notes

To keep this easy to extend in follow-up work:

1. Constant helpers are isolated from cast policy logic in `_infer_cast`.
2. Helpers support parenthesized wrappers and recursive cast/null inspection.
3. Future constant-folding can replace/augment helper internals without changing diagnostics policy at cast call sites.

## Verification

Planned verification commands:

```bash
cd compiler/stage1_py
pytest tests/type_checker/test_expr_typechecker_casts_and_nullability.py
pytest tests/integration/test_byte_type.py -k overflow
pytest tests/diagnostics/test_diagnostic_codes.py -k "TYP-0700 or TYP-0701"
```

## Related Docs

- `docs/reference/architecture.md`
- `docs/reference/c-backend-design.md`
- `docs/specs/compiler/stage1-contract.md`

