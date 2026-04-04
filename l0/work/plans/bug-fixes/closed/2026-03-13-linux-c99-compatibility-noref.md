# Bug Fix Plan

## Linux and strict C99 compatibility fixes for runtime, backend emission, and bootstrap validation

- Date: 2026-03-13
- Status: Closed (fixed)
- Title: Fix Linux and strict C99 compatibility bugs blocking host validation and bootstrap checks
- Kind: Bug Fix
- Severity: High
- Stage: Shared
- Subsystem: Runtime portability / C backend emission / Stage 2 bootstrap validation
- Modules:
  - `compiler/shared/runtime/l0_runtime.h`
  - `compiler/stage1_py/l0_backend.py`
  - `compiler/stage1_py/l0_c_emitter.py`
  - `compiler/stage2_l0/src/backend.l0`
  - `compiler/stage2_l0/src/c_emitter.l0`
  - `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`
  - `compiler/stage2_l0/README.md`
- Test modules:
  - `compiler/stage1_py/tests/backend/test_codegen_advanced.py`
  - `compiler/stage1_py/tests/backend/test_codegen_lvalue_caching.py`
  - `compiler/stage1_py/tests/integration/test_toplet.py`
  - `compiler/stage2_l0/tests/backend_test.l0`
  - `compiler/stage2_l0/tests/fixtures/backend_golden/types_and_toplet/types_and_toplet.golden.c`
  - `compiler/stage2_l0/tests/l0c_codegen_test.sh`
  - `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`
- Repro:
  - `make test-all`

## Summary

Linux validation exposed a cluster of portability bugs that were not visible on the primary local development path. The
failures break strict C99 compilation under GCC, assume Linux/POSIX runtime details that are not always available under
the current feature-macro set, and make the Stage 2 bootstrap identity check depend on raw ELF metadata instead of
meaningful code generation stability.

This fix set should restore Linux host compatibility without changing the intended compiler behavior:

1. generated C must compile cleanly under strict C99 on Linux
2. runtime helpers must treat ordinary filesystem edge cases as recoverable failures, not internal panics
3. Stage 1 and Stage 2 retained C output must stay in parity after the C99-safe emission change
4. Linux native bootstrap checks must compare stable artifacts rather than path-sensitive binary metadata

## Bug Inventory

### A. Runtime portability and Linux filesystem handling

1. `l0_runtime.h` assumes `off_t` and nanosecond timestamp members are always available under the current Linux build
   mode, which breaks strict C99 compilation on hosted Linux toolchains.
2. `rt_read_file_all()` can panic on directory and oversized-file cases that should surface as ordinary read failures in
   tests and compiler workflows.

### B. Strict C99 backend emission

1. Stage 1 emits file-scope struct and enum constructor lets through compound literals in places where GCC rejects them
   under strict C99.
2. Stage 2 still emits the old top-level initializer form, so retained-C parity and backend goldens drift after the
   Stage 1 fix unless Stage 2 is updated in lockstep.

### C. Linux bootstrap determinism

1. The Stage 2 triple-bootstrap test compares raw native binaries on Linux, but identical retained C can still produce
   different ELF bytes when source paths differ.
2. The bootstrap harness therefore reports a false mismatch even when the meaningful generated output is stable.

## Fix Plan

### A. Make runtime Linux-safe under strict C99

1. Include the required system types explicitly in `l0_runtime.h`.
2. Guard nanosecond timestamp access behind the actual feature-macro contract instead of assuming Linux implies the
   relevant `struct stat` fields.
3. Treat non-regular files and oversized files as normal read failures in `rt_read_file_all()` instead of panicking.

### B. Emit C99-safe static initializers in both stages

1. Add brace-only static initializer emission helpers for struct and tagged-union constructors.
2. Route top-level constant `let` lowering through those helpers in Stage 1.
3. Mirror the same emission rule in Stage 2 and refresh the affected backend expectations and golden output.

### C. Normalize Linux bootstrap artifact comparison

1. Keep retained-C comparison strict and byte-for-byte.
2. On Linux only, normalize native binaries before comparison using an available strip tool.
3. Document the Linux-specific normalization rule in the Stage 2 bootstrap notes so future failures are interpreted
   correctly.

## Verification

Execute at minimum:

```bash
./.venv/bin/python -m pytest compiler/stage1_py/tests/backend/test_codegen_advanced.py::test_generated_code_compiles_minimal
./.venv/bin/python -m pytest compiler/stage1_py/tests/backend/test_codegen_lvalue_caching.py::test_side_effect_counter_in_let
./.venv/bin/python -m pytest compiler/stage1_py/tests/integration/test_toplet.py::test_execute_toplet_nested_struct
bash compiler/stage2_l0/tests/l0c_codegen_test.sh types_and_toplet
make triple-test
```

Expected results:

1. strict C99 compilation succeeds on Linux for the previously failing Stage 1 generated cases
2. Stage 2 backend goldens match the new static initializer spelling
3. Linux triple-bootstrap passes when retained C is stable and normalized native binaries match
4. `make test-all` no longer fails because of these Linux/C99-specific incompatibilities

## Related Documents

- [Project status](../../../reference/project-status.md)
- [C backend design](../../../reference/c-backend-design.md)
- [Architecture](../../../reference/architecture.md)
