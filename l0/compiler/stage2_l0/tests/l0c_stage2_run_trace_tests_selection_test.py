#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Regression coverage for Stage 2 `run_trace_tests.py` selection helpers."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
RUNNER_DIR = SCRIPT_DIR.parent / "scripts"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

import run_tests
import run_trace_tests
from test_runner_common import TestCase


def fail(message: str) -> int:
    """Print one failure and return the shell-style exit code."""

    print(f"l0c_stage2_run_trace_tests_selection_test: FAIL: {message}")
    return 1


def test_parse_args_accepts_optional_test_names() -> str | None:
    """Return one failure message, or `None` when CLI parsing keeps trace selectors."""

    original_argv = sys.argv[:]
    sys.argv = [
        "run_trace_tests.py",
        "--max-details",
        "7",
        "l0c_lib_test",
        "type_resolve_test.l0",
    ]
    try:
        args = run_trace_tests.parse_args()
    finally:
        sys.argv = original_argv

    if args.max_details != 7:
        return f"expected --max-details to parse as 7, got {args.max_details!r}"
    if args.tests != ["l0c_lib_test", "type_resolve_test.l0"]:
        return f"unexpected parsed trace test selectors: {args.tests!r}"
    return None


def test_trace_selection_supports_optional_extensions() -> str | None:
    """Return one failure message, or `None` when trace selectors preserve discovery order."""

    cases = [
        TestCase(index=0, name="analysis_test", path=SCRIPT_DIR / "analysis_test.l0", kind="l0"),
        TestCase(index=1, name="l0c_lib_test", path=SCRIPT_DIR / "l0c_lib_test.l0", kind="l0"),
        TestCase(index=2, name="type_resolve_test", path=SCRIPT_DIR / "type_resolve_test.l0", kind="l0"),
    ]

    selected = run_tests.select_cases(cases, ["type_resolve_test.l0", "analysis_test"])
    actual = [case.path.name for case in selected]
    expected = ["analysis_test.l0", "type_resolve_test.l0"]
    if actual != expected:
        return f"expected trace selection to preserve discovery order, got {actual!r}"
    return None


def main() -> int:
    """Program entrypoint."""

    checks = [
        test_parse_args_accepts_optional_test_names,
        test_trace_selection_supports_optional_extensions,
    ]
    for check in checks:
        message = check()
        if message is not None:
            return fail(message)

    print("l0c_stage2_run_trace_tests_selection_test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
