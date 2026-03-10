# Refactor Plan

## Remove workarounds for drop in with clauses

- Date: 2026-02-27
- Status: Closed (implemented)
- Title: Remove workarounds for `drop` in `with` clauses
- Kind: Refactor
- Severity: Low (API simplification, no behavioral change)
- Stage: 2
- Subsystem: AST, Parser, Standard Library
- Modules: `compiler/shared/l0/stdlib/std/time.l0`, `compiler/stage2_l0/src/ast.l0`, `compiler/stage2_l0/src/l0c.l0`, `compiler/stage2_l0/src/parser/expr.l0`, `compiler/stage2_l0/src/parser/shared.l0`, `compiler/stage2_l0/src/parser/stmt.l0`, `compiler/stage2_l0/src/util/log.l0`, `examples/newdrop.l0`, `docs/reference/ownership.md`
- Test modules: `compiler/stage2_l0/tests/driver_test.l0`, `compiler/stage2_l0/tests/log_test.l0`

## Summary

Remove redundant direct wrappers (e.g. `log_config_free`, `import_free`, `qn_result_free_only_container`) that were originally created solely to avoid placing `drop` directly in inline cleanups within `with` blocks.

Replace `cleanup { drop x; }` blocks with inline `=> drop x` in `std.time`.
Explicitly document that the `drop` statement natively accepts nullable pointers (`T*?`) and gracefully handles null values at runtime as a no-op, meaning these wrappers aren't necessary.

Kept `type_ref_free` as it performs legitimate deep cleanup of contained string vectors.

## Changes

1. `ast.l0`: Removed redundant single-pointer free wrappers (`import_free`, `match_arm_free`, `case_arm_free`, `case_else_free`, `with_item_free`). Replaced their usages directly with `drop` operations.
2. `parser/shared.l0`, `parser/expr.l0`, `parser/stmt.l0`: Removed `qn_result_free_only_container` and replaced usages directly with `drop q` in parsing paths. Updated `case_else` dropping to natively drop the nullable pointer.
3. `util/log.l0` & `l0c.l0`: Removed `log_config_free` as it was a redundant wrapper around `drop` and updated its usage in `with` block cleanups.
4. `std.time.l0`: Replaced `cleanup { drop parts; }` blocks with inline `with (... => drop parts)` for `RtTimeParts`.
5. `tests/driver_test.l0`, `tests/log_test.l0`: Updated `log_config_free` usages in `with` blocks to `drop cfg`.
6. `docs/reference/ownership.md`: Added explicit documentation clarifying that the `drop` statement accepts both standard pointers (`T*`) and nullable pointers (`T*?`), and that `drop null` is a safe no-op.
7. `examples/newdrop.l0`: Updated inline comments regarding variable liveness and delegate dropping.

## Verification

Refactoring introduces no behavioral changes and only simplifies the API. Confirmed that the compiler tests and trace tests pass with zero memory leaks, as expected when delegating cleanup directly to the native `drop` operator.
