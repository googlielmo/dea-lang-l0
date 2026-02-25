# Refactor Plan

## Unify `DriverResult` into `DriverState` with source cache

- Date: 2026-02-25
- Status: Closed (implemented)
- Title: Unify `DriverResult` into `DriverState` with embedded source cache
- Kind: Refactor
- Severity: Low (API simplification, no behavioral change)
- Stage: 2
- Subsystem: Driver
- Modules: `compiler/stage2_l0/src/driver.l0`, `compiler/stage2_l0/src/diag_print.l0`,
  `compiler/stage2_l0/src/l0c.l0`
- Test modules: `compiler/stage2_l0/tests/driver_test.l0`

## Summary

Replace `DriverResult` with `DriverState`, a single struct that owns transient session state
(`loaded` list) alongside outputs (`units`, `diags`). Add `source_names`/`source_texts` vectors
as a source cache populated during `dr_load_module`.

Reduce `dr_load_module` from 6 parameters to 4 by threading the state struct instead of
individual fields.

Add `dp_print_collector_with_sources` to `diag_print` so callers with a driver state can pass
pre-populated source cache vectors, avoiding redundant file reads during diagnostic printing.

## Changes

1. `driver.l0`: Replace `DriverResult` struct with `DriverState` (adds `loaded`,
   `source_names`, `source_texts` fields). Rename `driver_result_free` to `driver_state_free`,
   `driver_result_has_errors` to `driver_has_errors`. Refactor `dr_load_module` to take
   `DriverState*` instead of separate `units`/`loaded`/`diags` params. Populate source cache
   after successful `read_file` + BOM strip.
2. `diag_print.l0`: Add `dp_print_collector_with_sources` that accepts external cache vectors.
   Rewrite `dp_print_collector` to delegate to the new function with fresh local vectors.
3. `l0c.l0`: Update `l0c_cmd_check` and `l0c_cmd_tok` all-modules path to use
   `dp_print_collector_with_sources` with driver state cache. Update `driver_result_*` calls to
   `driver_state_free`/`driver_has_errors`.
4. `driver_test.l0`: Update type and function names to match new API.

## Verification

All 14 Stage 2 tests pass. All 14 trace checks pass with zero leaks.
