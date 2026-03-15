#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Regression coverage for the `make dist` distribution workflow."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_TESTS_ROOT = REPO_ROOT / "build" / "tests"


def fail(message: str) -> None:
    raise SystemExit(f"test_make_dist_workflow: FAIL: {message}")


def is_windows_host() -> bool:
    return os.name == "nt"


def run_checked(command: list[str], *, env: dict[str, str] | None = None) -> str:
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


def assert_exists(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        fail(f"expected path: {path}")


def assert_contains(path: Path, needle: str) -> None:
    text = path.read_text(encoding="utf-8")
    if needle not in text:
        fail(f"expected {needle!r} in {path}")


def assert_not_contains(path: Path, needle: str) -> None:
    text = path.read_text(encoding="utf-8")
    if needle in text:
        fail(f"did not expect {needle!r} in {path}")


def clean_env() -> dict[str, str]:
    env = {"PATH": os.environ.get("PATH", "")}
    if is_windows_host():
        for name in ("SYSTEMROOT", "COMSPEC", "WINDIR"):
            value = os.environ.get(name)
            if value:
                env[name] = value
    return env


def stage2_launcher_path(base: Path) -> str:
    if is_windows_host():
        cmd_path = base.with_suffix(".cmd")
        if cmd_path.is_file():
            return str(cmd_path)
    return str(base)


def extract_archive(archive_path: Path, destination: Path) -> None:
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(destination)
        return
    if archive_path.name.endswith(".tar.gz"):
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(destination)
        return
    fail(f"unexpected archive format: {archive_path}")


def assert_version_report(text: str) -> None:
    for expected in (
        "Dea language / L0 compiler (Stage 2)",
        "build: ",
        "build time: ",
        "commit: ",
        "host: ",
        "compiler: ",
    ):
        if expected not in text:
            fail(f"expected {expected!r} in version output:\n{text}")


def parse_host_target(version_text: str) -> str:
    match = re.search(r"^host: (.+)$", version_text, flags=re.MULTILINE)
    if match is None:
        fail(f"could not parse host line from version output:\n{version_text}")
    words = match.group(1).split()
    if len(words) < 2:
        fail(f"unexpected host line: {match.group(1)!r}")
    return f"{words[0].lower()}-{words[-1].lower()}"


def make_hello_project(project_dir: Path) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "hello.l0").write_text(
        """module hello;

import std.io;

func main() -> int {
    printl_s("Hello, World!");
    return 0;
}
""",
        encoding="utf-8",
    )


def main() -> int:
    BUILD_TESTS_ROOT.mkdir(parents=True, exist_ok=True)
    extract_root = Path(tempfile.mkdtemp(prefix="make_dist_unpack.", dir=BUILD_TESTS_ROOT))
    project_dir = Path(tempfile.mkdtemp(prefix="make_dist_project.", dir=BUILD_TESTS_ROOT))

    try:
        output = run_checked(["make", "dist"])
        dist_match = re.search(r"created distribution directory at (.+)", output)
        archive_match = re.search(r"created distribution archive at (.+)", output)
        if dist_match is None:
            fail(f"could not find distribution directory in output:\n{output}")
        if archive_match is None:
            fail(f"could not find distribution archive in output:\n{output}")

        dist_dir = Path(dist_match.group(1).strip())
        archive_path = Path(archive_match.group(1).strip())
        if dist_dir.name != "dea-l0":
            fail(f"expected distribution directory name 'dea-l0', got {dist_dir.name!r}")
        expected_suffix = ".zip" if is_windows_host() else ".tar.gz"
        if not str(archive_path).endswith(expected_suffix):
            fail(f"expected archive suffix {expected_suffix!r}, got {archive_path}")
        assert_exists(dist_dir / "bin" / "l0c-stage2")
        assert_exists(dist_dir / "bin" / "l0c-stage2.native")
        assert_exists(dist_dir / "bin" / "l0c")
        assert_exists(dist_dir / "bin" / "l0-env.sh")
        assert_exists(dist_dir / "shared" / "l0" / "stdlib" / "std" / "io.l0")
        assert_exists(dist_dir / "shared" / "runtime" / "l0_runtime.h")
        assert_exists(archive_path)
        assert_not_contains(dist_dir / "bin" / "l0c-stage2", str(REPO_ROOT))
        assert_not_contains(dist_dir / "bin" / "l0-env.sh", str(REPO_ROOT))

        extract_archive(archive_path, extract_root)
        unpacked_dist = extract_root / "dea-l0"
        assert_exists(unpacked_dist / "bin" / "l0c-stage2")
        assert_exists(unpacked_dist / "bin" / "l0c-stage2.native")
        assert_exists(unpacked_dist / "bin" / "l0c")
        assert_exists(unpacked_dist / "shared" / "l0" / "stdlib" / "std" / "io.l0")
        assert_contains(unpacked_dist / "bin" / "l0-env.sh", 'export L0_HOME="${PREFIX_DIR}"')

        wrapper_version = run_checked([stage2_launcher_path(unpacked_dist / "bin" / "l0c-stage2"), "--version"], env=clean_env())
        native_version = run_checked([str(unpacked_dist / "bin" / "l0c-stage2.native"), "--version"], env=clean_env())
        assert_version_report(wrapper_version)
        if native_version != wrapper_version:
            fail("expected extracted wrapper/native --version output to match")
        archive_pattern = (
            rf"^dea-l0-lang_{re.escape(parse_host_target(wrapper_version))}_\d{{8}}-\d{{6}}"
            + (r"\.zip$" if is_windows_host() else r"\.tar\.gz$")
        )
        if re.match(archive_pattern, archive_path.name) is None:
            fail(f"unexpected archive name: {archive_path.name}")

        make_hello_project(project_dir)
        hello_bin = project_dir / "hello"
        if is_windows_host():
            hello_bin = hello_bin.with_suffix(".exe")
        run_checked(
            [
                stage2_launcher_path(unpacked_dist / "bin" / "l0c-stage2"),
                "--build",
                "-P",
                str(project_dir),
                "-o",
                str(hello_bin),
                "hello",
            ],
            env=clean_env(),
        )
        hello_output = run_checked([str(hello_bin)], env=clean_env())
        if "Hello, World!" not in hello_output:
            fail(f"expected Hello, World! from built binary, got:\n{hello_output}")
    finally:
        shutil.rmtree(extract_root, ignore_errors=True)
        shutil.rmtree(project_dir, ignore_errors=True)

    print("test_make_dist_workflow: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
