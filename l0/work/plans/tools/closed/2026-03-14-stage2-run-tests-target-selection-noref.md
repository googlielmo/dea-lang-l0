# Tool Plan

## Stage 2 targeted `run_tests.py` selection and timing

- Date: 2026-03-14
- Status: Implemented
- Title: Add direct Stage 2 test-name selection and per-test wall-clock timing to `run_tests.py`
- Kind: Tooling
- Severity: Medium
- Stage: 2
- Subsystem: Test runner
- Modules:
  - `Makefile`
  - `compiler/stage2_l0/run_tests.py`
  - `compiler/stage2_l0/README.md`
- Test modules:
  - `compiler/stage2_l0/tests/l0c_stage2_run_tests_selection_test.py`
- Repro: `./.venv/bin/python ./compiler/stage2_l0/run_tests.py driver_test`

## Summary

The Stage 2 runner currently executes the full suite every time, which slows focused local debugging. It also prints
only bare `PASS` / `FAIL` status lines, so short targeted runs give no per-test wall-clock feedback.

## Fix

- accept optional positional test selectors in `run_tests.py`
- forward `make test-stage2 TESTS="..."` into the same selector flow, while keeping the blank default on the full suite
- resolve selectors against `compiler/stage2_l0/tests/` file names, while allowing the extension to be omitted
- reject unknown selectors and future ambiguous stems with descriptive errors
- record wall-clock duration for each completed test and include it in the PASS/FAIL output
- cover the selection and formatting helpers with a dedicated Stage 2 Python regression

## Verification

```bash
./.venv/bin/python ./compiler/stage2_l0/tests/l0c_stage2_run_tests_selection_test.py
./.venv/bin/python ./compiler/stage2_l0/run_tests.py driver_test l0c_stage2_run_tests_selection_test
make DEA_BUILD_DIR=build/dea test-stage2 TESTS="driver_test l0c_stage2_run_tests_selection_test"
```
