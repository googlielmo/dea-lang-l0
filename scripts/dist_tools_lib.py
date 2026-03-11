#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Shared helpers for repo-local dist tool generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import stat


REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class DistLayout:
    """Resolved Phase 2 dist layout paths."""

    repo_root: Path
    dist_dir: Path
    bin_dir: Path
    dist_relative_from_repo: str
    repo_relative_from_bin: str


def normalize_dist_dir(dist_dir_text: str) -> DistLayout:
    """Return the normalized repo-local dist layout."""

    if not dist_dir_text.strip():
        raise ValueError("DIST_DIR must not be empty")

    raw_path = Path(dist_dir_text)
    if raw_path.is_absolute():
        dist_dir = raw_path.resolve(strict=False)
    else:
        dist_dir = (REPO_ROOT / raw_path).resolve(strict=False)

    try:
        dist_dir.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(
            f"DIST_DIR must resolve to a subdirectory inside the repository: {dist_dir}"
        ) from exc

    if dist_dir == REPO_ROOT:
        raise ValueError(
            f"DIST_DIR must resolve to a subdirectory inside the repository: {dist_dir}"
        )

    bin_dir = dist_dir / "bin"
    dist_relative_from_repo = os.path.relpath(dist_dir, REPO_ROOT)
    repo_relative_from_bin = os.path.relpath(REPO_ROOT, bin_dir)
    return DistLayout(
        repo_root=REPO_ROOT,
        dist_dir=dist_dir,
        bin_dir=bin_dir,
        dist_relative_from_repo=dist_relative_from_repo,
        repo_relative_from_bin=repo_relative_from_bin,
    )


def ensure_bin_dir(layout: DistLayout) -> None:
    """Create the dist bin directory when needed."""

    layout.bin_dir.mkdir(parents=True, exist_ok=True)


def write_executable(path: Path, text: str) -> None:
    """Write one executable text file."""

    path.write_text(text, encoding="utf-8")
    current_mode = path.stat().st_mode
    path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_relative_symlink(path: Path, target_name: str) -> None:
    """Write one sibling-relative symlink."""

    if path.exists() or path.is_symlink():
        path.unlink()
    path.symlink_to(target_name)


def remove_dist_tree(layout: DistLayout) -> None:
    """Delete one validated dist tree."""

    shutil.rmtree(layout.dist_dir, ignore_errors=True)


def render_stage1_wrapper(layout: DistLayout) -> str:
    """Return the repo-relative Stage 1 launcher."""

    return f"""#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(CDPATH= cd -- "${{script_dir}}/{layout.repo_relative_from_bin}" && pwd -P)

if [ -z "${{L0_HOME:-}}" ]; then
    export L0_HOME="${{repo_root}}/compiler"
fi

exec python3 "${{L0_HOME}}/stage1_py/l0c.py" "$@"
"""


def render_stage2_wrapper(layout: DistLayout) -> str:
    """Return the repo-relative Stage 2 launcher."""

    return f"""#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(CDPATH= cd -- "${{script_dir}}/{layout.repo_relative_from_bin}" && pwd -P)

if [ -z "${{L0_HOME:-}}" ]; then
    export L0_HOME="${{repo_root}}/compiler"
fi

exec "${{script_dir}}/l0c-stage2.native" "$@"
"""


def render_env_script(layout: DistLayout) -> str:
    """Return the repo-relative sourceable environment script."""

    return f"""#!/usr/bin/env bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

script_src="${{BASH_SOURCE[0]-}}"
if [[ -z "${{script_src}}" && -n "${{ZSH_VERSION-}}" ]]; then
    script_src="${{(%):-%x}}"
    if [[ -z "${{script_src}}" ]]; then
        script_src="${{(%):-%N}}"
    fi
fi

sourced=0
if [[ -n "${{BASH_VERSION-}}" && "${{BASH_SOURCE[0]-}}" != "${{0}}" ]]; then
    sourced=1
fi
if [[ "${{sourced}}" -eq 0 && -n "${{ZSH_VERSION-}}" && "${{ZSH_EVAL_CONTEXT-}}" == *:file ]]; then
    sourced=1
fi

if [[ -z "${{script_src}}" || "${{sourced}}" -eq 0 ]]; then
    echo "This script must be sourced: source {layout.dist_relative_from_repo}/bin/l0-env.sh" >&2
    return 1 2>/dev/null || exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${{script_src}}")" && pwd -P)"
REPO_ROOT="$(cd -- "${{SCRIPT_DIR}}/{layout.repo_relative_from_bin}" && pwd -P)"
export L0_HOME="${{REPO_ROOT}}/compiler"

if [[ -f "${{REPO_ROOT}}/.venv/bin/activate" ]]; then
    # shellcheck source=/dev/null
    . "${{REPO_ROOT}}/.venv/bin/activate"
fi

case ":${{PATH}}:" in
    *":${{SCRIPT_DIR}}:"*) ;;
    *) export PATH="${{SCRIPT_DIR}}${{PATH:+:${{PATH}}}}" ;;
esac

hash -r 2>/dev/null || true

# To pin down a specific C compiler, set the L0_CC environment variable here. For example:
#export L0_CC="clang"
"""


def write_stage1_wrapper(layout: DistLayout) -> Path:
    """Write the Stage 1 wrapper."""

    ensure_bin_dir(layout)
    path = layout.bin_dir / "l0c-stage1"
    write_executable(path, render_stage1_wrapper(layout))
    return path


def write_stage2_wrapper(layout: DistLayout) -> Path:
    """Write the Stage 2 wrapper."""

    ensure_bin_dir(layout)
    path = layout.bin_dir / "l0c-stage2"
    write_executable(path, render_stage2_wrapper(layout))
    return path


def write_env_script(layout: DistLayout) -> Path:
    """Write the dist environment script."""

    ensure_bin_dir(layout)
    path = layout.bin_dir / "l0-env.sh"
    write_executable(path, render_env_script(layout))
    return path


def set_alias(layout: DistLayout, stage: str) -> Path:
    """Point `l0c` at the selected stage wrapper."""

    if stage not in {"stage1", "stage2"}:
        raise ValueError(f"unknown stage: {stage}")

    ensure_bin_dir(layout)
    target_name = "l0c-stage1" if stage == "stage1" else "l0c-stage2"
    link_path = layout.bin_dir / "l0c"
    write_relative_symlink(link_path, target_name)
    return link_path
