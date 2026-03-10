#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Shared helpers for Stage 2 test runners."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import os
import subprocess
import sys

DEFAULT_MAX_JOBS = 9
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
TESTS_DIR = SCRIPT_DIR / "tests"


@dataclass(frozen=True)
class TestCase:
    """One discovered Stage 2 test case."""

    index: int
    name: str
    path: Path
    kind: str


@dataclass(frozen=True)
class CommandResult:
    """Captured subprocess result."""

    returncode: int
    output: str


def discover_l0_tests() -> list[TestCase]:
    """Return discovered `.l0` Stage 2 tests in deterministic order."""

    return [
        TestCase(index=index, name=path.stem, path=path, kind="l0")
        for index, path in enumerate(sorted(TESTS_DIR.glob("*.l0")))
    ]


def discover_stage2_tests() -> list[TestCase]:
    """Return discovered Stage 2 test cases in deterministic order."""

    cases: list[TestCase] = []
    index = 0

    for path in sorted(TESTS_DIR.glob("*.l0")):
        cases.append(TestCase(index=index, name=path.stem, path=path, kind="l0"))
        index += 1

    for path in sorted(TESTS_DIR.glob("*_test.sh")):
        cases.append(TestCase(index=index, name=path.name, path=path, kind="shell"))
        index += 1

    for path in sorted(TESTS_DIR.glob("*_test.py")):
        cases.append(TestCase(index=index, name=path.name, path=path, kind="python"))
        index += 1

    return cases


def resolve_job_count() -> int:
    """Return the worker count for the normal Stage 2 test runner."""

    jobs_text = os.environ.get("L0_TEST_JOBS", "").strip()
    if jobs_text:
        try:
            jobs = int(jobs_text)
        except ValueError as exc:
            raise ValueError(f"L0_TEST_JOBS must be a positive integer, got {jobs_text!r}") from exc
        if jobs < 1:
            raise ValueError(f"L0_TEST_JOBS must be a positive integer, got {jobs_text!r}")
        return jobs

    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count, DEFAULT_MAX_JOBS))


def build_normal_test_command(case: TestCase) -> list[str]:
    """Return the subprocess command for one normal Stage 2 test."""

    if case.kind == "l0":
        return ["./l0c", "-P", "compiler/stage2_l0/src", "--run", str(case.path)]
    if case.kind == "shell":
        return ["bash", str(case.path)]
    if case.kind == "python":
        return [sys.executable, str(case.path)]
    raise ValueError(f"Unsupported test kind: {case.kind}")


def run_combined_output(command: list[str]) -> CommandResult:
    """Run one subprocess and capture stdout/stderr as one stream."""

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return CommandResult(returncode=completed.returncode, output=completed.stdout)


def print_output_block(text: str) -> None:
    """Print captured output without losing the final line."""

    if not text:
        return

    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")


def first_lines(text: str, limit: int) -> str:
    """Return at most `limit` lines from `text`."""

    lines = text.splitlines()
    if len(lines) <= limit:
        return text
    return "\n".join(lines[:limit]) + "\n"


def summarize_failures(results: Iterable[TestCase]) -> str:
    """Return a stable one-line failed-test summary."""

    names = [result.name for result in results]
    if not names:
        return ""
    return " ".join(names)
