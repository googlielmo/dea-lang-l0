# Bug Fix Plan

## Stage 2 Windows argv regression uses CRLF redirected output

- Date: 2026-03-14
- Status: Implemented
- Title: Normalize Windows CRLF output in the Stage 2 argv forwarding shell regression
- Kind: Bug Fix
- Severity: Medium
- Stage: 2
- Subsystem: Test infrastructure
- Modules:
    - `compiler/stage2_l0/tests/l0c_build_run_test.sh`
- Test modules:
    - `compiler/stage2_l0/tests/l0c_build_run_test.sh`
- Repro: Windows CI `make test-stage2`

## Summary

The remaining Windows failure in `l0c_build_run_test.sh` is not an argv forwarding bug. The child program output matches
the expected lines, but redirected stdout uses CRLF line endings on Windows, so the raw `diff` between the expected LF
fixture and the captured output fails.

## Fix

- normalize the captured argv tail before diffing on Windows
- keep the raw-output diagnostics in place so future failures still show the original bytes and escaped line views
- leave non-Windows output comparisons unchanged

## Verification

```bash
compiler/stage2_l0/tests/l0c_build_run_test.sh
```
