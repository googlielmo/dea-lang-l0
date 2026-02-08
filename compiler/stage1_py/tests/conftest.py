#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from l0_driver import L0Driver
from l0_paths import SourceSearchPaths


@pytest.fixture
def repo_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def runtime_dir(repo_root: Path) -> Path:
    return repo_root / "runtime"


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def write_l0_file(temp_project: Path):
    def _write(module_name: str, content: str) -> Path:
        parts = module_name.split(".")
        file_path = temp_project.joinpath(*parts).with_suffix(".l0")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(dedent(content))
        return file_path

    return _write


@pytest.fixture
def write_l0_file_to():
    """Write L0 source to a specific root directory.

    Usage for tests that need separate system/project roots:
        def test_something(write_l0_file_to, tmp_path):
            sys_root = tmp_path / "sys"
            sys_root.mkdir()
            write_l0_file_to(sys_root, "std.io", '''
                module std.io;
                func print() -> void { }
            ''')
    """

    def _write(root: Path, module_name: str, content: str) -> Path:
        parts = module_name.split(".")
        file_path = root.joinpath(*parts).with_suffix(".l0")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(dedent(content))
        return file_path

    return _write


@pytest.fixture
def search_paths(temp_project: Path, repo_root: Path) -> SourceSearchPaths:
    paths = SourceSearchPaths()
    paths.add_project_root(temp_project)
    paths.add_system_root(repo_root / "l0" / "stdlib")
    return paths


@pytest.fixture
def codegen_dir() -> Path:
    return Path(__file__).parent / "codegen"


@pytest.fixture
def codegen_search_paths(codegen_dir: Path, repo_root: Path) -> SourceSearchPaths:
    paths = SourceSearchPaths()
    paths.add_project_root(codegen_dir)
    paths.add_system_root(repo_root / "l0" / "stdlib")
    return paths


@pytest.fixture
def compile_and_run(runtime_dir: Path):
    def _compile_and_run(c_code: str, work_dir: Path) -> tuple[bool, str, str]:
        c_file = work_dir / "output.c"
        exe_file = work_dir / "output"

        c_file.write_text(c_code)

        result = subprocess.run(
            [
                "gcc",
                "-Wall",
                "-Wextra",
                "-std=c99",
                "-I",
                str(runtime_dir),
                str(c_file),
                "-o",
                str(exe_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return False, "", result.stderr

        result = subprocess.run(
            [str(exe_file)],
            capture_output=True,
            text=True,
            timeout=10,
        )

        return result.returncode == 0, result.stdout, result.stderr

    return _compile_and_run


@pytest.fixture
def analyze_single(temp_project: Path, repo_root: Path):
    """Analyze a single L0 module from source string.

    Usage:
        def test_something(analyze_single):
            result = analyze_single("main", '''
                module main;
                func f() -> int { return 42; }
            ''')
            assert not result.has_errors()
    """

    def _analyze(module_name: str, src: str):
        parts = module_name.split(".")
        file_path = temp_project.joinpath(*parts).with_suffix(".l0")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(dedent(src))

        driver = L0Driver()
        driver.search_paths.add_system_root(repo_root / "l0" / "stdlib")
        driver.search_paths.add_project_root(temp_project)
        return driver.analyze(module_name)

    return _analyze


@pytest.fixture
def codegen_single(analyze_single):
    """Analyze and generate C code for a single L0 module.

    Returns (c_code, diagnostics) tuple. c_code is None if analysis failed.

    Usage:
        def test_something(codegen_single):
            c_code, diags = codegen_single("main", '''
                module main;
                func f() -> int { return 42; }
            ''')
            assert c_code is not None
    """

    def _codegen(module_name: str, src: str):
        result = analyze_single(module_name, src)

        if result.has_errors():
            return None, result.diagnostics

        from l0_backend import Backend

        backend = Backend(result)
        c_code = backend.generate()
        return c_code, []

    return _codegen


def has_error_code(diagnostics, code: str) -> bool:
    """Check if any diagnostic contains the given error code.

    Args:
        diagnostics: List of Diagnostic objects
        code: Error code string like "TYP-0110" or "[TYP-0110]"

    Returns:
        True if any diagnostic message contains the error code
    """
    if not code.startswith("["):
        code = f"[{code}]"
    return any(code in d.message for d in diagnostics)
