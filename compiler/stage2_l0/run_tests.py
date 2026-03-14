#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Run Stage 2 tests under `compiler/stage2_l0/tests/`."""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from pathlib import Path
import sys
from time import perf_counter

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
    elapsed_seconds: float


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
    parser.add_argument(
        "tests",
        nargs="*",
        metavar="TEST",
        help="Optional Stage 2 test name(s) to run. Match `tests/` file names exactly or omit the extension.",
    )
    return parser.parse_args()


def run_one(case: TestCase, python_path: str, repo_env: dict[str, str]) -> TestResult:
    """Run one Stage 2 test case."""

    started_at = perf_counter()
    completed = run_combined_output(
        build_normal_test_command(case, Path(python_path)),
        env=build_normal_test_env(case, repo_env),
    )
    return TestResult(
        case=case,
        returncode=completed.returncode,
        output=completed.output,
        elapsed_seconds=perf_counter() - started_at,
    )


def format_elapsed_seconds(seconds: float) -> str:
    """Return one human-readable wall-clock duration."""

    return f"{seconds:.3f}s"


def result_status_line(result: TestResult) -> str:
    """Return the one-line PASS/FAIL status for one completed test."""

    status = "PASS" if result.returncode == 0 else "FAIL"
    return f"Running {result.case.name}... {status} ({format_elapsed_seconds(result.elapsed_seconds)})"


def select_cases(cases: list[TestCase], requested: list[str]) -> list[TestCase]:
    """Return the selected Stage 2 cases for optional CLI test-name filters."""

    if not requested:
        return cases

    by_path_name = {case.path.name: case for case in cases}
    by_stem: dict[str, list[TestCase]] = {}
    for case in cases:
        by_stem.setdefault(case.path.stem, []).append(case)

    selected_indexes: set[int] = set()
    missing: list[str] = []
    ambiguous: list[str] = []

    for raw_name in requested:
        selector = Path(raw_name).name
        exact = by_path_name.get(selector)
        if exact is not None:
            selected_indexes.add(exact.index)
            continue

        selector_path = Path(selector)
        if selector_path.suffix:
            missing.append(selector)
            continue

        matches = by_stem.get(selector, [])
        if not matches:
            missing.append(selector)
            continue
        if len(matches) > 1:
            ambiguous.append(
                f"{selector}: {', '.join(case.path.name for case in matches)}"
            )
            continue
        selected_indexes.add(matches[0].index)

    if missing or ambiguous:
        parts: list[str] = []
        if missing:
            parts.append(f"unknown Stage 2 test name(s): {' '.join(missing)}")
        if ambiguous:
            parts.append(f"ambiguous Stage 2 test name(s): {'; '.join(ambiguous)}")
        raise ValueError("; ".join(parts))

    return [case for case in cases if case.index in selected_indexes]


def submission_priority(case: TestCase) -> tuple[int, int]:
    """Return the executor submission priority for one Stage 2 test case."""

    # Start the slow triple-bootstrap regression immediately to reduce overall wall time,
    # while preserving the normal discovery order for printed output.
    if case.name == "l0c_triple_bootstrap_test.py":
        return (0, case.index)
    return (1, case.index)


def main() -> int:
    """Program entrypoint."""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    args = parse_args()

    try:
        jobs = resolve_job_count()
    except ValueError as exc:
        print(f"run_tests.py: {exc}", file=sys.stderr, flush=True)
        return 2
    try:
        python_path, _, _, repo_env = require_repo_stage2_test_env("run_tests.py")
    except RuntimeError as exc:
        print(f"run_tests.py: {exc}", file=sys.stderr, flush=True)
        return 2

    try:
        cases = select_cases(discover_stage2_tests(), args.tests)
    except ValueError as exc:
        print(f"run_tests.py: {exc}", file=sys.stderr, flush=True)
        return 2
    if not cases:
        print("No tests found in compiler/stage2_l0/tests", flush=True)
        return 0

    print("Running stage2_l0 tests...", flush=True)
    print(f"Parallel jobs: {jobs}", flush=True)
    print("======================================", flush=True)

    passed = 0
    failures: list[TestResult] = []

    def emit(result: TestResult) -> None:
        nonlocal passed

        if args.verbose:
            print(f"Running {result.case.name}...", flush=True)
            print_output_block(result.output)
            sys.stdout.flush()
            print(
                f"{'PASS' if result.returncode == 0 else 'FAIL'} ({format_elapsed_seconds(result.elapsed_seconds)})",
                flush=True,
            )
        else:
            print(result_status_line(result), flush=True)

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
        print("======================================", flush=True)
        print("Failed test outputs:", flush=True)
        for result in failures:
            print(
                f"Output for {result.case.name} ({format_elapsed_seconds(result.elapsed_seconds)}):",
                flush=True,
            )
            print_output_block(result.output)
            sys.stdout.flush()
            print("--------------------------------------", flush=True)

    print("======================================", flush=True)
    print(f"Passed: {passed}", flush=True)
    print(f"Failed: {len(failures)}", flush=True)

    if failures:
        print(f"Failed tests: {summarize_failures(result.case for result in failures)}", flush=True)
        return 1

    print("All tests passed!", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
