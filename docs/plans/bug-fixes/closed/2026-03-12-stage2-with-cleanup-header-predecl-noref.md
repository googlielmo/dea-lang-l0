# Bug Fix Plan

## Stage 2 `with` cleanup-block header predeclaration parity

- Date: 2026-03-12
- Status: Closed (fixed)
- Title: Fix Stage 2 backend lowering for nullable `with`-header lets referenced by cleanup blocks on header `?` failure
- Kind: Bug Fix
- Severity: High
- Stage: 2
- Subsystem: Backend / `with` lowering / Stage 2 build-run parity
- Modules:
  - `compiler/stage2_l0/src/backend.l0`
  - `compiler/stage2_l0/tests/backend_test.l0`
  - `compiler/stage2_l0/tests/l0c_build_run_test.sh`
- Test modules:
  - `compiler/stage2_l0/tests/backend_test.l0`
  - `compiler/stage2_l0/tests/l0c_build_run_test.sh`
- Repro:
  - `./build/dea/bin/l0c-stage2 --run -P examples demo -- add 2 3`

## Summary

Stage 2 emitted cleanup-block code that referenced nullable `with`-header lets before they were declared when a later
header initializer failed through `?`. The visible user symptom was `examples/demo.l0` failing during generated C
compilation with undeclared `left` and `right` variables.

Stage 1 already handles this case by predeclaring nullable cleanup-block header lets to `null`, then emitting later
assignments after the header `?` succeeds. Stage 2 should mirror that lowering.

## Planned Changes

1. Add backend helpers to:
   - resolve the type of a `let`,
   - predeclare nullable cleanup-block header lets to their null literal,
   - emit later assignments for those predeclared lets.
2. Update `be_emit_with_stmt()` so cleanup-block form does a predeclaration pass over header items before emitting the
   actual initializer statements.
3. Keep inline `=>` cleanup lowering unchanged.
4. Add generated-C regression coverage for nullable header-let predeclaration and an end-to-end `examples/demo`
   build-run regression.

## Verification

Run:

```bash
./scripts/l0c --run -P examples demo -- add 2 3
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/backend_test.l0
./scripts/build-stage2-l0c.sh
./build/dea/bin/l0c-stage2 --run -P examples demo -- add 2 3
compiler/stage2_l0/tests/l0c_build_run_test.sh
```
