#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Shared helpers for Stage 2 integration-tool tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SCRIPT_DIR = Path(__file__).resolve().parent
STAGE_DIR = SCRIPT_DIR.parent
REPO_ROOT = STAGE_DIR.parent.parent
MONOREPO_ROOT = REPO_ROOT.parent
BUILD_TESTS_ROOT = REPO_ROOT / "build" / "tests"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dist_tools_lib import resolve_host_c_compiler


class ToolTestFailure(RuntimeError):
    """Raised when a Stage 2 integration-tool assertion fails."""


def is_windows_host() -> bool:
    """Return whether the current host should use Windows launcher behavior."""

    if os.name == "nt":
        return True
    if os.environ.get("OS") == "Windows_NT":
        return True
    return bool(os.environ.get("MSYSTEM", "").strip())


def native_path(path: Path | str) -> str:
    """Return a host-native path string for compiler command-line arguments."""

    raw_path = Path(path)
    if not is_windows_host():
        return str(raw_path)
    if os.name == "nt":
        return str(raw_path)

    cygpath = shutil.which("cygpath")
    if cygpath is None:
        return str(raw_path)
    completed = subprocess.run(
        [cygpath, "-w", str(raw_path)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise ToolTestFailure(f"cygpath failed for {raw_path}: {completed.stdout}")
    return completed.stdout.strip()


def stage2_launcher_path(base: Path) -> str:
    """Return the best launcher path for a generated Stage 2 wrapper."""

    cmd_path = base.with_suffix(".cmd")
    if is_windows_host() and cmd_path.is_file():
        return native_path(cmd_path)
    return native_path(base)


def clean_env(path: str | None = None, extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return a small environment for wrapper isolation tests."""

    env = {"PATH": path if path is not None else os.environ.get("PATH", "")}
    if is_windows_host():
        for name in ("SYSTEMROOT", "COMSPEC", "WINDIR", "OS", "TEMP", "TMP"):
            env[name] = os.environ.get(name, "")
    if extra is not None:
        env.update(extra)
    return env


def repo_l0_env(path: str | None = None) -> dict[str, str]:
    """Return a repo-local compiler environment for direct native binary use."""

    env = os.environ.copy()
    if path is not None:
        env["PATH"] = path
        env.pop("Path", None)
    env["L0_HOME"] = str(REPO_ROOT / "compiler")
    env.pop("L0_SYSTEM", None)
    env.pop("L0_RUNTIME_INCLUDE", None)
    env.pop("L0_RUNTIME_LIB", None)
    return env


def run(
        command: Sequence[str | Path],
        *,
        cwd: Path = REPO_ROOT,
        env: Mapping[str, str] | None = None,
        expected_returncode: int | None = 0,
) -> subprocess.CompletedProcess[str]:
    """Run one subprocess and capture decoded combined output streams."""

    completed = subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        env=dict(env) if env is not None else None,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if expected_returncode is not None and completed.returncode != expected_returncode:
        raise ToolTestFailure(
            "\n".join(
                [
                    f"command failed with rc={completed.returncode}: {' '.join(str(part) for part in command)}",
                    f"stdout:\n{completed.stdout}",
                    f"stderr:\n{completed.stderr}",
                ]
            ).rstrip()
        )
    return completed


def run_to_files(
        command: Sequence[str | Path],
        stdout_path: Path,
        stderr_path: Path,
        *,
        cwd: Path = REPO_ROOT,
        env: Mapping[str, str] | None = None,
        expected_returncode: int | None = 0,
) -> subprocess.CompletedProcess[str]:
    """Run one subprocess, capture stdout/stderr, and write both to files."""

    completed = run(
        command,
        cwd=cwd,
        env=env,
        expected_returncode=expected_returncode,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return completed


def build_stage2(dea_build_dir: Path | str, *, keep_c: bool = False) -> None:
    """Build one isolated Stage 2 artifact with the Python builder."""

    env = os.environ.copy()
    env["DEA_BUILD_DIR"] = str(dea_build_dir)
    if keep_c:
        env["KEEP_C"] = "1"
    else:
        env.pop("KEEP_C", None)
    run([sys.executable, REPO_ROOT / "scripts" / "build_stage2_l0c.py"], env=env)


def make_temp_dir(prefix: str, parent: Path | None = None) -> Path:
    """Create one temp directory under the repo build tree."""

    if parent is None:
        parent = REPO_ROOT / "build"
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=parent))


def repo_relative(path: Path) -> str:
    """Return a repository-relative path string for paths inside the L0 repo."""

    return path.relative_to(REPO_ROOT).as_posix()


def read_text(path: Path) -> str:
    """Read UTF-8 text with replacement for invalid bytes."""

    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    """Write one UTF-8 text file."""

    path.write_text(text, encoding="utf-8")


def assert_file(path: Path) -> None:
    """Assert that one regular file exists."""

    if not path.is_file():
        raise ToolTestFailure(f"expected file: {path}")


def assert_no_file(path: Path) -> None:
    """Assert that one path is absent."""

    if path.exists() or path.is_symlink():
        raise ToolTestFailure(f"did not expect path: {path}")


def assert_contains(path: Path, text: str) -> None:
    """Assert that one file contains a literal substring."""

    if text not in read_text(path):
        raise ToolTestFailure(f"expected {text!r} in {path}")


def assert_not_contains(path: Path, text: str) -> None:
    """Assert that one file does not contain a literal substring."""

    if text in read_text(path):
        raise ToolTestFailure(f"did not expect {text!r} in {path}")


def assert_matches(path: Path, pattern: str) -> None:
    """Assert that one file matches a regular expression."""

    if re.search(pattern, read_text(path), flags=re.MULTILINE) is None:
        raise ToolTestFailure(f"expected pattern {pattern!r} in {path}")


def assert_empty(path: Path) -> None:
    """Assert that one file is empty."""

    if path.exists() and path.stat().st_size != 0:
        raise ToolTestFailure(f"expected empty file: {path}")


def assert_text_equals(path: Path, expected: str) -> None:
    """Assert that one file exactly equals expected text."""

    actual = read_text(path)
    if actual != expected:
        raise ToolTestFailure(f"unexpected content in {path}: {actual!r}")


def assert_line_before(path: Path, first: str, second: str) -> None:
    """Assert that one line appears before another line in a file."""

    lines = read_text(path).splitlines()
    try:
        first_index = next(index for index, line in enumerate(lines) if first in line)
    except StopIteration as exc:
        raise ToolTestFailure(f"line {first!r} not found in {path}") from exc
    try:
        second_index = next(index for index, line in enumerate(lines) if second in line)
    except StopIteration as exc:
        raise ToolTestFailure(f"line {second!r} not found in {path}") from exc
    if first_index >= second_index:
        raise ToolTestFailure(f"expected {first!r} before {second!r} in {path}")


def c_output_path(output_path: Path) -> Path:
    """Return the `--keep-c` C output path for one executable output path."""

    if output_path.suffix:
        return output_path.with_suffix(".c")
    return output_path.with_name(f"{output_path.name}.c")


def normalize_text_file(src: Path, dst: Path) -> None:
    """Normalize CRLF/CR line endings and final newline into `dst`."""

    text = read_text(src).replace("\r\n", "\n").replace("\r", "\n")
    dst.write_text(text.rstrip("\n") + "\n", encoding="utf-8")


def detect_c_compiler() -> str | None:
    """Return the host C compiler command using the shared tooling precedence."""

    return resolve_host_c_compiler(os.environ.copy())
