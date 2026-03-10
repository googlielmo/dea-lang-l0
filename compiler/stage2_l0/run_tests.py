#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Run all Stage 2 tests under `compiler/stage2_l0/tests/`."""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import sys

from test_runner_common import (
    TestCase,
    build_normal_test_command,
    discover_stage2_tests,
    print_output_block,
    resolve_job_count,
    run_combined_output,
    summarize_failures,
)


@dataclass(frozen=True)
class TestResult:
    """One completed Stage 2 test result."""

    case: TestCase
    returncode: int
    output: str


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Run Stage 2 L0 tests.",
        epilog="Parallelism defaults to a bounded auto-detected worker count. Override with L0_TEST_JOBS=<n>.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show output for every test.",
    )
    return parser.parse_args()


def run_one(case: TestCase) -> TestResult:
    """Run one Stage 2 test case."""

    completed = run_combined_output(build_normal_test_command(case))
    return TestResult(
        case=case,
        returncode=completed.returncode,
        output=completed.output,
    )


def main() -> int:
    """Program entrypoint."""

    args = parse_args()

    try:
        jobs = resolve_job_count()
    except ValueError as exc:
        print(f"run_tests.py: {exc}", file=sys.stderr)
        return 2

    cases = discover_stage2_tests()
    if not cases:
        print("No tests found in compiler/stage2_l0/tests")
        return 0

    print("Running stage2_l0 tests...")
    print(f"Parallel jobs: {jobs}")
    print("======================================")

    passed = 0
    failures: list[TestResult] = []
    ready: dict[int, TestResult] = {}
    next_index = 0

    def emit(result: TestResult) -> None:
        nonlocal passed

        status = "PASS" if result.returncode == 0 else "FAIL"
        if args.verbose:
            print(f"Running {result.case.name}...")
            print_output_block(result.output)
            print(status)
        else:
            print(f"Running {result.case.name}... {status}")

        if result.returncode == 0:
            passed += 1
        else:
            failures.append(result)

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        future_map = {executor.submit(run_one, case): case.index for case in cases}
        for future in as_completed(future_map):
            result = future.result()
            ready[result.case.index] = result

            while next_index in ready:
                emit(ready.pop(next_index))
                next_index += 1

    if not args.verbose and failures:
        print("======================================")
        print("Failed test outputs:")
        for result in failures:
            print(f"Output for {result.case.name}:")
            print_output_block(result.output)
            print("--------------------------------------")

    print("======================================")
    print(f"Passed: {passed}")
    print(f"Failed: {len(failures)}")

    if failures:
        print(f"Failed tests: {summarize_failures(result.case for result in failures)}")
        return 1

    print("All tests passed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
