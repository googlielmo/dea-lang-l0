#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Shared helpers for repo-local Dea build and install-prefix tool generation."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import platform
import shlex
import shutil
import stat
import subprocess
import tempfile


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


@dataclass(frozen=True)
class Stage2BuildProvenance:
    """Resolved build-provenance fields embedded into artifact-producing Stage 2 binaries."""

    commit_full: str
    commit_short: str
    tree_state: str
    build_id: str
    build_time: str
    host: str
    compiler_banner: str
    has_embedded_version: bool


@dataclass(frozen=True)
class Stage2BuildInfoOverlay:
    """One temporary overlay root plus the exact build env used with it."""

    overlay_root: Path
    build_env: dict[str, str]
    provenance: Stage2BuildProvenance


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


def resolve_host_c_compiler(env: dict[str, str]) -> str | None:
    """Resolve the exact host C compiler command using the shared precedence contract."""

    from_env = env.get("L0_CC", "").strip()
    if from_env:
        return from_env

    path_text = env.get("PATH")
    for candidate in ("tcc", "gcc", "clang", "cc"):
        if shutil.which(candidate, path=path_text):
            return candidate

    from_cc = env.get("CC", "").strip()
    if from_cc:
        return from_cc
    return None


def _capture_first_line(command: list[str], *, cwd: Path, env: dict[str, str]) -> str | None:
    """Return the first non-empty output line for one subprocess, or `None` on failure."""

    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        return None

    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _git_output(repo_root: Path, env: dict[str, str], *args: str) -> str | None:
    """Return stripped git stdout for one repo-relative command, or `None` on failure."""

    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def format_host_triplet(kernel_name: str, kernel_release: str, machine: str) -> str:
    """Format the compact host triplet used by the Stage 2 `--version` output."""

    return " ".join((kernel_name, kernel_release, machine))


def _host_platform_text(repo_root: Path, env: dict[str, str]) -> str:
    """Return the recorded host platform text with the compact uname triplet contract."""

    if os.name != "nt":
        uname_parts: list[str] = []
        for flag in ("-s", "-r", "-m"):
            value = _capture_first_line(["uname", flag], cwd=repo_root, env=env)
            if value is None:
                uname_parts = []
                break
            uname_parts.append(value)
        if len(uname_parts) == 3:
            return format_host_triplet(uname_parts[0], uname_parts[1], uname_parts[2])

    return format_host_triplet(
        platform.system().strip() or "unknown",
        platform.release().strip() or "unknown",
        platform.machine().strip() or "unknown",
    )


def _compiler_banner_text(repo_root: Path, env: dict[str, str], compiler_text: str) -> str:
    """Return the first line of `<compiler> --version`, or `unknown` when unavailable."""

    try:
        compiler_words = shlex.split(compiler_text)
    except ValueError:
        return "unknown"
    if not compiler_words:
        return "unknown"

    version_line = _capture_first_line([*compiler_words, "--version"], cwd=repo_root, env=env)
    if version_line:
        return version_line
    return "unknown"


def format_build_time_utc(timestamp: datetime) -> str:
    """Render one UTC datetime for the Stage 2 `build time:` line."""

    return timestamp.astimezone(timezone.utc).isoformat(sep=" ", timespec="seconds")


def format_commit_for_version(commit_full: str, tree_state: str) -> str:
    """Return the Stage 2 `commit:` field text."""

    if tree_state == "dirty" and commit_full != "unknown":
        return f"{commit_full}+dirty"
    return commit_full


def _sanitize_build_id_component(text: str, default: str = "unknown") -> str:
    """Normalize one build-id component to a shell- and log-friendly token."""

    stripped = text.strip()
    if not stripped:
        return default
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in stripped)


def _derive_build_id(env: dict[str, str], commit_short: str, build_stamp: str) -> str:
    """Return the build identifier following the approved precedence order."""

    explicit = env.get("DEA_BUILD_ID", "").strip()
    if explicit:
        return explicit

    if env.get("GITHUB_ACTIONS") == "true":
        return (
            "gha-"
            f"{_sanitize_build_id_component(env.get('GITHUB_RUN_ID', ''))}."
            f"{_sanitize_build_id_component(env.get('GITHUB_RUN_ATTEMPT', ''))}-"
            f"{_sanitize_build_id_component(env.get('GITHUB_JOB', ''))}-"
            f"{_sanitize_build_id_component(env.get('RUNNER_OS', ''))}-"
            f"{_sanitize_build_id_component(env.get('RUNNER_ARCH', ''))}"
        )

    if commit_short != "unknown":
        return f"{commit_short}-{build_stamp}"
    return f"local-{build_stamp}"


def collect_stage2_build_provenance(repo_root: Path, env: dict[str, str]) -> tuple[Stage2BuildProvenance, str]:
    """Capture one build-provenance snapshot for Stage 2 artifact-producing flows."""

    resolved_compiler = resolve_host_c_compiler(env)
    if resolved_compiler is None:
        raise ValueError("no host C compiler found; set L0_CC or CC")

    git_env = env.copy()
    git_env.setdefault("LC_ALL", "C")
    git_env.setdefault("LANG", "C")

    commit_full = _git_output(repo_root, git_env, "rev-parse", "HEAD") or "unknown"
    commit_short = _git_output(repo_root, git_env, "rev-parse", "--short", "HEAD") or "unknown"

    status_output = _git_output(repo_root, git_env, "status", "--porcelain", "--untracked-files=normal")
    if status_output is None:
        tree_state = "unknown"
    elif status_output == "":
        tree_state = "clean"
    else:
        tree_state = "dirty"

    build_timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    build_stamp = build_timestamp.strftime("%Y%m%dT%H%M%SZ")
    build_time = format_build_time_utc(build_timestamp)
    host = _host_platform_text(repo_root, env)
    compiler_banner = _compiler_banner_text(repo_root, env, resolved_compiler)
    build_id = _derive_build_id(env, commit_short, build_stamp)

    required_fields = (build_id, build_time, host, compiler_banner)
    has_embedded_version = all(field and field != "unknown" for field in required_fields)

    return Stage2BuildProvenance(
        commit_full=commit_full,
        commit_short=commit_short,
        tree_state=tree_state,
        build_id=build_id,
        build_time=build_time,
        host=host,
        compiler_banner=compiler_banner,
        has_embedded_version=has_embedded_version,
    ), resolved_compiler


def _render_l0_string(text: str) -> str:
    """Render one Python string as an escaped L0 string literal."""

    return json.dumps(text, ensure_ascii=True)


def render_stage2_build_info_module(provenance: Stage2BuildProvenance) -> str:
    """Render one overlay `build_info.l0` module for embedded Stage 2 provenance."""

    enabled = "true" if provenance.has_embedded_version else "false"
    commit_text = format_commit_for_version(provenance.commit_full, provenance.tree_state)
    return f"""/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * Copyright (c) 2026 gwz
 */

module build_info;

import std.text;

func build_info_has_embedded_version() -> bool {{
    return {enabled};
}}

func build_info_build_id() -> string {{
    return {_render_l0_string(provenance.build_id)};
}}

func build_info_build_time() -> string {{
    return {_render_l0_string(provenance.build_time)};
}}

func build_info_commit() -> string {{
    return {_render_l0_string(commit_text)};
}}

func build_info_host() -> string {{
    return {_render_l0_string(provenance.host)};
}}

func build_info_compiler() -> string {{
    return {_render_l0_string(provenance.compiler_banner)};
}}

func build_info_version_text(identity: string) -> string? {{
    if (!build_info_has_embedded_version()) {{
        return null;
    }}

    with (let sb = sb_create() => sb_free(sb)) {{
        sb_append(sb, identity);
        sb_append(sb, "\\nbuild: ");
        sb_append(sb, build_info_build_id());
        sb_append(sb, "\\nbuild time: ");
        sb_append(sb, build_info_build_time());
        sb_append(sb, "\\ncommit: ");
        sb_append(sb, build_info_commit());
        sb_append(sb, "\\nhost: ");
        sb_append(sb, build_info_host());
        sb_append(sb, "\\ncompiler: ");
        sb_append(sb, build_info_compiler());
        return sb_to_string(sb);
    }}
}}
"""


@contextmanager
def stage2_build_info_overlay(
        repo_root: Path,
        env: dict[str, str],
        *,
        temp_parent: Path | None = None,
):
    """Yield one temporary overlay root and exact build env for embedded provenance builds."""

    provenance, resolved_compiler = collect_stage2_build_provenance(repo_root, env)
    temp_dir = Path(tempfile.mkdtemp(prefix="stage2_build_info.", dir=temp_parent))
    try:
        overlay_root = temp_dir.resolve(strict=False)
        (overlay_root / "build_info.l0").write_text(
            render_stage2_build_info_module(provenance),
            encoding="utf-8",
        )
        build_env = env.copy()
        build_env["L0_CC"] = resolved_compiler
        yield Stage2BuildInfoOverlay(
            overlay_root=overlay_root,
            build_env=build_env,
            provenance=provenance,
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


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
