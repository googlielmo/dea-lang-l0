#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Run latest-stage `--check` across example sources and fail on warnings."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from dea_tooling.bootstrap import wrapper_command


WARNING_MARKER = "warning: ["


@dataclass(frozen=True)
class CheckFailure:
    """One failing example check result."""

    source: Path
    reason: str


def relative_text(path: Path) -> str:
    """Return `path` relative to the current working directory when possible.

    Args:
        path: Path to render.

    Returns:
        A POSIX-style relative path when `path` lives under the current working
        directory, otherwise the original POSIX-style path.
    """

    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_compiler_command(compiler: Path) -> list[str]:
    """Resolve the executable command for a compiler wrapper path.

    Args:
        compiler: Wrapper or native compiler path, with or without a `.cmd`
            suffix on Windows.

    Returns:
        The subprocess command vector for invoking the compiler.

    Raises:
        SystemExit: If no matching compiler wrapper exists.
    """

    selected = compiler.expanduser()
    if not selected.is_absolute():
        selected = selected.resolve(strict=False)
    command = wrapper_command(selected)
    if not Path(command[0]).is_file():
        raise SystemExit(f"check_examples: missing compiler wrapper at {selected}")
    return command


def find_examples(examples_dir: Path, extension: str) -> list[Path]:
    """Return the top-level example files for one language subtree.

    Args:
        examples_dir: Directory containing example sources.
        extension: Required source-file suffix, including the leading dot.

    Returns:
        Sorted list of matching example files.

    Raises:
        SystemExit: If the directory is missing or contains no matching files.
    """

    if not examples_dir.is_dir():
        raise SystemExit(f"check_examples: missing examples directory: {examples_dir}")
    sources = sorted(path for path in examples_dir.iterdir() if path.is_file() and path.suffix == extension)
    if not sources:
        raise SystemExit(
            f"check_examples: no {extension} example sources found under {examples_dir.as_posix()}"
        )
    return sources


def is_warning_header(line: str) -> bool:
    """Report whether one compiler output line is a warning diagnostic header.

    Args:
        line: One merged stdout/stderr output line from the compiler process.

    Returns:
        `True` when the line looks like a compiler warning header.
    """

    stripped = line.strip()
    return stripped.startswith(WARNING_MARKER) or ": warning: [" in stripped


def run_check(compiler_command: list[str], source: Path) -> tuple[int, str, bool]:
    """Run `--check` for one source file.

    Args:
        compiler_command: Executable compiler command, already resolved for the
            current platform.
        source: Source file to check.

    Returns:
        Tuple of process return code, merged compiler output, and whether a
        warning diagnostic header was observed.
    """

    completed = subprocess.run(
        [*compiler_command, "--check", relative_text(source)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = completed.stdout or ""
    return completed.returncode, output, any(is_warning_header(line) for line in output.splitlines())


def check_examples(
    *,
    compiler: Path,
    examples_dir: Path,
    extension: str,
    label: str | None,
) -> int:
    """Run warning-free `--check` validation across all matching examples.

    Args:
        compiler: Compiler wrapper path.
        examples_dir: Directory containing example sources.
        extension: Required source-file suffix, including the leading dot.
        label: Optional human-readable compiler label.

    Returns:
        Process-style exit code.
    """

    compiler_command = resolve_compiler_command(compiler)
    sources = find_examples(examples_dir, extension)
    display_label = label or Path(compiler_command[0]).stem

    print(f"check_examples: checking {len(sources)} source(s) with {display_label}")
    failures: list[CheckFailure] = []
    for index, source in enumerate(sources, start=1):
        source_text = relative_text(source)
        print(f"[{index}/{len(sources)}] {source_text}")
        return_code, output, warning_found = run_check(compiler_command, source)
        if output:
            print(output, end="" if output.endswith("\n") else "\n")

        reasons: list[str] = []
        if return_code != 0:
            reasons.append(f"compiler exited with status {return_code}")
        if warning_found:
            reasons.append("warning diagnostics emitted")
        if reasons:
            failures.append(CheckFailure(source, "; ".join(reasons)))

    if failures:
        print(
            f"check_examples: FAIL: {len(failures)} of {len(sources)} source(s) produced warnings or errors",
            file=sys.stderr,
        )
        for failure in failures:
            print(f"  {relative_text(failure.source)}: {failure.reason}", file=sys.stderr)
        return 1

    print(f"check_examples: PASS: {len(sources)} source(s) passed without warnings or errors")
    return 0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the example checker.

    Returns:
        Parsed CLI namespace.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--examples-dir", type=Path, required=True)
    parser.add_argument("--extension", required=True)
    parser.add_argument("--label")
    return parser.parse_args()


def main() -> int:
    """Run the example checker CLI.

    Returns:
        Process-style exit code.
    """

    args = parse_args()
    return check_examples(
        compiler=args.compiler,
        examples_dir=args.examples_dir,
        extension=args.extension,
        label=args.label,
    )


if __name__ == "__main__":
    raise SystemExit(main())
