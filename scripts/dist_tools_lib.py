#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Shared helpers for repo-local Dea build and install-prefix tool generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import stat


REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class DeaBuildLayout:
    """Resolved repo-local Dea build layout paths."""

    repo_root: Path
    dea_build_dir: Path
    bin_dir: Path
    dea_build_relative_from_repo: str
    repo_relative_from_bin: str


@dataclass(frozen=True)
class PrefixLayout:
    """Resolved Phase 3 install-prefix layout paths."""

    repo_root: Path
    prefix_dir: Path
    bin_dir: Path
    shared_dir: Path
    stdlib_dir: Path
    runtime_dir: Path


def normalize_dea_build_dir(dea_build_dir_text: str) -> DeaBuildLayout:
    """Return the normalized repo-local Dea build layout."""

    if not dea_build_dir_text.strip():
        raise ValueError("DEA_BUILD_DIR must not be empty")

    raw_path = Path(dea_build_dir_text)
    if raw_path.is_absolute():
        dea_build_dir = raw_path.resolve(strict=False)
    else:
        dea_build_dir = (REPO_ROOT / raw_path).resolve(strict=False)

    try:
        dea_build_dir.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(
            f"DEA_BUILD_DIR must resolve to a subdirectory inside the repository: {dea_build_dir}"
        ) from exc

    if dea_build_dir == REPO_ROOT:
        raise ValueError(
            f"DEA_BUILD_DIR must resolve to a subdirectory inside the repository: {dea_build_dir}"
        )

    bin_dir = dea_build_dir / "bin"
    dea_build_relative_from_repo = os.path.relpath(dea_build_dir, REPO_ROOT)
    repo_relative_from_bin = os.path.relpath(REPO_ROOT, bin_dir)
    return DeaBuildLayout(
        repo_root=REPO_ROOT,
        dea_build_dir=dea_build_dir,
        bin_dir=bin_dir,
        dea_build_relative_from_repo=dea_build_relative_from_repo,
        repo_relative_from_bin=repo_relative_from_bin,
    )


def normalize_prefix_dir(prefix_dir_text: str) -> PrefixLayout:
    """Return the normalized install-prefix layout."""

    if not prefix_dir_text.strip():
        raise ValueError("PREFIX must not be empty")

    raw_path = Path(prefix_dir_text)
    if raw_path.is_absolute():
        prefix_dir = raw_path.resolve(strict=False)
    else:
        prefix_dir = (REPO_ROOT / raw_path).resolve(strict=False)

    if prefix_dir == REPO_ROOT:
        raise ValueError("PREFIX must not resolve to the repository root")

    shared_dir = prefix_dir / "shared"
    return PrefixLayout(
        repo_root=REPO_ROOT,
        prefix_dir=prefix_dir,
        bin_dir=prefix_dir / "bin",
        shared_dir=shared_dir,
        stdlib_dir=shared_dir / "l0" / "stdlib",
        runtime_dir=shared_dir / "runtime",
    )


def ensure_dea_build_bin_dir(layout: DeaBuildLayout) -> None:
    """Create the Dea build bin directory when needed."""

    layout.bin_dir.mkdir(parents=True, exist_ok=True)


def ensure_prefix_bin_dir(layout: PrefixLayout) -> None:
    """Create the install-prefix bin directory when needed."""

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


def remove_dea_build_tree(layout: DeaBuildLayout) -> None:
    """Delete one validated repo-local Dea build tree."""

    shutil.rmtree(layout.dea_build_dir, ignore_errors=True)


def copy_tree(source: Path, destination: Path) -> None:
    """Replace one directory tree with a copy of another."""

    shutil.rmtree(destination, ignore_errors=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def copy_file(source: Path, destination: Path) -> None:
    """Copy one file into place, creating parent directories as needed."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def render_stage1_wrapper(layout: DeaBuildLayout) -> str:
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


def render_stage2_wrapper(layout: DeaBuildLayout) -> str:
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


def render_env_script(layout: DeaBuildLayout) -> str:
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
    echo "This script must be sourced: source {layout.dea_build_relative_from_repo}/bin/l0-env.sh" >&2
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


def render_prefix_stage2_wrapper() -> str:
    """Return the prefix-relative Stage 2 launcher."""

    return """#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
prefix_root=$(CDPATH= cd -- "${script_dir}/.." && pwd -P)

if [ -z "${L0_HOME:-}" ]; then
    export L0_HOME="${prefix_root}"
fi

exec "${script_dir}/l0c-stage2.native" "$@"
"""


def render_prefix_env_script() -> str:
    """Return the prefix-relative sourceable environment script."""

    return """#!/usr/bin/env bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

script_src="${BASH_SOURCE[0]-}"
if [[ -z "${script_src}" && -n "${ZSH_VERSION-}" ]]; then
    script_src="${(%):-%x}"
    if [[ -z "${script_src}" ]]; then
        script_src="${(%):-%N}"
    fi
fi

SCRIPT_DIR=""
PREFIX_DIR=""
if [[ -n "${script_src}" ]]; then
    SCRIPT_DIR="$(cd -- "$(dirname -- "${script_src}")" && pwd -P)"
    PREFIX_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
fi

sourced=0
if [[ -n "${BASH_VERSION-}" && "${BASH_SOURCE[0]-}" != "${0}" ]]; then
    sourced=1
fi
if [[ "${sourced}" -eq 0 && -n "${ZSH_VERSION-}" && "${ZSH_EVAL_CONTEXT-}" == *:file ]]; then
    sourced=1
fi

if [[ -z "${script_src}" || "${sourced}" -eq 0 ]]; then
    if [[ -n "${SCRIPT_DIR}" ]]; then
        echo "This script must be sourced: source ${SCRIPT_DIR}/l0-env.sh" >&2
    else
        echo "This script must be sourced: source <install-prefix>/bin/l0-env.sh" >&2
    fi
    return 1 2>/dev/null || exit 1
fi

export L0_HOME="${PREFIX_DIR}"

case ":${PATH}:" in
    *":${SCRIPT_DIR}:"*) ;;
    *) export PATH="${SCRIPT_DIR}${PATH:+:${PATH}}" ;;
esac

hash -r 2>/dev/null || true

# To pin down a specific C compiler, set the L0_CC environment variable here. For example:
#export L0_CC="clang"
"""


def write_stage1_wrapper(layout: DeaBuildLayout) -> Path:
    """Write the Stage 1 wrapper."""

    ensure_dea_build_bin_dir(layout)
    path = layout.bin_dir / "l0c-stage1"
    write_executable(path, render_stage1_wrapper(layout))
    return path


def write_stage2_wrapper(layout: DeaBuildLayout) -> Path:
    """Write the Stage 2 wrapper."""

    ensure_dea_build_bin_dir(layout)
    path = layout.bin_dir / "l0c-stage2"
    write_executable(path, render_stage2_wrapper(layout))
    return path


def write_env_script(layout: DeaBuildLayout) -> Path:
    """Write the repo-local Dea build environment script."""

    ensure_dea_build_bin_dir(layout)
    path = layout.bin_dir / "l0-env.sh"
    write_executable(path, render_env_script(layout))
    return path


def write_prefix_stage2_wrapper(layout: PrefixLayout) -> Path:
    """Write the installed Stage 2 wrapper."""

    ensure_prefix_bin_dir(layout)
    path = layout.bin_dir / "l0c-stage2"
    write_executable(path, render_prefix_stage2_wrapper())
    return path


def write_prefix_env_script(layout: PrefixLayout) -> Path:
    """Write the installed prefix environment script."""

    ensure_prefix_bin_dir(layout)
    path = layout.bin_dir / "l0-env.sh"
    write_executable(path, render_prefix_env_script())
    return path


def set_alias(layout: DeaBuildLayout, stage: str) -> Path:
    """Point `l0c` at the selected stage wrapper."""

    if stage not in {"stage1", "stage2"}:
        raise ValueError(f"unknown stage: {stage}")

    ensure_dea_build_bin_dir(layout)
    target_name = "l0c-stage1" if stage == "stage1" else "l0c-stage2"
    link_path = layout.bin_dir / "l0c"
    write_relative_symlink(link_path, target_name)
    return link_path


def set_prefix_alias(layout: PrefixLayout) -> Path:
    """Point installed `l0c` at the Stage 2 wrapper."""

    ensure_prefix_bin_dir(layout)
    link_path = layout.bin_dir / "l0c"
    write_relative_symlink(link_path, "l0c-stage2")
    return link_path


def copy_prefix_shared_assets(layout: PrefixLayout) -> None:
    """Copy the shared stdlib and runtime assets into the install prefix."""

    copy_tree(REPO_ROOT / "compiler" / "shared" / "l0" / "stdlib", layout.stdlib_dir)
    copy_tree(REPO_ROOT / "compiler" / "shared" / "runtime", layout.runtime_dir)


def install_prefix_stage2(layout: PrefixLayout, stage2_native_source: Path) -> Path:
    """Install the Stage 2 compiler and shared assets into one prefix."""

    ensure_prefix_bin_dir(layout)
    copy_file(stage2_native_source, layout.bin_dir / "l0c-stage2.native")
    copy_prefix_shared_assets(layout)
    write_prefix_stage2_wrapper(layout)
    write_prefix_env_script(layout)
    set_prefix_alias(layout)
    return layout.bin_dir / "l0c-stage2.native"
