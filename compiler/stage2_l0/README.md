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

Phase 1 `DIST_DIR` values must resolve inside the repository. The generated launcher derives the repo root relative to
itself and sets `L0_HOME` automatically when unset.

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
./l0c -P compiler/stage2_l0/src --run --trace-arc --trace-memory compiler/stage2_l0/tests/parser_test.l0
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
