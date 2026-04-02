#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Helpers for resolving bootstrap compiler commands across language levels."""

from __future__ import annotations

import os
from pathlib import Path


def is_windows_host() -> bool:
    """Return whether the current Python host is Windows."""

    return os.name == "nt"


def wrapper_command(path: Path) -> list[str]:
    """Return the executable command for one wrapper/native base path."""

    if path.suffix.lower() == ".cmd":
        return [str(path)]
    if is_windows_host():
        cmd_path = path.with_suffix(".cmd")
        if cmd_path.is_file():
            return [str(cmd_path)]
    return [str(path)]


def resolve_bootstrap_compiler(
    *,
    override_text: str | None,
    default_path: Path,
    env_var_name: str,
    setup_hint: str,
) -> tuple[Path, list[str]]:
    """Resolve one explicit-or-default bootstrap compiler command."""

    selected = Path(override_text).expanduser() if override_text else default_path
    if not selected.is_absolute():
        selected = selected.resolve(strict=False)

    if selected.is_file():
        return selected, wrapper_command(selected)

    if is_windows_host():
        cmd_path = selected.with_suffix(".cmd")
        if cmd_path.is_file():
            return selected, [str(cmd_path)]

    raise RuntimeError(
        f"missing bootstrap compiler at {selected}; set {env_var_name} or {setup_hint}"
    )
