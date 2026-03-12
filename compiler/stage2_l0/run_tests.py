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
from pathlib import Path
import sys

from test_runner_common import (
    build_normal_test_env,
    TestCase,
    build_normal_test_command,
    discover_stage2_tests,
    print_output_block,
    require_repo_stage2_test_env,
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


def run_one(case: TestCase, python_path: str, repo_env: dict[str, str]) -> TestResult:
    """Run one Stage 2 test case."""

    completed = run_combined_output(
        build_normal_test_command(case, Path(python_path)),
        env=build_normal_test_env(case, repo_env),
    )
    return TestResult(
        case=case,
        returncode=completed.returncode,
        output=completed.output,
    )


def submission_priority(case: TestCase) -> tuple[int, int]:
    """Return the executor submission priority for one Stage 2 test case."""

    # Start the slow triple-bootstrap regression immediately to reduce overall wall time,
    # while preserving the normal discovery order for printed output.
    if case.name == "l0c_triple_bootstrap_test.py":
        return (0, case.index)
    return (1, case.index)


def main() -> int:
    """Program entrypoint."""

    args = parse_args()

    try:
        jobs = resolve_job_count()
    except ValueError as exc:
        print(f"run_tests.py: {exc}", file=sys.stderr)
        return 2
    try:
        python_path, _, _, repo_env = require_repo_stage2_test_env("run_tests.py")
    except RuntimeError as exc:
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

    scheduled_cases = sorted(cases, key=submission_priority)

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        future_map = {
            executor.submit(run_one, case, str(python_path), repo_env): case.index
            for case in scheduled_cases
        }
        for future in as_completed(future_map):
            result = future.result()
            emit(result)

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
