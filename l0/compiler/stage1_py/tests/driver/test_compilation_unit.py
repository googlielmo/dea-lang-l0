#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import textwrap
from pathlib import Path

from l0_driver import L0Driver
from l0_paths import SourceSearchPaths


def _write(tmp_root: Path, rel: str, content: str) -> Path:
    path = tmp_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


def test_compilation_unit_collects_transitive_modules(tmp_path):
    """
    app.main -> app.util -> std.io

    The CompilationUnit should contain all three modules, with app.main as entry.
    """
    proj_root = tmp_path / "project"
    proj_root.mkdir()

    _write(
        proj_root,
        "app/main.l0",
        """
        module app.main;
        import app.util;

        func main() -> int { return 0; }
        """,
    )

    _write(
        proj_root,
        "app/util.l0",
        """
        module app.util;
        import std.io;

        func helper() -> int { return 1; }
        """,
    )

    _write(
        proj_root,
        "std/io.l0",
        """
        module std.io;

        func print_int(x: int) -> void { }
        """,
    )

    paths = SourceSearchPaths()
    paths.add_project_root(proj_root)

    driver = L0Driver(search_paths=paths)
    cu = driver.build_compilation_unit("app.main")

    assert cu.entry_name == "app.main"
    assert set(cu.modules.keys()) == {"app.main", "app.util", "std.io"}
    # Sanity: entry module in modules mapping
    assert cu.entry_name in cu.modules


def test_compilation_unit_ignores_unrelated_cached_modules(tmp_path):
    """
    If a module was loaded before but is not reachable from the entry,
    it should not appear in the CompilationUnit.
    """
    proj_root = tmp_path / "project"
    proj_root.mkdir()

    # Entry and its dependency
    _write(
        proj_root,
        "app/main.l0",
        """
        module app.main;
        import app.util;

        func main() -> int { return 0; }
        """,
    )

    _write(
        proj_root,
        "app/util.l0",
        """
        module app.util;

        func helper() -> int { return 1; }
        """,
    )

    # Unrelated module
    _write(
        proj_root,
        "other/extra.l0",
        """
        module other.extra;

        func f() -> int { return 42; }
        """,
    )

    paths = SourceSearchPaths()
    paths.add_project_root(proj_root)

    driver = L0Driver(search_paths=paths)

    # Load unrelated module first, so it is in the cache
    extra = driver.load_module("other.extra")
    assert extra.name == "other.extra"
    assert "other.extra" in driver.module_cache

    # Now build compilation unit for app.main
    cu = driver.build_compilation_unit("app.main")

    assert cu.entry_name == "app.main"
    assert "other.extra" not in cu.modules
    assert set(cu.modules.keys()) == {"app.main", "app.util"}
