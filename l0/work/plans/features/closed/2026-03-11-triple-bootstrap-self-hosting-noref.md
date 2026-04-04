# Feature Plan

## Triple-bootstrap / triple-compilation test and Stage 2 self-hosting prerequisites

- Date: 2026-03-11
- Status: Closed (implemented)
- Title: Triple-bootstrap / triple-compilation test and Stage 2 self-hosting prerequisites
- Kind: Feature
- Severity: High
- Stage: 2
- Subsystem: Bootstrap/self-hosting validation / Stage 2 semantic stabilization
- Modules:
  - `compiler/stage2_l0/src/expr_types.l0`
  - `compiler/stage2_l0/src/l0c.l0`
  - `compiler/stage2_l0/run_tests.py`
  - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`
  - `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`
  - `work/plans/tools/closed/2026-03-09-stage2-bootstrap-compiler-artifact-noref.md`
- Test modules:
  - `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`
  - `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh`
- Repro:
  `DIST_DIR=build/tests/triple-probe ./scripts/build-stage2-l0c.sh && ./build/tests/triple-probe/bin/l0c-stage2 --check -P compiler/stage2_l0/src l0c`

## Summary

Phases 1 and 2 of the bootstrap plan produced a runnable Stage 2 compiler artifact and a repo-local Make workflow. This
follow-on milestone is now implemented: the built Stage 2 compiler can self-host on the current checkout and the strict
triple-bootstrap / triple-compilation regression is part of the Stage 2 test surface.

The original blocker was that a built `l0c-stage2` artifact could not yet self-host cleanly on the Stage 2 compiler
sources. A direct `--check` or `--build` of `compiler/stage2_l0/src/l0c.l0` through a built Stage 2 artifact exposed a
cluster of semantic-analysis, literal-decoding, and retained-C parity bugs. Those prerequisites were fixed first, then
the strict fixed-point regression was added on top.

This plan therefore covers both:

1. the prerequisite Stage 2 self-hosting fixes needed to make a built `l0c-stage2` compile the Stage 2 compiler sources
   correctly, and
2. the final strict triple-bootstrap regression that compares the second and third self-built Stage 2 compiler artifacts
   at both the retained-C and native-binary levels.

This plan depends on the Phase 1 and Phase 2 deliverables from
`work/plans/tools/closed/2026-03-09-stage2-bootstrap-compiler-artifact-noref.md`. It does not change that plan’s Phase 3
install-prefix scope.

## Goals

1. Make a built `l0c-stage2` artifact able to `--check` the Stage 2 compiler source tree.
2. Make a built `l0c-stage2` artifact able to `--build --keep-c` the Stage 2 compiler source tree into a second
   self-built compiler artifact.
3. Add an automated triple-bootstrap / triple-compilation regression under the Stage 2 test suite.
4. Require byte-for-byte identity for retained C on every supported host compiler, and for native compiler binaries on
   toolchains that can produce stable binaries with deterministic settings.
5. Keep all bootstrap-comparison artifacts under isolated `build/tests/...` directories.

## Non-Goals

1. Weakening the final comparison to “compiles successfully” only.
2. Comparing generated wrapper scripts; the identity target is retained C and native compiler binaries only.
3. Replacing the bootstrap plan’s Phase 3 install-prefix work.
4. Solving unrelated Stage 2 semantic cleanup that does not block self-hosting or the triple test.

## Public Interface and Deliverables

This feature adds one new Stage 2 regression:

1. `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py`

Its contract is:

1. build a Stage 2 compiler artifact from Stage 1 into an isolated repo-local directory under `build/tests/...`,
2. use that built Stage 2 compiler to build a second self-built compiler artifact from the same source tree,
3. use the second self-built compiler to build a third self-built compiler artifact from the same source tree,
4. compare the second-build retained C artifact against the third-build retained C artifact byte-for-byte,
5. compare the second-build native compiler binary against the third-build native compiler binary byte-for-byte,
6. fail with a clear artifact-difference summary when either comparison differs, and
7. keep artifacts on failure or when explicitly requested, while cleaning them on success by default.

The third self-built compiler must also pass a direct smoke check after the identity comparisons succeed.

## Key Implementation Changes

### A. Unblock direct Stage 2 self-hosting first

1. Add narrow targeted regressions for the currently failing Stage 2 semantic defect classes before attempting the full
   triple-bootstrap harness.
2. Fix the Stage 2 semantic/type-checking behavior that currently prevents a built `l0c-stage2` from checking and
   building `compiler/stage2_l0/src/l0c.l0`.
3. Treat the current parser, lexer, and shared-stdlib failures as symptom clusters. The implementation focus should be
   on the root semantic defects in `expr_types.l0` and directly related helpers, not on ad hoc source rewrites in each
   failing module.
4. Keep prerequisite fixes scoped to self-hosting correctness. Do not broaden this plan into unrelated semantic
   refactors unless a new blocker is discovered during diagnosis.

### B. Add the strict triple-bootstrap harness

1. Build Stage 2 from Stage 1 with `KEEP_C=1` into a unique repo-local directory under `build/tests/...`.
2. Before the full self-build, run a direct built-artifact probe that `--check`s the Stage 2 compiler source tree, so
   self-hosting readiness fails fast with a clear error.
3. Build the second self-built compiler artifact by invoking the built `l0c-stage2` directly with
   `--build --keep-c -P compiler/stage2_l0/src -o <triple_dir>/l0c-stage2-second.native l0c`.
4. Build the third self-built compiler artifact by invoking the second self-built compiler directly with
   `--build --keep-c -P compiler/stage2_l0/src -o <triple_dir>/l0c-stage2-third.native l0c`.
5. Compare `l0c-stage2-second.c` against `l0c-stage2-third.c`, and compare `l0c-stage2-second.native` against
   `l0c-stage2-third.native` when the host compiler can produce stable binaries.
6. On mismatch, report which artifacts differ and include compact hashes/sizes; include a short unified diff only for
   retained-C mismatches.
7. After a successful comparison, run a direct smoke check through the third self-built compiler with `L0_HOME` set
   explicitly.

### C. Enforce deterministic native outputs

1. Resolve one host C compiler once and use it for all self-builds.
2. Preserve existing user-provided `L0_CFLAGS`, but append deterministic linker flags by platform:
   1. Darwin: `-Wl,-no_uuid`
   2. ELF gcc/clang toolchains: `-Wl,--build-id=none`
3. If the host compiler is `tcc`, keep the retained-C comparison but skip the native-binary stability probe and the
   native-binary identity check.
4. If some other host toolchain still does not produce stable binaries after that deterministic-flags probe, fail the
   test early with a clear unsupported-toolchain diagnostic instead of silently relaxing the native-binary comparison.

### D. Keep the existing Stage 2 bootstrap regression focused

1. `compiler/stage2_l0/tests/l0c_stage2_bootstrap_test.sh` should remain the end-to-end regression for “a built Stage 2
   artifact works correctly”.
2. The new triple-bootstrap comparison logic belongs in the dedicated triple-bootstrap test, not in the existing Stage 2
   bootstrap script.

## Test Plan

1. Add targeted Stage 2 regressions for the semantic/type-checking defect classes that currently block built-artifact
   self-hosting.
2. Verify that a built `l0c-stage2` can `--check -P compiler/stage2_l0/src l0c`.
3. Verify that a built `l0c-stage2` can
   `--build --keep-c -P compiler/stage2_l0/src -o <tmp>/l0c-stage2-second.native l0c`.
4. Verify that the second self-built compiler can
   `--build --keep-c -P compiler/stage2_l0/src -o <tmp>/l0c-stage2-third.native l0c`.
5. Run `compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py` and require:
   1. the second-build retained C artifact matches the third-build retained C artifact exactly
   2. the second-build native compiler binary matches the third-build native compiler binary exactly on stable host
      toolchains, and is skipped for `tcc`
   3. the third self-built compiler passes a direct smoke check
   4. all artifacts stay under `build/tests/...`
6. Run `./compiler/stage2_l0/run_tests.py` to confirm the new triple-bootstrap regression integrates cleanly with the
   Stage 2 suite.

## Assumptions and Defaults

1. The triple-bootstrap plan is a separate feature plan, not a rewrite of the existing bootstrap/install plan.
2. The final comparison is intentionally strict: retained C must match byte-for-byte on every supported host compiler,
   and native compiler binaries must also match byte-for-byte on stable host toolchains.
3. Wrapper scripts are not part of the identity comparison.
4. The preferred new test implementation language is Python, not shell, to keep the comparison/reporting logic
   structured and portable.
5. Deterministic linker flags are required for native comparison; `tcc` is a documented exception that currently skips
   native-binary identity while still requiring retained-C identity.
