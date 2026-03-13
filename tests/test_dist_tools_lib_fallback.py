#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Focused regression for Stage 2 provenance fallback without Git availability."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dist_tools_lib import collect_stage2_build_provenance, render_stage2_build_info_module


def fail(message: str) -> None:
    raise SystemExit(f"test_dist_tools_lib_fallback: FAIL: {message}")


def fake_subprocess_run(command: list[str], **_: object) -> SimpleNamespace:
    tool = command[0]
    if tool == "git":
        raise FileNotFoundError("git")
    if tool == "uname":
        mapping = {
            "-s": "Darwin\n",
            "-r": "24.6.0\n",
            "-m": "x86_64\n",
        }
        return SimpleNamespace(returncode=0, stdout=mapping[command[1]], stderr="")
    if tool == "gcc":
        return SimpleNamespace(
            returncode=0,
            stdout="gcc-15 (Homebrew GCC 15.2.0_1) 15.2.0\n",
            stderr="",
        )
    fail(f"unexpected subprocess command: {command!r}")


def main() -> int:
    env = os.environ.copy()
    env["L0_CC"] = "gcc"

    with patch("dist_tools_lib.subprocess.run", side_effect=fake_subprocess_run):
        provenance, resolved_compiler = collect_stage2_build_provenance(REPO_ROOT, env)

    if resolved_compiler != "gcc":
        fail(f"expected resolved compiler 'gcc', got {resolved_compiler!r}")
    if provenance.commit_full != "unknown":
        fail(f"expected unknown commit without git, got {provenance.commit_full!r}")
    if provenance.tree_state != "unknown":
        fail(f"expected unknown tree state without git, got {provenance.tree_state!r}")
    if not provenance.build_id.startswith("local-"):
        fail(f"expected local fallback build id, got {provenance.build_id!r}")
    if provenance.build_time.endswith("+00:00") is False:
        fail(f"expected UTC offset build time, got {provenance.build_time!r}")
    if provenance.host != "Darwin 24.6.0 x86_64":
        fail(f"unexpected host text: {provenance.host!r}")
    if provenance.compiler_banner != "gcc-15 (Homebrew GCC 15.2.0_1) 15.2.0":
        fail(f"unexpected compiler banner: {provenance.compiler_banner!r}")
    if not provenance.has_embedded_version:
        fail("expected embedded version output to remain enabled without git metadata")

    rendered = render_stage2_build_info_module(provenance)
    for expected in ("build: ", "build time: ", "commit: ", "host: ", "compiler: "):
        if expected not in rendered:
            fail(f"expected {expected!r} in rendered build_info module")
    if 'func build_info_commit() -> string {\n    return "unknown";\n}' not in rendered:
        fail("expected rendered build_info module to embed an unknown commit field")
    if 'func build_info_host() -> string {\n    return "Darwin 24.6.0 x86_64";\n}' not in rendered:
        fail("expected rendered build_info module to embed the compact host triplet")
    if 'func build_info_compiler() -> string {\n    return "gcc-15 (Homebrew GCC 15.2.0_1) 15.2.0";\n}' not in rendered:
        fail("expected rendered build_info module to embed the compiler banner")

    print("test_dist_tools_lib_fallback: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
