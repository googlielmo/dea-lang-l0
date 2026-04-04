#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Regression coverage for Stage 2 `run_tests.py` selection and timing helpers."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
RUNNER_DIR = SCRIPT_DIR.parent / "scripts"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

import run_tests
from test_runner_common import TestCase


def fail(message: str) -> int:
    """Print one failure and return the shell-style exit code."""

    print(f"l0c_stage2_run_tests_selection_test: FAIL: {message}")
    return 1


def test_select_cases_supports_optional_extensions() -> str | None:
    """Return one failure message, or `None` when selection works."""

    cases = [
        TestCase(index=0, name="driver_test", path=SCRIPT_DIR / "driver_test.l0", kind="l0"),
        TestCase(index=1, name="l0c_build_run_test.sh", path=SCRIPT_DIR / "l0c_build_run_test.sh", kind="shell"),
        TestCase(index=2, name="demo_trace_test.py", path=SCRIPT_DIR / "demo_trace_test.py", kind="python"),
    ]

    selected = run_tests.select_cases(
        cases,
        ["driver_test", "l0c_build_run_test", "demo_trace_test.py"],
    )
    expected = ["driver_test.l0", "l0c_build_run_test.sh", "demo_trace_test.py"]
    actual = [case.path.name for case in selected]
    if actual != expected:
        return f"expected optional-extension selection to preserve discovery order, got {actual!r}"
    indexes = [case.index for case in selected]
    if indexes != [0, 1, 2]:
        return f"expected selected cases to be reindexed contiguously, got {indexes!r}"
    return None


def test_select_cases_reports_unknown_names() -> str | None:
    """Return one failure message, or `None` when unknown-name errors are descriptive."""

    cases = [TestCase(index=0, name="driver_test", path=SCRIPT_DIR / "driver_test.l0", kind="l0")]

    try:
        run_tests.select_cases(cases, ["missing_test"])
    except ValueError as exc:
        if "unknown Stage 2 test name(s): missing_test" not in str(exc):
            return f"unexpected unknown-name error text: {exc}"
        return None
    return "expected unknown selector to raise ValueError"


def test_select_cases_reports_ambiguous_stems() -> str | None:
    """Return one failure message, or `None` when ambiguous stem errors are descriptive."""

    cases = [
        TestCase(index=0, name="dup_test.sh", path=SCRIPT_DIR / "dup_test.sh", kind="shell"),
        TestCase(index=1, name="dup_test.py", path=SCRIPT_DIR / "dup_test.py", kind="python"),
    ]

    try:
        run_tests.select_cases(cases, ["dup_test"])
    except ValueError as exc:
        text = str(exc)
        if "ambiguous Stage 2 test name(s): dup_test: dup_test.sh, dup_test.py" not in text:
            return f"unexpected ambiguous-selector error text: {exc}"
        return None
    return "expected ambiguous selector to raise ValueError"


def test_result_status_line_includes_elapsed_time() -> str | None:
    """Return one failure message, or `None` when status formatting includes wall time."""

    case = TestCase(index=0, name="driver_test", path=SCRIPT_DIR / "driver_test.l0", kind="l0")
    result = run_tests.TestResult(case=case, returncode=0, output="", elapsed_seconds=1.2344)
    line = run_tests.result_status_line(result)
    if line != "Running driver_test... PASS (1.234s)":
        return f"unexpected PASS status line: {line!r}"

    failed = run_tests.TestResult(case=case, returncode=1, output="", elapsed_seconds=0.25)
    failed_line = run_tests.result_status_line(failed)
    if failed_line != "Running driver_test... FAIL (0.250s)":
        return f"unexpected FAIL status line: {failed_line!r}"
    return None


def main() -> int:
    """Program entrypoint."""

    checks = [
        test_select_cases_supports_optional_extensions,
        test_select_cases_reports_unknown_names,
        test_select_cases_reports_ambiguous_stems,
        test_result_status_line_includes_elapsed_time,
    ]
    for check in checks:
        message = check()
        if message is not None:
            return fail(message)

    print("l0c_stage2_run_tests_selection_test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
