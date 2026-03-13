#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Build the repo-local Stage 2 compiler artifact."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import os
from pathlib import Path
import subprocess
import sys

from dist_tools_lib import DeaBuildLayout, normalize_dea_build_dir, stage2_build_info_overlay, write_stage2_wrapper


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Build the repo-local Stage 2 compiler artifact.")
    return parser.parse_args()


def build_stage2_artifact(
        layout: DeaBuildLayout,
        *,
        keep_c: bool,
        extra_project_roots: Sequence[str] | None = None,
        extra_env: Mapping[str, str] | None = None,
) -> tuple[Path, Path, Path]:
    """Build the repo-local Stage 2 compiler artifact for one validated layout."""

    layout.bin_dir.mkdir(parents=True, exist_ok=True)

    native_bin = layout.bin_dir / "l0c-stage2.native"
    c_output = layout.bin_dir / "l0c-stage2.c"

    build_args = ["./scripts/l0c", "--build"]
    if keep_c:
        build_args.append("--keep-c")
    else:
        c_output.unlink(missing_ok=True)
    for root in extra_project_roots or ():
        build_args.extend(["-P", root])
    build_args.extend(["-P", "compiler/stage2_l0/src", "-o", str(native_bin), "l0c"])

    build_env = os.environ.copy()
    if extra_env is not None:
        build_env.update(extra_env)
    build_env["L0_HOME"] = str(layout.repo_root / "compiler")
    build_env.pop("L0_SYSTEM", None)
    build_env.pop("L0_RUNTIME_INCLUDE", None)
    build_env.pop("L0_RUNTIME_LIB", None)

    subprocess.run(build_args, cwd=layout.repo_root, env=build_env, check=True)

    if not keep_c:
        c_output.unlink(missing_ok=True)

    wrapper_bin = write_stage2_wrapper(layout)
    native_bin.chmod(native_bin.stat().st_mode | 0o111)
    return wrapper_bin, native_bin, c_output


def main() -> int:
    """Program entrypoint."""

    parse_args()

    dea_build_dir_text = os.environ.get("DEA_BUILD_DIR", "build/dea")
    keep_c = os.environ.get("KEEP_C", "0") == "1"

    try:
        layout = normalize_dea_build_dir(dea_build_dir_text)
    except ValueError as exc:
        print(f"build-stage2-l0c: {exc}", file=sys.stderr)
        return 1

    build_root = layout.repo_root / "build"
    build_root.mkdir(parents=True, exist_ok=True)
    try:
        with stage2_build_info_overlay(layout.repo_root, os.environ.copy(), temp_parent=build_root) as overlay:
            wrapper_bin, native_bin, c_output = build_stage2_artifact(
                layout,
                keep_c=keep_c,
                extra_project_roots=[str(overlay.overlay_root)],
                extra_env=overlay.build_env,
            )
    except ValueError as exc:
        print(f"build-stage2-l0c: {exc}", file=sys.stderr)
        return 1

    print(f"build-stage2-l0c: wrote {wrapper_bin}")
    print(f"build-stage2-l0c: wrote {native_bin}")
    if keep_c:
        print(f"build-stage2-l0c: wrote {c_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
