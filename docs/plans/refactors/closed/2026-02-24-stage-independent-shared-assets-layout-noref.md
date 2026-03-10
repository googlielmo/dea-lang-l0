# Refactor Plan

## Move shared stdlib/runtime assets to `compiler/shared` for Stage 1 and Stage 2 reuse

- Date: 2026-02-24
- Status: Closed (implemented)
- Title: Relocate Stage 1-owned stdlib/runtime assets into stage-independent shared directories and update all path defaults
- Kind: Refactor
- Severity: Medium (toolchain layout and default environment-path contract change)
- Stage: 1/2
- Subsystem: Compiler asset layout + CLI path defaults + tests/docs
- Modules: `compiler/stage1_py/l0c.py`, `l0c`, `l0-env.sh`,
  `compiler/stage1_py/tests/conftest.py`, `compiler/stage1_py/tests/driver/test_driver.py`,
  `README.md`, `SECURITY.md`, `docs/reference/design-decisions.md`,
  `docs/reference/c-backend-design.md`
- Asset moves: `compiler/stage1_py/l0/stdlib -> compiler/shared/l0/stdlib`,
  `compiler/stage1_py/runtime -> compiler/shared/runtime`

## Summary

Make stdlib and runtime stage-independent by moving them out of `compiler/stage1_py` into `compiler/shared`.

Apply a one-shot hard cut (no compatibility fallback, no symlink shim).

Set canonical `L0_HOME` base to `compiler`, so derived defaults become:

1. `L0_SYSTEM=$L0_HOME/shared/l0/stdlib`
2. `L0_RUNTIME_INCLUDE=$L0_HOME/shared/runtime`

Update direct path users in Stage 1 tests, wrapper scripts, and active docs.

## Public API and Interface Changes

1. Environment-default behavior in Stage 1 CLI (`l0c.py`) changes:
   `L0_HOME` is interpreted as compiler root, not Stage 1 root.
2. Wrapper script behavior changes:
   `./l0c` defaults `L0_HOME` to `.../compiler`, then invokes `stage1_py/l0c.py`.
3. Shell bootstrap behavior changes:
   `source ./l0-env.sh` exports `L0_HOME=.../compiler`.
4. CLI flags/env var names remain unchanged:
   `--sys-root`, `--runtime-include`, `L0_SYSTEM`, `L0_RUNTIME_INCLUDE`, `L0_RUNTIME_LIB`.

## Implementation Sequence

1. Move directories:
   1. `compiler/stage1_py/l0/stdlib` -> `compiler/shared/l0/stdlib`
   2. `compiler/stage1_py/runtime` -> `compiler/shared/runtime`
2. Update Stage 1 default path derivation in `compiler/stage1_py/l0c.py` (`_init_env_defaults`):
   1. set `L0_SYSTEM` default to `$L0_HOME/shared/l0/stdlib`
   2. set `L0_RUNTIME_INCLUDE` default to `$L0_HOME/shared/runtime`
3. Update repo launcher `l0c`:
   1. default `L0_HOME="${DIR}/compiler"`
   2. run `python3 "$L0_HOME/stage1_py/l0c.py" "$@"`
4. Update `l0-env.sh`:
   1. export `L0_HOME="${SCRIPT_DIR}/compiler"`
5. Update Stage 1 tests with hardcoded old paths:
   1. `compiler/stage1_py/tests/conftest.py`
   2. `compiler/stage1_py/tests/driver/test_driver.py`
6. Update active docs referencing old locations:
   1. `README.md`
   2. `SECURITY.md`
   3. `docs/reference/design-decisions.md`
   4. `docs/reference/c-backend-design.md`
7. Remove old directories after move so stale path usage fails fast.
8. Run verification gates and path audits.

## Acceptance Criteria

1. No active runtime/stdlib assets remain under `compiler/stage1_py/{l0/stdlib,runtime}`.
2. Stage 1 and Stage 2 workflows succeed using shared assets under `compiler/shared`.
3. `./l0c` works with no manual env exports in a clean shell.
4. Stage 1 tests pass.
5. Stage 2 tests and trace checks pass.
6. Active docs reflect canonical shared paths and updated `L0_HOME` semantics.
7. No fallback logic for old layout exists (hard-cut requirement).

## Test Cases and Scenarios

1. Stage 1 regression suite:
   `cd compiler/stage1_py && pytest -n auto`
2. Stage 2 suite:
   `./compiler/stage2_l0/run_tests.sh`
3. Stage 2 trace gate:
   `./compiler/stage2_l0/run_trace_tests.sh`
4. CLI smoke tests:
   1. `./l0c -P examples --check hello`
   2. `./l0c -P examples --gen hello`
   3. `./l0c -P examples --build hello -o /tmp/l0_hello`
5. Env override checks:
   1. explicit `L0_SYSTEM` still overrides derived default
   2. explicit `L0_RUNTIME_INCLUDE` still overrides derived default
6. Stale-path audit:
   `rg -n "compiler/stage1_py/l0/stdlib|compiler/stage1_py/runtime|stage1_root / \"l0\" / \"stdlib\"|stage1_root / \"runtime\"" README.md SECURITY.md docs compiler/stage1_py`

## Assumptions and Defaults

1. Hard cut is intentional; no migration shim is required.
2. Canonical `L0_HOME` is `compiler`.
3. Env var names and CLI flags are stable and unchanged.
4. Historical records under `docs/plans/**` may keep old paths unless explicitly normalized later.

## Implementation Verification

Executed on 2026-02-24:

1. `uv run --group dev pytest -n auto compiler/stage1_py/tests`
   Result: pass (`985 passed`).
2. `./compiler/stage2_l0/run_tests.sh`
   Result: pass (`9/9` tests passed).
3. `./compiler/stage2_l0/run_trace_tests.sh`
   Result: pass (`9/9` trace checks passed; `leaked_object_ptrs=0`, `leaked_string_ptrs=0` for all tests).
4. `./l0c -P examples --check hello`
   Result: pass.
5. `./l0c -P examples --gen hello -o /tmp/hello.c`
   Result: pass.
6. `./l0c -P examples --build hello -o /tmp/hello_bin`
   Result: pass.
