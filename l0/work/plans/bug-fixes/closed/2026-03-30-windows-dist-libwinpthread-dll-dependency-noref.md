# Bug Fix Plan

## Windows distribution binary depends on `libwinpthread-1.dll`

- Date: 2026-03-30
- Status: Implemented
- Title: Statically link GCC runtime in Windows dist/install builds to eliminate `libwinpthread-1.dll` dependency
- Kind: Bug Fix
- Severity: High (`l0c` binary from CI distribution cannot run from Windows CMD outside MSYS2)
- Stage: Tooling
- Subsystem: Distribution / build tooling
- Modules:
  - `Makefile`
- Test modules:
  - `tests/test_make_dist_workflow.py`
- Repro: Download the Windows `.zip` distribution, extract, and run `l0c --version` from CMD

## Summary

The CI-built `l0c` binary on Windows depends on `libwinpthread-1.dll`, which is part of the MSYS2 MinGW-w64 runtime but
is not present on a standard Windows PATH outside MSYS2. This prevents the distributed compiler from running in CMD or
PowerShell.

## Root Cause

MinGW-w64 GCC with the POSIX threading model (the default in MSYS2 MINGW64) implicitly links `libwinpthread-1.dll` into
every compiled binary. The L0 codebase has zero direct pthread usage; the dependency is entirely from GCC's own runtime
support.

## Fix

Add a `DIST_L0_CFLAGS_DEFAULT` Makefile variable that expands to `-O2 -static` on Windows and `-O2` on other platforms.
The `dist` and `install` targets use this as the default value for `L0_CFLAGS`, statically linking the GCC runtime
libraries (including winpthread) into the `l0c` binary. Users who set `L0_CFLAGS` explicitly override the default as
before. Dev build targets are not affected.

## Verification

- `make test-workflows` passes on all platforms.
- On Windows MSYS2 MINGW64: `make dist`, then `ldd` the resulting binary shows only system DLLs.
- The built `l0c` binary runs from CMD outside MSYS2.
