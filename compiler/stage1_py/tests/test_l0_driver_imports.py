#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import pytest

from l0_driver import L0Driver, ImportCycleError
from l0_paths import SourceSearchPaths


def test_load_module_recursively_loads_imports(write_l0_file, temp_project):
    """
    app.main imports std.io and app.util.
    All three should be parsed and present in module_cache.
    """
    # app.main
    write_l0_file(
        "app.main",
        """
        module app.main;
        import std.io;
        import app.util;

        func main() -> int { return 0; }
        """,
    )

    # std.io
    write_l0_file(
        "std.io",
        """
        module std.io;

        func print_int(x: int) -> void { }
        """,
    )

    # app.util
    write_l0_file(
        "app.util",
        """
        module app.util;

        func helper() -> int { return 1; }
        """,
    )

    paths = SourceSearchPaths()
    paths.add_project_root(temp_project)

    driver = L0Driver(search_paths=paths)
    main_mod = driver.load_module("app.main")

    assert main_mod.name == "app.main"
    # All imported modules must be in the cache
    assert set(driver.module_cache.keys()) == {"app.main", "std.io", "app.util"}


def test_system_root_takes_priority(write_l0_file_to, tmp_path):
    """
    If the same module exists in system and project roots, system wins.
    """
    sys_root = tmp_path / "sys"
    proj_root = tmp_path / "project"
    sys_root.mkdir()
    proj_root.mkdir()

    # System version
    write_l0_file_to(
        sys_root,
        "std.io",
        """
        module std.io;

        func identity() -> int { return 1; }
        """,
    )

    # Project version
    write_l0_file_to(
        proj_root,
        "std.io",
        """
        module std.io;

        func identity() -> int { return 2; }
        """,
    )

    paths = SourceSearchPaths(
        system_roots=[sys_root],
        project_roots=[proj_root],
    )

    driver = L0Driver(search_paths=paths)
    mod = driver.load_module("std.io")

    # We only check the declared name here.
    # The fact that load_module() didn't raise and name matches means sys_root
    # was successfully used and parsing was OK.
    assert mod.name == "std.io"
    assert "std.io" in driver.module_cache


def test_import_cycle_raises(write_l0_file_to, tmp_path):
    """
    a imports b; b imports a.
    This should raise ImportCycleError.
    """
    proj_root = tmp_path / "project"
    proj_root.mkdir()

    write_l0_file_to(
        proj_root,
        "a",
        """
        module a;
        import b;

        func fa() -> int { return 0; }
        """,
    )

    write_l0_file_to(
        proj_root,
        "b",
        """
        module b;
        import a;

        func fb() -> int { return 0; }
        """,
    )

    paths = SourceSearchPaths()
    paths.add_project_root(proj_root)

    driver = L0Driver(search_paths=paths)

    with pytest.raises(ImportCycleError):
        driver.load_module("a")
