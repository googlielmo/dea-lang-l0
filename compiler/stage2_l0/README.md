# Stage 2 Dea/L0 Language Compiler

This directory contains the self-hosted Stage 2 compiler for the L0 programming language. It includes source code,
tests, and utilities for the compiler and its runtime traces.

Like the Stage 1 compiler, it compiles L0 source code to C99, but is itself implemented in L0. Stage 2 implements the
full current public CLI surface: `--check`, `--tok`, `--sym`, `--type`, `--ast`, `--gen`, `--build`, and `--run`.

## Bootstrap artifact

Build a repo-local Stage 2 compiler artifact:

```bash
./scripts/build-stage2-l0c.sh
./build/dea/bin/l0c-stage2 --check -P examples hello
./build/dea/bin/l0c-stage2 --gen -P examples hello
./build/dea/bin/l0c-stage2 --build -P examples hello
./build/dea/bin/l0c-stage2 --run -P examples hello
```

Optional builder environment variables:

- `DEA_BUILD_DIR=build/dea-alt` writes the same artifact layout under a different repo-local output root.
- `KEEP_C=1` retains `l0c-stage2.c` alongside the wrapper and native binary.

`DEA_BUILD_DIR` values must resolve to a subdirectory inside the repository. The generated launcher derives the repo
root relative to itself and sets `L0_HOME` automatically when unset.

## Repo-local Dea build workflow

For normal development, install both stage-specific launchers under `build/dea/bin`, then select which one `l0c` should
point at:

```bash
make install-dev-stages
make use-dev-stage2      # or: make use-dev-stage1
source build/dea/bin/l0-env.sh
l0c --check -P examples hello
l0c --version
```

The generated `build/dea/bin/l0-env.sh` keeps `L0_HOME` repo-relative, activates `.venv` if present, prepends
`build/dea/bin` to `PATH`, and leaves `L0_SYSTEM` unset.

The `make use-*` targets switch `build/dea/bin/l0c` and print the `source` command to run next.

## Install prefix

Install a repo-independent Stage 2 toolchain under one prefix:

```bash
make PREFIX=/tmp/l0-install install
source /tmp/l0-install/bin/l0-env.sh
l0c --check -P examples hello
```

`make install` requires an explicit `PREFIX=...`; there is no implicit default install root.

To package the same relocatable layout into a temporary distribution tree and archive:

```bash
make dist
```

`make dist` creates `build/.../dea-l0` and archives it as `dea-l0-lang_<os>-<arch>_YYYYMMDD-HHMMSS.tar.gz` on POSIX
hosts or `dea-l0-lang_<os>-<arch>_YYYYMMDD-HHMMSS.zip` on Windows, using the lower-case OS/architecture from the
recorded build host plus the UTC build timestamp in the archive name.

If a repo-root `VERSION` file exists when `make dist` runs, it is copied into the top level of the packaged `dea-l0/`
tree. The file should contain the release version string without a leading `v`. `make dist` also defaults `L0_CFLAGS` to
`-O2` unless you override it explicitly on the command line.

`install` installs the self-hosted Stage 2 compiler (`Compiler 2` from the triple-bootstrap chain), not the initial
Stage 1-built artifact. The installed prefix contains:

- `bin/l0c-stage2`
- `bin/l0c-stage2.native`
- `bin/l0c`
- `bin/l0-env.sh`
- `shared/l0/stdlib/...`
- `shared/runtime/...`

The installed wrapper derives `L0_HOME` from `PREFIX` at runtime. The installed `l0-env.sh` sets `L0_HOME="$PREFIX"`
only; the compiler then derives stdlib and runtime defaults from `L0_HOME` unless you explicitly override them.

The full CLI contract — mode flags, options, identity strings, `--version` provenance, and exit codes — is documented in
`docs/specs/compiler/cli-contract.md`.

The source-tree `./scripts/l0c` entrypoint is Stage 1 only and is mainly useful for bootstrap mechanics, internal
tooling, and Stage 1-focused testing.

## Running tests

Run Stage 2 L0 tests:

```bash
make DEA_BUILD_DIR=build/dev-dea test-stage2
make DEA_BUILD_DIR=build/dev-dea test-stage2 TESTS="driver_test l0c_build_run_test"
make DEA_BUILD_DIR=build/dev-dea test-stage2-trace
make DEA_BUILD_DIR=build/dev-dea triple-test
```

These Make targets are self-contained repo-local workflows: they ensure `./.venv`, prepare the Stage 2 artifact under
`DEA_BUILD_DIR`, and scrub installed-prefix `L0_*` env leakage before running.

`make test-stage2` also accepts `TESTS="..."`. Leave it blank to run the full suite; otherwise pass one or more Stage 2
test names separated by spaces, using either the exact file name or the extensionless stem.

If you invoke the Python helpers directly instead, prepare the repo-local env first:

```bash
make venv
make DEA_BUILD_DIR=build/dev-dea install-dev-stage2
./.venv/bin/python ./compiler/stage2_l0/run_tests.py
./.venv/bin/python ./compiler/stage2_l0/run_trace_tests.py
./.venv/bin/python ./compiler/stage2_l0/run_test_trace.py parser_test
./.venv/bin/python ./compiler/stage2_l0/run_tests.py driver_test l0c_build_run_test
```

`run_tests.py` executes `*.l0` test modules plus `*_test.sh` and `*_test.py` regression scripts under
`compiler/stage2_l0/tests/`. Pass optional positional test names to run only those cases; match either the exact file
name or omit the extension (for example `driver_test` or `l0c_build_run_test.sh`). It uses a bounded auto-detected
worker count by default; override with `L0_TEST_JOBS=<n>`.

Options:

- `-v`: verbose output with all test names and outputs.
- `TEST ...`: optional Stage 2 test names to run instead of the full suite.

Output:

- Per-test `PASS`/`FAIL` lines include wall-clock runtime, followed by the usual summary and any failure output blocks.
- Exit code: `0` if all tests pass, `1` if any test fails.

### Triple-bootstrap regression

Run the strict triple-bootstrap / triple-compilation regression directly from the repo root:

```bash
make DEA_BUILD_DIR=build/dev-dea triple-test
./.venv/bin/python compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py
```

Useful environment overrides:

- `KEEP_ARTIFACTS=1` keeps the generated temp directory under `build/tests/l0_stage2_triple_bootstrap.*` for inspection.
- `L0_CC=<compiler>` pins the exact host C compiler used for all self-builds.
- `L0_CFLAGS="..."` appends extra C compiler flags; the test still adds deterministic linker flags required for native
  identity checks.
- When `L0_CC` resolves to `tcc`, the test still compares retained C outputs but skips the native-binary identity check
  because `tcc` does not currently guarantee stable binaries across identical builds.

Examples:

```bash
KEEP_ARTIFACTS=1 python3 compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py
L0_CC=clang KEEP_ARTIFACTS=1 python3 compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py
```

The test performs, in order:

1. trusted Stage 1 → first Stage 2 build with retained C enabled
2. first Stage 2 compiler → second self-built Stage 2 compiler
3. second self-built Stage 2 compiler → third self-built Stage 2 compiler
4. byte-for-byte comparison of second-build vs third-build retained C
5. byte-for-byte comparison of second-build vs third-build native compiler binaries, unless the host compiler is `tcc`
6. smoke run through the third self-built compiler

On Linux, the native identity step compares stripped binaries. Raw ELF outputs can differ across identical builds when
the retained C source path changes, even after disabling the linker build ID. Stripping preserves the meaningful native
code / link-result comparison while ignoring filename-sensitive metadata.

If you want to run the same flow manually step by step, keep one compiler and one flag set for both builds:

```bash
export L0_CC=clang
export L0_CFLAGS="-Wl,-no_uuid"         # macOS
# export L0_CFLAGS="-Wl,--build-id=none"  # Linux

DEA_BUILD_DIR=build/tests/triple-manual KEEP_C=1 ./scripts/build-stage2-l0c.sh
L0_HOME="$PWD/compiler" ./build/tests/triple-manual/bin/l0c-stage2 --build --keep-c -P compiler/stage2_l0/src -o build/tests/triple-manual/l0c-stage2-second.native l0c
L0_HOME="$PWD/compiler" ./build/tests/triple-manual/l0c-stage2-second.native --build --keep-c -P compiler/stage2_l0/src -o build/tests/triple-manual/l0c-stage2-third.native l0c
cmp build/tests/triple-manual/l0c-stage2-second.c build/tests/triple-manual/l0c-stage2-third.c
strip -s -o build/tests/triple-manual/l0c-stage2-second.stripped build/tests/triple-manual/l0c-stage2-second.native
strip -s -o build/tests/triple-manual/l0c-stage2-third.stripped build/tests/triple-manual/l0c-stage2-third.native
cmp build/tests/triple-manual/l0c-stage2-second.stripped build/tests/triple-manual/l0c-stage2-third.stripped
L0_HOME="$PWD/compiler" ./build/tests/triple-manual/l0c-stage2-third.native --run -P examples hello
```

When the host compiler is `tcc`, keep the retained-C comparison but skip the native-binary `cmp` step above.

Expected smoke output:

```text
Hello, World!
```

Run Stage 2 L0 trace checks (runtime + leak triage on every test):

```bash
./compiler/stage2_l0/run_trace_tests.py
```

This runner also uses a bounded auto-detected worker count by default; override with `L0_TEST_JOBS=<n>`.

Options:

- `-v`: print per-test analyzer details.
- `--keep-artifacts`: keep stdout/stderr/report files under `/tmp`.
- `--max-details <n>`: pass through to `check_trace_log.py` detail limit.

Output:

- Per-test `TRACE_OK`/`TRACE_FAIL`/`RUN_FAIL`.
- Leak summary fields from analyzer (`leaked_object_ptrs`, `leaked_string_ptrs`).
- Exit code: `0` if all trace checks pass, `1` if any test fails or has trace errors.

## Trace test runs

Capture Stage 2 trace logs (both ARC and memory) for a Stage 2 test:

```bash
./compiler/stage2_l0/run_test_trace.py parser_test
```

The test argument accepts either `parser_test` or `parser_test.l0`.

This runs:

```bash
./scripts/l0c -P compiler/stage2_l0/src --run --trace-arc --trace-memory compiler/stage2_l0/tests/parser_test.l0
```

By default, output files are written under `/tmp` and printed at the end:

- `trace_stderr=...` (runtime trace lines, including `[l0][arc]` and `[l0][mem]`)
- `trace_stdout=...`
- `exit_code=...`

Custom output paths:

```bash
./compiler/stage2_l0/run_test_trace.py \
  parser_test \
  --out /tmp/parser.stderr.log \
  --stdout /tmp/parser.stdout.log
```

## Check trace logs

Analyze a captured trace log and detect definite issues (leaks, malformed critical events, panic traces):

```bash
./compiler/stage2_l0/check_trace_log.py /tmp/parser.stderr.log
```

Triage and detail controls:

```bash
./compiler/stage2_l0/check_trace_log.py /tmp/parser.stderr.log --triage --max-details 100
```

Exit codes:

- `0`: no definite problems detected
- `1`: definite runtime/trace problems found
- `2`: usage or input-file error
