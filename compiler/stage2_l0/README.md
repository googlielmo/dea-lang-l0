# Stage 2 Dea/L0 Language Compiler

This directory contains the Stage 2 compiler for the L0 programming language, currently in development.
It includes source code, tests, and utilities for the compiler and its runtime traces.

Like the Stage 1 compiler, it compiles L0 source code to C99, but is itself implemented in L0.

## Bootstrap artifact

Build a repo-local Stage 2 compiler artifact:

```bash
./scripts/build-stage2-l0c.sh
./build/stage2/bin/l0c-stage2 --check -P examples hello
./build/stage2/bin/l0c-stage2 --gen -P examples hello
./build/stage2/bin/l0c-stage2 --build -P examples hello
./build/stage2/bin/l0c-stage2 --run -P examples hello
```

Optional builder environment variables:

- `DIST_DIR=build/stage2-alt` writes the same artifact layout under a different repo-local output root.
- `KEEP_C=1` retains `l0c-stage2.c` alongside the wrapper and native binary.

Phase 1 `DIST_DIR` values must resolve to a strict subdirectory inside the repository. The generated launcher derives
the repo root relative to itself and sets `L0_HOME` automatically when unset.

## Repo-local dist workflow

For normal development, install both stage-specific launchers under `dist/bin`, then select which one `l0c` should
point at:

```bash
make install-dev-stages
make use-dev-stage1      # or: make use-dev-stage2
source dist/bin/l0-env.sh
l0c --check -P examples hello
l0c --version
```

The generated `dist/bin/l0-env.sh` keeps `L0_HOME` repo-relative, activates `.venv` if present, prepends `dist/bin`
to `PATH`, and leaves `L0_SYSTEM` unset. `make use-dev-stage2` switches `dist/bin/l0c` and prints the exact `source`
command to run next. `DIST_DIR` may be overridden, but it must remain inside the repository.

The Stage 2 CLI also supports `--help` and `--version`. Both show the Stage 2 identity text
`Dea language / L0 compiler (Stage 2)`. Verbose mode (`-v`) emits the same identity line on stderr through the normal
info-level log path, including CLI usage failures such as `l0c -v` without a target.

The source-tree `./scripts/l0c` entrypoint is Stage 1 only and is mainly useful for bootstrap mechanics, internal
tooling, and Stage 1-focused testing.

## Running tests

Run Stage 2 L0 tests:

```bash
./compiler/stage2_l0/run_tests.py
```

This runner executes `*.l0` test modules plus `*_test.sh` and `*_test.py` regression scripts under
`compiler/stage2_l0/tests/`.
It uses a bounded auto-detected worker count by default; override with `L0_TEST_JOBS=<n>`.

Options:

- `-v`: verbose output with all test names and outputs.

Output:

- Summary of test results (total, passed, failed) and details for any failures.
- Exit code: `0` if all tests pass, `1` if any test fails.

### Triple-bootstrap regression

Run the strict triple-bootstrap / triple-compilation regression directly from the repo root:

```bash
make triple-test
python3 compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py
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

1. trusted Stage 1 -> first Stage 2 build with retained C enabled
2. first Stage 2 compiler -> second self-built Stage 2 compiler
3. second self-built Stage 2 compiler -> third self-built Stage 2 compiler
4. byte-for-byte comparison of second-build vs third-build retained C
5. byte-for-byte comparison of second-build vs third-build native compiler binaries, unless the host compiler is `tcc`
6. smoke run through the third self-built compiler

If you want to run the same flow manually step by step, keep one compiler and one flag set for both builds:

```bash
export L0_CC=clang
export L0_CFLAGS="-Wl,-no_uuid"         # macOS
# export L0_CFLAGS="-Wl,--build-id=none"  # Linux

DIST_DIR=build/tests/triple-manual KEEP_C=1 ./scripts/build-stage2-l0c.sh
L0_HOME="$PWD/compiler" ./build/tests/triple-manual/bin/l0c-stage2 --build --keep-c -P compiler/stage2_l0/src -o build/tests/triple-manual/l0c-stage2-second.native l0c
L0_HOME="$PWD/compiler" ./build/tests/triple-manual/l0c-stage2-second.native --build --keep-c -P compiler/stage2_l0/src -o build/tests/triple-manual/l0c-stage2-third.native l0c
cmp build/tests/triple-manual/l0c-stage2-second.c build/tests/triple-manual/l0c-stage2-third.c
cmp build/tests/triple-manual/l0c-stage2-second.native build/tests/triple-manual/l0c-stage2-third.native
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
