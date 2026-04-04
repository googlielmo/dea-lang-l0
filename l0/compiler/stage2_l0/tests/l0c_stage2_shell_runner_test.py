#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Regression coverage for Stage 2 shell-runner bash resolution."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
RUNNER_DIR = SCRIPT_DIR.parent / "scripts"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

import test_runner_common as common
from test_runner_common import TestCase, build_normal_test_command


def fail(message: str) -> int:
    """Print one failure and return the shell-style exit code."""

    print(f"l0c_stage2_shell_runner_test: FAIL: {message}")
    return 1


def main() -> int:
    """Program entrypoint."""

    original_os_name = common.os.name
    try:
        common.os.name = "nt"
        if not common.is_windows_wsl_bash_path(Path(r"C:\Windows\System32\bash.exe")):
            return fail("expected the System32 bash shim to be rejected on Windows")
        if common.is_windows_wsl_bash_path(Path(r"C:\msys64\usr\bin\bash.exe")):
            return fail("did not expect an MSYS2 bash path to be rejected")
    finally:
        common.os.name = original_os_name

    shell_case = TestCase(
        index=0,
        name="shell_case",
        path=SCRIPT_DIR / "l0c_stage2_default_dea_build_test.sh",
        kind="shell",
    )

    bash_path = common.resolve_shell_bash_path()
    if bash_path is None:
        print("l0c_stage2_shell_runner_test: PASS (no usable bash on this host)")
        return 0

    command = build_normal_test_command(shell_case, Path(sys.executable))
    if Path(command[0]) != bash_path:
        return fail("shell tests must execute the resolved bash path directly")
    if not Path(command[0]).is_absolute():
        return fail("shell tests must use an absolute bash path")

    print("l0c_stage2_shell_runner_test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
