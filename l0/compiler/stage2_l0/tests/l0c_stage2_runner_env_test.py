#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Regression coverage for normal Stage 2 runner env selection."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_DIR = SCRIPT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from test_runner_common import build_normal_test_env, require_repo_stage2_test_env, TestCase


def fail(message: str) -> int:
    """Print one failure and return the shell-style exit code."""

    print(f"l0c_stage2_runner_env_test: FAIL: {message}")
    return 1


def main() -> int:
    """Program entrypoint."""

    try:
        _, dea_build_dir_text, _, repo_env = require_repo_stage2_test_env("l0c_stage2_runner_env_test.py")
    except RuntimeError as exc:
        return fail(str(exc))

    python_case = TestCase(index=0, name="python_case", path=SCRIPT_DIR / "demo_trace_test.py", kind="python")
    shell_case = TestCase(
        index=1,
        name="shell_case",
        path=SCRIPT_DIR / "l0c_stage2_default_dea_build_test.sh",
        kind="shell",
    )
    l0_case = TestCase(index=2, name="l0_case", path=SCRIPT_DIR / "smoke.l0", kind="l0")

    python_env = build_normal_test_env(python_case, repo_env)
    if python_env.get("DEA_BUILD_DIR") != dea_build_dir_text:
        return fail("python cases must preserve DEA_BUILD_DIR for nested Stage 2 helpers")

    shell_env = build_normal_test_env(shell_case, repo_env)
    if "DEA_BUILD_DIR" in shell_env:
        return fail("shell cases must not inherit DEA_BUILD_DIR")

    l0_env = build_normal_test_env(l0_case, repo_env)
    if "DEA_BUILD_DIR" in l0_env:
        return fail(".l0 cases must not inherit DEA_BUILD_DIR")

    if repo_env.get("DEA_BUILD_DIR") != dea_build_dir_text:
        return fail("runner env must remain unchanged after per-case env derivation")

    print("l0c_stage2_runner_env_test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
