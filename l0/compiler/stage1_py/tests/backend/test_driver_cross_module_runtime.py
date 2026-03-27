#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_backend import Backend
from l0_driver import L0Driver


def test_cross_module_execution(tmp_path, write_l0_file, search_paths, compile_and_run):
    write_l0_file(
        "util.math",
        """
        module util.math;

        func add(a: int, b: int) -> int {
            return a + b;
        }
        """,
    )

    write_l0_file(
        "main",
        """
        module main;

        import std.io;
        import util.math;

        func main() -> int {
            let v: int = add(20, 22);
            printl_i(v);
            return v;
        }
        """,
    )

    driver = L0Driver(search_paths=search_paths)
    result = driver.analyze("main")
    assert not result.has_errors(), result.diagnostics

    backend = Backend(result)
    c_code = backend.generate()

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert stdout.strip().splitlines()[-1] == "42"
