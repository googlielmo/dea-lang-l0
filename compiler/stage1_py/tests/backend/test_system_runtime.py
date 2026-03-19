#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import os

import pytest


def test_system_runtime_returns_exit_code(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "system_runtime_returns_exit_code",
        """
        module system_runtime_returns_exit_code;

        import std.io;
        import std.system;

        func main() -> int {
            printl_i(system("sh -c 'exit 7'"));
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr
    assert stdout.strip().splitlines() == ["7"]


def test_system_runtime_get_pid_returns_positive_int(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "system_runtime_get_pid_returns_positive_int",
        """
        module system_runtime_get_pid_returns_positive_int;

        import std.io;
        import std.system;

        func main() -> int {
            printl_i(get_pid());
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr
    pid_lines = stdout.strip().splitlines()
    assert len(pid_lines) == 1
    assert int(pid_lines[0]) > 0


@pytest.mark.skipif(os.name == "nt", reason="signal status normalization is POSIX-specific")
def test_system_runtime_returns_signal_code(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "system_runtime_returns_signal_code",
        """
        module system_runtime_returns_signal_code;

        import std.io;
        import std.system;

        func main() -> int {
            printl_i(system("sh -c 'kill -INT $$'"));
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr
    assert stdout.strip().splitlines() == ["130"]
