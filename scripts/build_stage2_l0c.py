#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Build the repo-local Stage 2 compiler artifact."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

from dist_tools_lib import normalize_dist_dir, write_stage2_wrapper


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Build the repo-local Stage 2 compiler artifact.")
    return parser.parse_args()


def main() -> int:
    """Program entrypoint."""

    parse_args()

    dist_dir_text = os.environ.get("DIST_DIR", "build/stage2")
    keep_c = os.environ.get("KEEP_C", "0") == "1"

    try:
        layout = normalize_dist_dir(dist_dir_text)
    except ValueError as exc:
        print(f"build-stage2-l0c: {exc}", file=sys.stderr)
        return 1

    layout.bin_dir.mkdir(parents=True, exist_ok=True)

    native_bin = layout.bin_dir / "l0c-stage2.native"
    c_output = layout.bin_dir / "l0c-stage2.c"

    build_args = [
        "./scripts/l0c",
        "--build",
        "-P",
        "compiler/stage2_l0/src",
        "-o",
        str(native_bin),
        "l0c",
    ]
    if keep_c:
        build_args.insert(1, "--keep-c")
    else:
        c_output.unlink(missing_ok=True)

    subprocess.run(build_args, cwd=layout.repo_root, check=True)

    if not keep_c:
        c_output.unlink(missing_ok=True)

    wrapper_bin = write_stage2_wrapper(layout)
    native_bin.chmod(native_bin.stat().st_mode | 0o111)

    print(f"build-stage2-l0c: wrote {wrapper_bin}")
    print(f"build-stage2-l0c: wrote {native_bin}")
    if keep_c:
        print(f"build-stage2-l0c: wrote {c_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
