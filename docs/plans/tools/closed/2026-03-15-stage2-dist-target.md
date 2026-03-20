# Feature Plan

## Stage 2 distribution archive target

- Date: 2026-03-15
- Status: Closed (implemented)
- Title: Add `make dist` and `make test-dist` for relocatable Stage 2 packaging
- Kind: Feature
- Severity: Medium
- Stage: Shared
- Subsystem: Build workflow / release packaging
- Modules:
  - `Makefile`
  - `scripts/dist_tools_lib.py`
  - `scripts/gen_dist_tools.py`
  - `README.md`
  - `docs/reference/architecture.md`
  - `docs/reference/project-status.md`
  - `compiler/stage2_l0/README.md`
- Test modules:
  - `tests/test_make_dea_build_workflow.py`
  - `tests/test_make_dist_workflow.py`

## Summary

The repository already has two working Stage 2 delivery surfaces:

1. a repo-local developer build under `DEA_BUILD_DIR`
2. a relocatable install prefix produced by `make PREFIX=... install`

What is still missing is a one-command packaging target that turns the relocatable Stage 2 layout into a distributable
archive without requiring the caller to choose or manage a persistent prefix directory.

## Goals

1. `make dist` creates a relocatable `dist/` tree containing exactly the files needed to run `l0c`.
2. `make dist` also writes one host-native archive for that tree:
   - `.zip` on Windows
   - `.tar.gz` on POSIX hosts
3. The top-level distribution directory is named `dea-l0`, and the archive itself is named
   `dea-l0-lang_<os>-<arch>_YYYYMMDD-HHMMSS` using the lower-case OS/architecture from the recorded build host and the
   UTC build timestamp.
4. The packaging surface reuses the existing install-prefix layout so there is only one relocatable runtime contract.
5. `make test-dist` validates that the produced archive can be unpacked and used independently of the repository path.

## Non-Goals

- A versioned release naming scheme.
- A global installer or platform-specific packaging beyond zip/tar.gz.
- Replacing `make install` as the explicit install-prefix workflow.

## Implementation

1. Extend `scripts/dist_tools_lib.py` with helpers to archive a prepared relocatable layout.
2. Extend `scripts/gen_dist_tools.py` with one `make-dist` command that:
   - builds a bootstrap Stage 2 compiler
   - self-hosts a relocatable Stage 2 binary
   - assembles `dea-l0/`
   - archives `dea-l0/` as `dea-l0-lang_<os>-<arch>_YYYYMMDD-HHMMSS`
3. Add `dist` and `test-dist` targets to `Makefile` and document them in `make help`.
4. Cover the new behavior with:
   - one Make workflow regression for help/dry-run coverage
   - one end-to-end dist workflow test that unpacks the archive and builds a hello-world program

## Verification

```bash
make dist
make test-dist
```

Expected:

1. `make dist` reports the generated `dea-l0/` directory and archive path under `build/`.
2. The packaged tree contains `bin/l0c-stage2`, `bin/l0c-stage2.native`, `bin/l0c`, `bin/l0-env.sh`,
   `shared/l0/stdlib/...`, and `shared/runtime/...`.
3. After unpacking the archive elsewhere, `bin/l0c-stage2 --version` and a hello-world `--build` invocation succeed.
