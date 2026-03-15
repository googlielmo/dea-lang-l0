#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Regression coverage for the Make Dea build and install-prefix workflows."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_TESTS_ROOT = REPO_ROOT / "build" / "tests"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dist_tools_lib import Stage2BuildProvenance, format_build_time_utc, format_commit_for_version, render_stage2_build_info_module


def fail(message: str) -> None:
    raise SystemExit(f"test_make_dea_build_workflow: FAIL: {message}")


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


def make_command(dea_build_rel: str, *targets: str, dry_run: bool = False) -> list[str]:
    command = ["make"]
    if dry_run:
        command.append("-n")
    command.append(f"DEA_BUILD_DIR={dea_build_rel}")
    command.extend(targets)
    return command


def prefix_command(prefix: Path, *targets: str, dry_run: bool = False) -> list[str]:
    command = ["make"]
    if dry_run:
        command.append("-n")
    command.append(f"PREFIX={prefix}")
    command.extend(targets)
    return command


def assert_output_contains(text: str, expected: str) -> None:
    if expected not in text:
        fail(f"expected {expected!r} in output:\n{text}")


def assert_output_not_contains(text: str, unexpected: str) -> None:
    if unexpected in text:
        fail(f"did not expect {unexpected!r} in output:\n{text}")


def assert_version_report(text: str) -> None:
    for expected in (
        "Dea language / L0 compiler (Stage 2)",
        "build: ",
        "build time: ",
        "commit: ",
        "host: ",
        "compiler: ",
    ):
        assert_output_contains(text, expected)
    for unexpected in ("tree: ", "build id: ", "built at: ", "compiler version: "):
        assert_output_not_contains(text, unexpected)


def assert_provenance_helper_contract() -> None:
    timestamp = datetime(2026, 3, 12, 23, 55, 56, tzinfo=timezone.utc)
    if format_build_time_utc(timestamp) != "2026-03-12 23:55:56+00:00":
        fail("format_build_time_utc must use the fixed `+00:00` rendering")
    if format_commit_for_version("abc123", "clean") != "abc123":
        fail("clean commit formatting must not add a suffix")
    if format_commit_for_version("abc123", "dirty") != "abc123+dirty":
        fail("dirty commit formatting must append +dirty")

    rendered = render_stage2_build_info_module(
        Stage2BuildProvenance(
            commit_full="f8174b779f339af1f159765880b92f3b5c40490b",
            commit_short="f8174b7",
            tree_state="dirty",
            build_id="f8174b7-20260312T235556Z",
            build_time="2026-03-12 23:55:56+00:00",
            host="Darwin 24.6.0 x86_64",
            compiler_banner="gcc-15 (Homebrew GCC 15.2.0_1) 15.2.0",
            has_embedded_version=True,
        )
    )
    for expected in ("build: ", "build time: ", "commit: ", "host: ", "compiler: ", "+dirty", "Darwin 24.6.0 x86_64"):
        assert_output_contains(rendered, expected)
    for unexpected in ("tree: ", "build id: ", "built at: ", "compiler version: "):
        assert_output_not_contains(rendered, unexpected)


def source_env_and_check(dea_build_dir: Path) -> None:
    env_script = dea_build_dir / "bin" / "l0-env.sh"
    command = [
        "bash",
        "-lc",
        f"source {shlex.quote(str(env_script))} && l0c --check -P examples hello",
    ]
    run_checked(command)


def main() -> int:
    BUILD_TESTS_ROOT.mkdir(parents=True, exist_ok=True)
    assert_provenance_helper_contract()
    dea_build_dir = Path(tempfile.mkdtemp(prefix="make_dea_build.", dir=BUILD_TESTS_ROOT))
    prefix_dir = Path(tempfile.mkdtemp(prefix="make_prefix.")).resolve(strict=False)
    dea_build_rel = os.path.relpath(dea_build_dir, REPO_ROOT)
    alias_path = dea_build_dir / "bin" / "l0c"
    stage1_path = dea_build_dir / "bin" / "l0c-stage1"
    stage2_path = dea_build_dir / "bin" / "l0c-stage2"
    native_path = dea_build_dir / "bin" / "l0c-stage2.native"
    env_path = dea_build_dir / "bin" / "l0-env.sh"
    prefix_alias_path = prefix_dir / "bin" / "l0c"
    prefix_stage2_path = prefix_dir / "bin" / "l0c-stage2"
    prefix_native_path = prefix_dir / "bin" / "l0c-stage2.native"
    prefix_env_path = prefix_dir / "bin" / "l0-env.sh"
    expected_source_hint = f"source {dea_build_rel}/bin/l0-env.sh"

    try:
        help_output = run_checked(["make", "help"])
        for target in (
            "install-dev-stage1",
            "install-dev-stage2",
            "install-dev-stages",
            "install",
            "dist",
            "use-dev-stage1",
            "use-dev-stage2",
            "test-stage1",
            "test-stage2",
            "test-stage2-trace",
            "test-dist",
            "triple-test",
            "test-all",
            "docs",
            "docs-pdf",
            "clean-dea-build",
        ):
            assert_output_contains(help_output, target)
        assert_output_contains(help_output, "PREFIX=<required>")

        print_dea_build_output = run_checked(make_command(dea_build_rel, "print-dea-build-dir"))
        if print_dea_build_output.strip() != dea_build_rel:
            fail(f"expected print-dea-build-dir to return {dea_build_rel!r}, got {print_dea_build_output!r}")

        run_checked(make_command(dea_build_rel, "install-dev-stage1"))
        assert_exists(stage1_path)
        assert_exists(env_path)
        assert_missing(alias_path)
        stable_env_text = env_path.read_text(encoding="utf-8")

        run_expected_fail(
            ["bash", str(env_path)],
            expected_source_hint,
        )

        run_checked(make_command(dea_build_rel, "install-dev-stage2"))
        assert_exists(stage2_path)
        assert_exists(native_path)
        assert_exists(env_path)
        assert_missing(alias_path)
        repo_wrapper_version = run_checked([str(stage2_path), "--version"])
        repo_native_version = run_checked([str(native_path), "--version"])
        assert_version_report(repo_wrapper_version)
        if repo_native_version != repo_wrapper_version:
            fail("expected repo-local wrapper/native --version output to match")
        if env_path.read_text(encoding="utf-8") != stable_env_text:
            fail("expected l0-env.sh to remain stable after install-dev-stage2")

        run_checked(make_command(dea_build_rel, "install-dev-stages"))
        assert_exists(stage1_path)
        assert_exists(stage2_path)
        assert_exists(native_path)
        assert_exists(env_path)
        assert_missing(alias_path)
        if env_path.read_text(encoding="utf-8") != stable_env_text:
            fail("expected l0-env.sh to remain stable after install-dev-stages")

        use_stage1_output = run_checked(make_command(dea_build_rel, "use-dev-stage1"))
        assert_symlink_target(alias_path, "l0c-stage1")
        assert_output_contains(use_stage1_output, expected_source_hint)

        run_checked(make_command(dea_build_rel, "install-dev-stages"))
        assert_symlink_target(alias_path, "l0c-stage1")

        source_env_and_check(dea_build_dir)

        use_stage2_output = run_checked(make_command(dea_build_rel, "use-dev-stage2"))
        assert_symlink_target(alias_path, "l0c-stage2")
        assert_output_contains(use_stage2_output, expected_source_hint)
        run_checked(make_command(dea_build_rel, "use-dev-stage2"))
        assert_symlink_target(alias_path, "l0c-stage2")
        source_env_and_check(dea_build_dir)

        install_prefix_output = run_checked(prefix_command(prefix_dir, "install"))
        assert_exists(prefix_stage2_path)
        assert_exists(prefix_native_path)
        assert_exists(prefix_env_path)
        assert_exists(prefix_dir / "shared" / "l0" / "stdlib" / "std" / "io.l0")
        assert_exists(prefix_dir / "shared" / "runtime" / "l0_runtime.h")
        assert_symlink_target(prefix_alias_path, "l0c-stage2")
        assert_output_contains(install_prefix_output, "installed self-hosted Stage 2 compiler")
        prefix_wrapper_version = run_checked([str(prefix_stage2_path), "--version"])
        prefix_native_version = run_checked([str(prefix_native_path), "--version"])
        assert_version_report(prefix_wrapper_version)
        if prefix_native_version != prefix_wrapper_version:
            fail("expected installed wrapper/native --version output to match")

        run_expected_fail(
            ["make", "DEA_BUILD_DIR=/tmp/l0-dev", "install-dev-stage1"],
            "DEA_BUILD_DIR must resolve to a subdirectory inside the repository",
        )
        run_expected_fail(
            ["make", "DEA_BUILD_DIR=.", "install-dev-stage1"],
            "DEA_BUILD_DIR must resolve to a subdirectory inside the repository",
        )
        run_expected_fail(
            ["make", "install"],
            "make install: PREFIX is required; example: make PREFIX=/tmp/l0-install L0_CC=gcc install",
        )
        run_expected_fail(
            ["make", "PREFIX=.", "install"],
            "PREFIX must not resolve to the repository root",
        )
        run_expected_fail(
            ["python3", "./scripts/gen_dist_tools.py", "write-env-script", "--dea-build-dir", "/tmp/l0-dev"],
            "DEA_BUILD_DIR must resolve to a subdirectory inside the repository",
        )
        run_expected_fail(
            ["./scripts/build-stage2-l0c.sh"],
            "DEA_BUILD_DIR must resolve to a subdirectory inside the repository",
            extra_env={"DEA_BUILD_DIR": "."},
        )

        dry_run_expectations = {
            "install": "gen_dist_tools.py install-prefix --prefix",
            "dist": "gen_dist_tools.py make-dist",
            "test-stage1": "pytest -n auto",
            "test-stage2": "./compiler/stage2_l0/run_tests.py",
            "test-stage2-trace": "./compiler/stage2_l0/run_trace_tests.py",
            "test-dist": "./tests/test_make_dist_workflow.py",
            "triple-test": "./compiler/stage2_l0/tests/l0c_triple_bootstrap_test.py",
            "test-all": "./compiler/stage2_l0/run_trace_tests.py",
            "docs": "./scripts/gen-docs.sh",
            "docs-pdf": "./scripts/gen-docs.sh --strict --pdf",
        }
        for target, expected in dry_run_expectations.items():
            output = run_checked(make_command(dea_build_rel, target, dry_run=True))
            assert_output_contains(output, expected)
            if target in {"test-stage2", "test-stage2-trace", "triple-test"}:
                assert_output_contains(output, "./scripts/build-stage2-l0c.sh")

        run_checked(make_command(dea_build_rel, "clean-dea-build"))
        if dea_build_dir.exists():
            fail(f"expected clean-dea-build to remove {dea_build_dir}")
    finally:
        shutil.rmtree(dea_build_dir, ignore_errors=True)
        shutil.rmtree(prefix_dir, ignore_errors=True)

    print("test_make_dea_build_workflow: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
