# Bug Fix Plan

## Darwin arm64 triple-bootstrap native mismatch

- Date: 2026-03-17
- Status: Closed (fixed)
- Title: Darwin arm64 triple-bootstrap native mismatch
- Kind: Bug Fix
- Severity: High
- Stage: 2
- Subsystem: Bootstrap/self-hosting validation
- Modules:
  - `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`
  - `compiler/stage2_l0/README.md`
- Test modules:
  - `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`
- Repro: `L0_CC=clang make DEA_BUILD_DIR=build/dev-dea triple-test`

## Summary

The strict triple-bootstrap regression compared the second and third self-built native Stage 2 binaries after stripping.
That passed on Linux and Darwin Intel, but failed on the `macos-15-arm64` GitHub Actions runner even when retained C
matched byte-for-byte.

The remaining delta was Darwin-native metadata rather than Stage 2 codegen drift. Apple linkers support ad hoc
code-signing, and arm64 runners can produce signed outputs whose signature blob differs across output artifacts even
when the linked program content is otherwise identical.

## Fix Plan

1. Extend the deterministic Darwin linker flags used by the triple-bootstrap test to include `-Wl,-no_adhoc_codesign`
   alongside `-Wl,-no_uuid`.
2. Harden Darwin artifact normalization by removing any residual code signature from the copied native artifact before
   running `strip`.
3. Update the Stage 2 README so the manual triple-bootstrap instructions document the same Darwin-native stabilization
   flags.

## Validation

1. Run `L0_CC=clang KEEP_ARTIFACTS=1 ./.venv/bin/python compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py` on Darwin
   to confirm the stricter normalization path still passes.
2. Keep the existing retained-C identity check unchanged so genuine Stage 2 codegen drift still fails the regression.
