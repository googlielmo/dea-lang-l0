#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Run Stage 2 trace checks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from test_runner_common import REPO_ROOT, SCRIPT_DIR, discover_l0_tests, first_lines, resolve_job_count

TRACE_CHECKER = SCRIPT_DIR / "check_trace_log.py"


@dataclass(frozen=True)
class TraceResult:
    """One completed trace test result."""

    case_index: int
    case_name: str
    status: str
    report_text: str
    trace_text: str
    summary: str


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Run Stage 2 ARC/memory trace checks.",
        epilog="Parallelism defaults to a bounded auto-detected worker count. Override with L0_TEST_JOBS=<n>.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show analyzer details for each test.")
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep trace/stdout/report files under the temp directory.",
    )
    parser.add_argument(
        "--max-details",
        type=int,
        default=5,
        help="Pass through to check_trace_log.py detail limit (default: 5).",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    """Read one text file with replacement for invalid bytes."""

    return path.read_text(encoding="utf-8", errors="replace")


def leak_summary(report_text: str) -> str:
    """Return the leak summary fields from one trace report."""

    fields: list[str] = []
    for line in report_text.splitlines():
        if line.startswith("leaked_object_ptrs=") or line.startswith("leaked_string_ptrs="):
            fields.append(line)
    if not fields:
        return ""
    return " ".join(fields)


def run_one(case_index: int, case_name: str, case_path: Path, artifact_dir: Path, max_details: int) -> TraceResult:
    """Run one trace test and analyze its log."""

    out_path = artifact_dir / f"{case_name}.stdout.log"
    trace_path = artifact_dir / f"{case_name}.stderr.log"
    report_path = artifact_dir / f"{case_name}.trace_report.txt"

    with out_path.open("w", encoding="utf-8") as stdout_file, trace_path.open("w", encoding="utf-8") as stderr_file:
        run_result = subprocess.run(
            [
                "./scripts/l0c",
                "--trace-memory",
                "--trace-arc",
                "-P",
                "compiler/stage2_l0/src",
                "--run",
                str(case_path),
            ],
            cwd=REPO_ROOT,
            stdout=stdout_file,
            stderr=stderr_file,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    trace_text = read_text(trace_path)
    if run_result.returncode != 0:
        return TraceResult(
            case_index=case_index,
            case_name=case_name,
            status="RUN_FAIL",
            report_text="",
            trace_text=trace_text,
            summary="",
        )

    with report_path.open("w", encoding="utf-8") as report_file:
        analyzer_result = subprocess.run(
            [
                sys.executable,
                str(TRACE_CHECKER),
                str(trace_path),
                "--triage",
                "--max-details",
                str(max_details),
            ],
            cwd=REPO_ROOT,
            stdout=report_file,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    report_text = read_text(report_path)
    if analyzer_result.returncode == 0:
        return TraceResult(
            case_index=case_index,
            case_name=case_name,
            status="TRACE_OK",
            report_text=report_text,
            trace_text=trace_text,
            summary=leak_summary(report_text),
        )

    return TraceResult(
        case_index=case_index,
        case_name=case_name,
        status="TRACE_FAIL",
        report_text=report_text,
        trace_text=trace_text,
        summary="",
    )


def main() -> int:
    """Program entrypoint."""

    args = parse_args()
    try:
        jobs = resolve_job_count()
    except ValueError as exc:
        print(f"run_trace_tests.py: {exc}", file=sys.stderr)
        return 2

    cases = discover_l0_tests()
    if not cases:
        print("No tests found in compiler/stage2_l0/tests")
        return 0

    artifact_dir = Path(tempfile.mkdtemp(prefix="l0_stage2_trace_tests."))
    keep_artifacts = args.keep_artifacts
    failed_names: list[str] = []
    passed = 0

    try:
        print("Running stage2_l0 trace checks...")
        print(f"artifacts={artifact_dir}")
        print(f"Parallel jobs: {jobs}")
        print("======================================")

        ready: dict[int, TraceResult] = {}
        next_index = 0

        def emit(result: TraceResult) -> None:
            nonlocal passed

            suffix = f" {result.summary}" if result.summary else ""
            print(f"{result.case_name}: {result.status}{suffix}")

            if result.status == "TRACE_OK":
                passed += 1
                if args.verbose:
                    sys.stdout.write(first_lines(result.report_text, 80))
                    if result.report_text and not result.report_text.endswith("\n"):
                        sys.stdout.write("\n")
                return

            failed_names.append(result.case_name)
            if args.verbose:
                detail_text = result.trace_text if result.status == "RUN_FAIL" else result.report_text
                sys.stdout.write(first_lines(detail_text, 120))
                if detail_text and not detail_text.endswith("\n"):
                    sys.stdout.write("\n")

        with ThreadPoolExecutor(max_workers=jobs) as executor:
            future_map = {
                executor.submit(run_one, case.index, case.name, case.path, artifact_dir, args.max_details): case.index
                for case in cases
            }
            for future in as_completed(future_map):
                result = future.result()
                ready[result.case_index] = result

                while next_index in ready:
                    emit(ready.pop(next_index))
                    next_index += 1

        print("======================================")
        print(f"Passed: {passed}")
        print(f"Failed: {len(failed_names)}")

        if failed_names:
            print(f"Failed tests: {' '.join(failed_names)}")
            print(f"Trace artifacts kept at: {artifact_dir}")
            keep_artifacts = True
            return 1

        print("All trace checks passed!")
        if keep_artifacts:
            print(f"Trace artifacts kept at: {artifact_dir}")
        return 0
    finally:
        if not keep_artifacts:
            shutil.rmtree(artifact_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
