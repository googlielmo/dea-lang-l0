# Bug Fix Plan

## Stage 2 `new` expression parity for zero-arg structs and enum variants

- Date: 2026-03-12
- Status: Closed (fixed)
- Title: Fix Stage 2 `new` semantic-analysis parity for zero-argument struct allocation and enum-variant heap allocation
- Kind: Bug Fix
- Severity: High
- Stage: 2
- Subsystem: Semantic analysis / typing / Stage 2 CLI parity
- Modules:
  - `compiler/stage2_l0/src/expr_types.l0`
  - `compiler/stage2_l0/tests/expr_types_test.l0`
  - `compiler/stage2_l0/tests/backend_test.l0`
  - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`
  - `docs/reference/ownership.md`
- Test modules:
  - `compiler/stage2_l0/tests/expr_types_test.l0`
  - `compiler/stage2_l0/tests/backend_test.l0`
  - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`
- Repro:
  - `./build/dea/bin/l0c-stage2 --check -P examples newdrop`
  - `./build/dea/bin/l0c-stage2 --check -P examples hamurabi`

## Summary

Stage 2 diverged from Stage 1 in `new` expression typing:

1. `new Struct` and `new Struct()` were rejected with `TYP-0283` unless all fields were supplied explicitly.
2. `new Variant(...)` was routed through type resolution as though the variant name were a type name, producing
   `SIG-0010` instead of enum-variant allocation behavior.
3. `new EnumType(...)` was not explicitly rejected with the Stage 1 rule that enum heap allocation requires a variant.

The fix should restore Stage 1 behavior, make the intended semantics explicit in docs, and cover the regression at
semantic-analysis, backend, and built-artifact CLI levels.

## Planned Changes

1. Update `compiler/stage2_l0/src/expr_types.l0` so `EX_NEW`:
   - accepts zero-arg struct allocation and only enforces full-field arity when arguments are present,
   - resolves enum variant targets before type-name resolution so `new Variant(...)` is treated as a legal constructor,
   - rejects `new EnumType(...)` without a variant using `TYP-0281`.
2. Add focused Stage 2 typing fixtures for successful and failing `new` cases.
3. Extend backend regression coverage so generated C is validated for zero-initialized struct allocation and
   enum-variant heap allocation.
4. Extend the built Stage 2 artifact regression to require `examples/newdrop.l0` and `examples/hamurabi.l0` to
   type-check unchanged.
5. Clarify the current `new` semantics in `docs/reference/ownership.md`.

## Verification

Run:

```bash
./scripts/l0c --check -P examples newdrop
./scripts/l0c --check -P examples hamurabi
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/expr_types_test.l0
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/backend_test.l0
./scripts/build-stage2-l0c.sh
./build/dea/bin/l0c-stage2 --check -P examples newdrop
./build/dea/bin/l0c-stage2 --check -P examples hamurabi
```
