#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_driver import L0Driver


def test_driver_load_single_file_basic(write_l0_file, temp_project):
    write_l0_file(
        "demo",
        """
        module demo;

        func main() -> int {
            return 0;
        }
        """,
    )
    path = temp_project / "demo.l0"

    driver = L0Driver()
    module = driver._load_single_file(path)

    assert module.name == "demo"
    assert module.imports == []
    assert len(module.decls) == 1


def test_driver_load_with_imports(write_l0_file, temp_project):
    write_l0_file(
        "top",
        """
        module top;
        import foo;
        import std.io;

        func main() -> int { return 1; }
        """,
    )
    path = temp_project / "top.l0"

    driver = L0Driver()
    module = driver._load_single_file(path)

    assert module.name == "top"
    assert [imp.name for imp in module.imports] == ["foo", "std.io"]
    assert len(module.decls) == 1


def test_driver_caches_by_module_name(write_l0_file, temp_project):
    write_l0_file(
        "cache_test",
        """
        module cache_test;

        func main() -> int { return 2; }
        """,
    )
    path = temp_project / "cache_test.l0"

    driver = L0Driver()
    module1 = driver._load_single_file(path)
    module2 = driver._load_single_file(path)

    # Same module object returned?
    # Stage 1: load_single_file always reparses, but cache should store the last result.
    assert "cache_test" in driver.module_cache
    assert driver.module_cache["cache_test"].name == "cache_test"

    # module1 and module2 are fresh parses, but the cached module must match
    cached = driver.module_cache["cache_test"]
    assert cached.name == module1.name == module2.name


def test_driver_accepts_utf8_bom(write_l0_file, temp_project):
    path = write_l0_file(
        "bom.main",
        """
        module bom.main;
        func main() -> int { return 0; }
        """,
    )
    path.write_text("\ufeff" + path.read_text(encoding="utf-8"), encoding="utf-8")

    driver = L0Driver()
    module = driver._load_single_file(path)

    assert module.name == "bom.main"


def test_driver_reports_non_utf8_source(write_l0_file, temp_project, repo_root):
    path = write_l0_file(
        "badenc.main",
        """
        module badenc.main;
        func main() -> int { return 0; }
        """,
    )
    path.write_bytes(b"module badenc.main;\nfunc main() -> int { return 0; }\n\xff")

    driver = L0Driver()
    driver.search_paths.add_system_root(repo_root / "l0" / "stdlib")
    driver.search_paths.add_project_root(temp_project)

    result = driver.analyze("badenc.main")

    assert result.has_errors()
    assert any("[DRV-0040]" in d.message for d in result.diagnostics)
