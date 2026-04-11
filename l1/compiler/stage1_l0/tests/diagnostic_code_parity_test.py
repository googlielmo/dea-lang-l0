#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Check L1 Stage 1 diagnostic-code parity with the Python L0 oracle, excluding LEX-0060."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
L1_ROOT = REPO_ROOT / "l1"


def main() -> int:
    build_dir = Path(os.environ.get("L1_BUILD_DIR", "build/dea"))
    if not build_dir.is_absolute():
        build_dir = L1_ROOT / build_dir
    compiler = build_dir / "bin" / "l1c-stage1"
    return subprocess.run(
        [str(REPO_ROOT / ".venv" / "bin" / "python"), str(REPO_ROOT / "scripts" / "diagnostic_parity.py"),
         "--stage", "l1", "--compiler", str(compiler)],
        cwd=REPO_ROOT,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
