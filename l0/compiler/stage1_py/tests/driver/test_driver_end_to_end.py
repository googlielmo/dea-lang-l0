#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import pytest

from l0_driver import L0Driver, ImportCycleError
from l0_paths import SourceSearchPaths


def test_multi_module_project_with_system_and_project_roots(write_l0_file_to, tmp_path):
    """
    System root provides std.io.
    Project root provides app.util and app.main (which imports both).
    Driver should load all three modules and populate the cache.
    """
    sys_root = tmp_path / "sys"
    proj_root = tmp_path / "project"
    sys_root.mkdir()
    proj_root.mkdir()

    # System std.io
    write_l0_file_to(
        sys_root,
        "std.io",
        """
        module std.io;

        func print_int(x: int) -> void { }
        """,
    )

    # Project app.util
    write_l0_file_to(
        proj_root,
        "app.util",
        """
        module app.util;

        func helper() -> int { return 1; }
        """,
    )

    # Project app.main importing both std.io and app.util
    write_l0_file_to(
        proj_root,
        "app.main",
        """
        module app.main;
        import std.io;
        import app.util;

        func main() -> int {
            return 0;
        }
        """,
    )

    paths = SourceSearchPaths(
        system_roots=[sys_root],
        project_roots=[proj_root],
    )

    driver = L0Driver(search_paths=paths)
    main_mod = driver.load_module("app.main")

    assert main_mod.name == "app.main"
    # All transitively imported modules should have been loaded
    assert set(driver.module_cache.keys()) == {"app.main", "app.util", "std.io"}


def test_missing_module_raises_file_not_found(tmp_path):
    """
    Asking for a module that does not exist in system or project roots
    should raise FileNotFoundError.
    """
    proj_root = tmp_path / "project"
    proj_root.mkdir()

    paths = SourceSearchPaths()
    paths.add_project_root(proj_root)

    driver = L0Driver(search_paths=paths)

    with pytest.raises(FileNotFoundError):
        driver.load_module("does.not.exist")


def test_module_name_mismatch_raises_value_error(write_l0_file_to, tmp_path):
    """
    If the file exists but the declared module name does not match the
    requested module name, the driver should raise ValueError.
    """
    proj_root = tmp_path / "project"
    proj_root.mkdir()

    # File is where 'foo.correct' would be, but declares 'module foo.wrong;'
    write_l0_file_to(
        proj_root,
        "foo.correct",
        """
        module foo.wrong;

        func f() -> int { return 0; }
        """,
    )

    paths = SourceSearchPaths()
    paths.add_project_root(proj_root)

    driver = L0Driver(search_paths=paths)

    with pytest.raises(ValueError) as excinfo:
        driver.load_module("foo.correct")

    # Optional: check the error message mentions both names
    msg = str(excinfo.value)
    assert "foo.wrong" in msg
    assert "foo.correct" in msg


def test_import_cycle_still_raises_import_cycle_error(write_l0_file_to, tmp_path):
    """
    Sanity check: cycles are detected at the driver level.
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
