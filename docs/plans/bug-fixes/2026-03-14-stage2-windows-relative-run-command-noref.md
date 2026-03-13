# Bug Fix Plan

## Stage 2 Windows relative `--run` command fallback

- Date: 2026-03-14
- Status: Implemented
- Title: Normalize Windows relative executable tokens before Stage 2 `system()` execution
- Kind: Bug Fix
- Severity: High
- Stage: 2
- Subsystem: Driver / build-run execution
- Modules:
    - `compiler/stage2_l0/src/build_driver.l0`
- Test modules:
    - `compiler/stage2_l0/tests/build_driver_test.l0`
    - `compiler/stage2_l0/tests/l0c_build_run_test.sh`
    - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`
- Repro: Windows CI `make test-stage2`

## Summary

Windows Stage 2 `--run` still fails when the driver falls back to the current directory for temp artifacts. The
temp executable path becomes `./l0c-stage2-run-...exe`, and `system()` routes that through `cmd.exe`, which treats the
leading `./` as a command named `.` and aborts before the child program starts.

## Fix

Normalize the first Windows shell token before joining the command line:

- rewrite relative executable paths beginning with `.` from POSIX-style `/` separators to `\`
- keep plain command names unchanged so compiler invocations such as `gcc` still log and execute normally
- cover the normalization with a focused `build_driver_test.l0` regression

## Verification

```bash
./scripts/l0c -P compiler/stage2_l0/src --run compiler/stage2_l0/tests/build_driver_test.l0
compiler/stage2_l0/tests/l0c_build_run_test.sh
compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh
```
