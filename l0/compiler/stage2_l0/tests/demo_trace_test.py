#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Trace regression for `examples/demo.l0`."""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
TRACE_CHECKER = REPO_ROOT / "compiler/stage2_l0/check_trace_log.py"
TARGET = REPO_ROOT / "examples/demo.l0"


class DemoTraceFailure(RuntimeError):
    """Raised when one demo trace assertion fails."""


def read_text(path: Path) -> str:
    """Read text with replacement for invalid bytes."""

    return path.read_text(encoding="utf-8", errors="replace")


def fail(message: str, artifact_dir: Path) -> None:
    """Abort the test and keep artifacts."""

    raise DemoTraceFailure(f"{message}\nartifacts={artifact_dir}")


def assert_contains(path: Path, needle: str, artifact_dir: Path) -> None:
    """Assert that `needle` exists in `path`."""

    if needle not in read_text(path):
        fail(f"expected {needle!r} in {path}", artifact_dir)


def source_tree_l0c_command() -> list[str]:
    """Return the command used to invoke the source-tree Stage 1 compiler."""

    if os.name == "nt":
        cmd_path = REPO_ROOT / "scripts" / "l0c.cmd"
        if cmd_path.is_file():
            return [str(cmd_path)]
        return [sys.executable, str(REPO_ROOT / "compiler" / "stage1_py" / "l0c.py")]
    return ["./scripts/l0c"]


def run_case(name: str, expected_rc: int, expected_stdout_substr: str, artifact_dir: Path, *argv: str) -> None:
    """Run one demo trace scenario and assert trace health."""

    out_path = artifact_dir / f"{name}.stdout.log"
    trace_path = artifact_dir / f"{name}.stderr.log"
    report_path = artifact_dir / f"{name}.trace_report.txt"

    command = [*source_tree_l0c_command(), "--run", "--trace-memory", "--trace-arc", str(TARGET)]
    if argv:
        command.extend(["--", *argv])

    run_result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    out_path.write_bytes(run_result.stdout if run_result.stdout is not None else b"")
    trace_path.write_bytes(run_result.stderr if run_result.stderr is not None else b"")

    if run_result.returncode != expected_rc:
        fail(f"{name} expected exit code {expected_rc}, got {run_result.returncode}", artifact_dir)

    with report_path.open("w", encoding="utf-8") as report_file:
        analyzer_result = subprocess.run(
            [sys.executable, str(TRACE_CHECKER), "--triage", str(trace_path)],
            cwd=REPO_ROOT,
            stdout=report_file,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    if analyzer_result.returncode != 0:
        fail(f"{name} trace triage failed (analyzer_rc={analyzer_result.returncode})", artifact_dir)

    assert_contains(report_path, "errors=0", artifact_dir)
    assert_contains(report_path, "leaked_object_ptrs=0", artifact_dir)
    assert_contains(report_path, "leaked_string_ptrs=0", artifact_dir)
    assert_contains(out_path, expected_stdout_substr, artifact_dir)


def main() -> int:
    """Program entrypoint."""

    artifact_dir = Path(tempfile.mkdtemp(prefix="l0_demo_trace_test."))
    keep_artifacts = os.environ.get("KEEP_ARTIFACTS", "0") == "1"

    try:
        run_case("ok_mul", 0, "= 32", artifact_dir, "mul", "4", "add", "5", "3")
        run_case("ok_add", 0, "= 5", artifact_dir, "add", "2", "3")
        run_case("ok_mul_2", 0, "= 32", artifact_dir, "mul", "4", "add", "5", "mul", "1", "mul", "1", "3")
        run_case("err_unknown_op", 1, "usage: demo <expr>", artifact_dir, "foo", "1", "2")
        run_case("err_incomplete_rhs", 1, "usage: demo <expr>", artifact_dir, "add", "1")
        run_case("err_no_args", 1, "usage: demo <expr>", artifact_dir)
        run_case("err_trailing_token", 1, "usage: demo <expr>", artifact_dir, "add", "1", "2", "3")
        print("demo_trace_test: PASS")
        return 0
    except DemoTraceFailure as exc:
        keep_artifacts = True
        lines = str(exc).splitlines()
        if lines:
            print(f"demo_trace_test: FAIL: {lines[0]}")
        for line in lines[1:]:
            print(f"demo_trace_test: {line}")
        return 1
    finally:
        if not keep_artifacts:
            shutil.rmtree(artifact_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
