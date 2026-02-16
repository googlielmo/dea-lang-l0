#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_backend import Backend
from l0_driver import L0Driver


def test_arithmetic_overflow_aborts(tmp_path, write_l0_file, search_paths, compile_and_run):
    write_l0_file(
        "overflow",
        """
        module overflow;

        import std.io;

        func main() -> int {
            let max: int = 2147483647;
            let y: int = max + 1;
            printl_i(y);
            return 0;
        }
        """,
    )

    driver = L0Driver(search_paths=search_paths)
    result = driver.analyze("overflow")
    assert not result.has_errors(), result.diagnostics

    backend = Backend(result)
    c_code = backend.generate()

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert "Software Failure: integer addition overflow" in stderr.strip().splitlines()[-1]


def test_nested_control_flow_executes(tmp_path, write_l0_file, search_paths, compile_and_run):
    write_l0_file(
        "control",
        """
        module control;

        import std.io;

        enum Flag { Yes(); No(); }

        func inner(v: int) -> int {
            if (v > 10) {
                match (Yes()) {
                    Yes() => { return 1; }
                    No() => { return -1; }
                }
            } else {
                return 0;
            }
        }

        func main() -> int {
            let res: int = 0;
            if (true) {
                if (false) {
                    res = -10;
                } else {
                    res = inner(20);
                }
            } else {
                res = inner(5);
            }
            printl_i(res);
            return 0;
        }
        """,
    )

    driver = L0Driver(search_paths=search_paths)
    result = driver.analyze("control")
    assert not result.has_errors(), result.diagnostics

    backend = Backend(result)
    c_code = backend.generate()

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr
    assert stdout.strip().splitlines()[-1] == "1"
