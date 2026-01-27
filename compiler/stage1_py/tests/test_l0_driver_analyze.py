#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_driver import L0Driver
from l0_paths import SourceSearchPaths


def test_analyze_success(write_l0_file, temp_project):
    write_l0_file(
        "main",
        """
        module main;

        func main() -> int { return 0; }
        """,
    )

    paths = SourceSearchPaths()
    paths.add_project_root(temp_project)

    driver = L0Driver(search_paths=paths)
    result = driver.analyze("main")

    assert result.cu is not None
    assert not result.has_errors()
    assert "main" in result.module_envs
    # Function env for main should exist
    assert ("main", "main") in result.func_envs


def test_analyze_missing_module(temp_project):
    paths = SourceSearchPaths()
    paths.add_project_root(temp_project)

    driver = L0Driver(search_paths=paths)
    result = driver.analyze("does.not.exist")

    assert result.cu is None
    assert result.diagnostics
    assert any("not found" in d.message for d in result.diagnostics)
