# Bug Fix Plan

## Stage 2 null-statement backend parity for `with (null)` and bare `null;`

- Date: 2026-03-22
- Status: Closed (fixed)
- Title: Fix Stage 2 backend parity for statement-position `null` lowering and add null-form golden coverage
- Kind: Bug Fix
- Severity: Medium
- Stage: 2
- Subsystem: Backend / null lowering / Stage 2 codegen parity
- Modules:
  - `compiler/stage2_l0/src/backend.l0`
  - `compiler/stage2_l0/tests/l0c_lib_test.l0`
  - `compiler/stage2_l0/tests/fixtures/driver/cleanup_return_main.l0`
  - `compiler/stage2_l0/tests/fixtures/backend_golden/null_forms_and_with/`
  - `compiler/stage2_l0/tests/l0c_codegen_test.sh`
- Test modules:
  - `compiler/stage2_l0/tests/l0c_lib_test.l0`
  - `compiler/stage2_l0/tests/l0c_codegen_test.sh`
- Repro:
  - `source build/dea/bin/l0-env.sh && l0c --run -P compiler/stage2_l0/tests/fixtures/driver cleanup_return_main`

## Summary

Stage 2 mishandled bare `null` in statement position. The immediate user-visible failure was an internal compiler error
when lowering:

```l0
with (null) {
    return 0;
} cleanup {
    return 1;
}
```

The Stage 2 backend tried to lower the `null` header item as though it needed a typed expression-context null literal,
which reached `ICE-1292`. After an initial stopgap fix, Stage 2 still differed from Stage 1 in one important detail:
Stage 1 treats statement-position `null;` as a no-op comment, while Stage 2 emitted `(void)0;`.

The fix restores exact Stage 1 parity for statement-position `null` and adds a curated backend-golden case that covers
both statement and expression-context null forms.

## Implemented Changes

1. Update `compiler/stage2_l0/src/backend.l0` so `ST_EXPR` with `EX_NULL` emits the emitter-owned comment form
   `/* null literal */` instead of backend-owned C syntax.
2. Keep expression-context `null` lowering unchanged and oracle-matched:
   - pointer / pointer-nullable `null` lowers to `NULL`
   - value-nullable `null` lowers to the optional-wrapper none form or `{0}` in initializer contexts
3. Add `compiler/stage2_l0/tests/fixtures/backend_golden/null_forms_and_with/` and refresh it from Stage 1. The new case
   covers:
   - `with (null) { ... }`
   - bare `null;`
   - `return null` for `int?`
   - `return null` for `int*?`
   - `== null` on value-nullable and pointer-nullable expressions
4. Keep the end-to-end CLI regression in `compiler/stage2_l0/tests/l0c_lib_test.l0` using
   `compiler/stage2_l0/tests/fixtures/driver/cleanup_return_main.l0` so the original `with (null)` crash remains covered
   in built-artifact flows.

## Verification

Run:

```bash
source build/dea/bin/l0-env.sh && l0c --run -P compiler/stage2_l0/tests/fixtures/driver cleanup_return_main
compiler/stage2_l0/tests/l0c_codegen_test.sh null_forms_and_with
source build/dea/bin/l0-env.sh && l0c --run -P compiler/stage2_l0/tests -P compiler/stage2_l0/src l0c_lib_test
```
