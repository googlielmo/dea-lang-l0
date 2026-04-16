#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from pathlib import Path
from textwrap import dedent

pytest_plugins = ["pytester"]

REAL_CONFTEST = Path(__file__).resolve().parents[1] / "conftest.py"


def _install_real_stage1_conftest(pytester) -> None:
    pytester.makeconftest(
        dedent(
            f"""
import importlib.util
import sys

spec = importlib.util.spec_from_file_location(
    "l0_stage1_real_conftest",
    r"{REAL_CONFTEST}",
)
assert spec is not None
assert spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

for name in dir(module):
    if not name.startswith("__"):
        globals()[name] = getattr(module, name)
"""
        )
    )


def test_quiet_progress_replaces_final_percentage_with_done(pytester, monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)

    _install_real_stage1_conftest(pytester)
    pytester.makepyfile(
        """
def test_one():
    assert True


def test_two():
    assert True
"""
    )

    result = pytester.runpytest(
        "--quiet-progress",
        "-n",
        "2",
        "-o",
        "console_output_style=progress",
        "--color=yes",
    )

    result.assert_outcomes(passed=2)
    stdout = result.stdout.str()
    assert result.ret == 0
    assert "\ndone.\n" in stdout
    assert "done.\n\n" not in stdout
    assert "[100%]" not in stdout


def test_quiet_progress_q_reports_resolved_xdist_worker_count(pytester, monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)

    _install_real_stage1_conftest(pytester)
    pytester.makepyfile(
        """
def test_one():
    assert True
"""
    )

    result = pytester.runpytest(
        "--quiet-progress",
        "-q",
        "-n",
        "2",
    )

    result.assert_outcomes(passed=1)
    stdout = result.stdout.str()
    stderr = result.stderr.str()
    assert result.ret == 0
    assert "[L0] xdist workers: 2" in stdout + stderr
