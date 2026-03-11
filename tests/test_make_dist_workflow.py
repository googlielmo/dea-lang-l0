#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Regression coverage for the repo-local Make dist workflow."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_TESTS_ROOT = REPO_ROOT / "build" / "tests"


def fail(message: str) -> None:
    raise SystemExit(f"test_make_dist_workflow: FAIL: {message}")


def run_checked(command: list[str], *, extra_env: dict[str, str] | None = None) -> str:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if proc.returncode != 0:
        fail(
            f"command failed ({proc.returncode}): {' '.join(command)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    return proc.stdout + proc.stderr


def run_expected_fail(command: list[str], expected: str, *, extra_env: dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if proc.returncode == 0:
        fail(f"expected command to fail: {' '.join(command)}")
    combined = proc.stdout + proc.stderr
    if expected not in combined:
        fail(
            f"expected {expected!r} in failing output for {' '.join(command)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )


def assert_exists(path: Path) -> None:
    if not path.exists():
        fail(f"expected path: {path}")


def assert_missing(path: Path) -> None:
    if path.exists() or path.is_symlink():
        fail(f"did not expect path: {path}")


def assert_symlink_target(path: Path, expected: str) -> None:
    if not path.is_symlink():
        fail(f"expected symlink: {path}")
    target = os.readlink(path)
    if target != expected:
        fail(f"expected {path} -> {expected}, got {target}")


def make_command(dist_rel: str, *targets: str, dry_run: bool = False) -> list[str]:
    command = ["make"]
    if dry_run:
        command.append("-n")
    command.append(f"DIST_DIR={dist_rel}")
    command.extend(targets)
    return command


def assert_output_contains(text: str, expected: str) -> None:
    if expected not in text:
        fail(f"expected {expected!r} in output:\n{text}")


def source_env_and_check(dist_dir: Path) -> None:
    env_script = dist_dir / "bin" / "l0-env.sh"
    command = [
        "bash",
        "-lc",
        f"source {shlex.quote(str(env_script))} && l0c --check -P examples hello",
    ]
    run_checked(command)


def main() -> int:
    BUILD_TESTS_ROOT.mkdir(parents=True, exist_ok=True)
    dist_dir = Path(tempfile.mkdtemp(prefix="make_dist.", dir=BUILD_TESTS_ROOT))
    dist_rel = os.path.relpath(dist_dir, REPO_ROOT)
    alias_path = dist_dir / "bin" / "l0c"
    stage1_path = dist_dir / "bin" / "l0c-stage1"
    stage2_path = dist_dir / "bin" / "l0c-stage2"
    native_path = dist_dir / "bin" / "l0c-stage2.native"
    env_path = dist_dir / "bin" / "l0-env.sh"
    expected_source_hint = f"source {dist_rel}/bin/l0-env.sh"

    try:
        help_output = run_checked(["make", "help"])
        for target in (
            "install-stage1",
            "install-stage2",
            "install-all",
            "use-stage1",
            "use-stage2",
            "test-stage1",
            "test-stage2",
            "test-stage2-trace",
            "triple-test",
            "test-all",
            "docs",
            "docs-pdf",
            "clean-dist",
        ):
            assert_output_contains(help_output, target)

        run_checked(make_command(dist_rel, "install-stage1"))
        assert_exists(stage1_path)
        assert_exists(env_path)
        assert_missing(alias_path)
        stable_env_text = env_path.read_text(encoding="utf-8")

        run_expected_fail(
            ["bash", str(env_path)],
            expected_source_hint,
        )

        run_checked(make_command(dist_rel, "install-stage2"))
        assert_exists(stage2_path)
        assert_exists(native_path)
        assert_exists(env_path)
        assert_missing(alias_path)
        if env_path.read_text(encoding="utf-8") != stable_env_text:
            fail("expected l0-env.sh to remain stable after install-stage2")

        run_checked(make_command(dist_rel, "install-all"))
        assert_exists(stage1_path)
        assert_exists(stage2_path)
        assert_exists(native_path)
        assert_exists(env_path)
        assert_missing(alias_path)
        if env_path.read_text(encoding="utf-8") != stable_env_text:
            fail("expected l0-env.sh to remain stable after install-all")

        use_stage1_output = run_checked(make_command(dist_rel, "use-stage1"))
        assert_symlink_target(alias_path, "l0c-stage1")
        assert_output_contains(use_stage1_output, expected_source_hint)

        run_checked(make_command(dist_rel, "install-all"))
        assert_symlink_target(alias_path, "l0c-stage1")

        source_env_and_check(dist_dir)

        use_stage2_output = run_checked(make_command(dist_rel, "use-stage2"))
        assert_symlink_target(alias_path, "l0c-stage2")
        assert_output_contains(use_stage2_output, expected_source_hint)
        run_checked(make_command(dist_rel, "use-stage2"))
        assert_symlink_target(alias_path, "l0c-stage2")
        source_env_and_check(dist_dir)

        run_expected_fail(
            ["make", "DIST_DIR=/tmp/l0-dev", "install-stage1"],
            "DIST_DIR must resolve to a subdirectory inside the repository",
        )
        run_expected_fail(
            ["make", "DIST_DIR=.", "install-stage1"],
            "DIST_DIR must resolve to a subdirectory inside the repository",
        )
        run_expected_fail(
            ["python3", "./scripts/gen_dist_tools.py", "write-env-script", "--dist-dir", "/tmp/l0-dev"],
            "DIST_DIR must resolve to a subdirectory inside the repository",
        )
        run_expected_fail(
            ["./scripts/build-stage2-l0c.sh"],
            "DIST_DIR must resolve to a subdirectory inside the repository",
            extra_env={"DIST_DIR": "."},
        )

        dry_run_expectations = {
            "test-stage1": "pytest -n auto",
            "test-stage2": "./compiler/stage2_l0/run_tests.py",
            "test-stage2-trace": "./compiler/stage2_l0/run_trace_tests.py",
            "triple-test": "python3 ./compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py",
            "test-all": "./compiler/stage2_l0/run_trace_tests.py",
            "docs": "./scripts/gen-docs.sh",
            "docs-pdf": "./scripts/gen-docs.sh --pdf",
        }
        for target, expected in dry_run_expectations.items():
            output = run_checked(make_command(dist_rel, target, dry_run=True))
            assert_output_contains(output, expected)

        run_checked(make_command(dist_rel, "clean-dist"))
        if dist_dir.exists():
            fail(f"expected clean-dist to remove {dist_dir}")
    finally:
        shutil.rmtree(dist_dir, ignore_errors=True)

    print("test_make_dist_workflow: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
