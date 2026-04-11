#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Check L0 Stage 2 diagnostic-code parity with the Python L0 oracle."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
L0_ROOT = REPO_ROOT / "l0"


def main() -> int:
    build_dir = Path(os.environ.get("DEA_BUILD_DIR", "build/dea"))
    if not build_dir.is_absolute():
        build_dir = L0_ROOT / build_dir
    compiler = build_dir / "bin" / "l0c-stage2"
    return subprocess.run(
        [str(REPO_ROOT / ".venv" / "bin" / "python"), str(REPO_ROOT / "scripts" / "diagnostic_parity.py"),
         "--stage", "l0", "--compiler", str(compiler)],
        cwd=REPO_ROOT,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
