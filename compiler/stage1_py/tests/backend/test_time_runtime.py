#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz


def test_time_wall_now_runtime(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "time_wall_now_runtime",
        """
        module time_wall_now_runtime;

        import std.time;
        import std.io;

        func main() -> int {
            let now_opt = wall_now();
            if (now_opt == null) {
                printl_i(-1);
                return 0;
            }

            let now = now_opt as WallTime;
            printl_i(now.nsec);
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr

    lines = stdout.strip().splitlines()
    assert len(lines) == 1
    nsec = int(lines[0])
    assert nsec >= 0
    assert nsec < 1_000_000_000


def test_time_utc_epoch_conversion_runtime(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "time_utc_epoch_conversion_runtime",
        """
        module time_utc_epoch_conversion_runtime;

        import std.time;
        import std.io;

        func print_is_dst(x: bool) {
            if (x) {
                printl_i(1);
            } else {
                printl_i(0);
            }
        }

        func main() -> int {
            let dt_opt = wall_to_utc_datetime(WallTime(0, 0));
            if (dt_opt == null) {
                printl_s("null");
                return 0;
            }

            let dt = dt_opt as DateTime;
            printl_i(dt.year);
            printl_i(dt.month);
            printl_i(dt.day);
            printl_i(dt.hour);
            printl_i(dt.minute);
            printl_i(dt.second);
            printl_i(dt.weekday);
            printl_i(dt.yearday);
            printl_i(dt.utc_offset_sec);
            print_is_dst(dt.is_dst);
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr

    lines = stdout.strip().splitlines()
    assert lines == [
        "1970",
        "1",
        "1",
        "0",
        "0",
        "0",
        "4",
        "1",
        "0",
        "0",
    ]


def test_time_invalid_nsec_rejected_runtime(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "time_invalid_nsec_rejected_runtime",
        """
        module time_invalid_nsec_rejected_runtime;

        import std.time;
        import std.io;

        func main() -> int {
            let bad1 = wall_to_utc_datetime(WallTime(0, -1));
            let bad2 = wall_to_utc_datetime(WallTime(0, 1000000000));
            printl_b(bad1 == null);
            printl_b(bad2 == null);
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr
    assert stdout.strip().splitlines() == ["true", "true"]


def test_time_monotonic_runtime_contract(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "time_monotonic_runtime_contract",
        """
        module time_monotonic_runtime_contract;

        import std.time;
        import std.io;

        func main() -> int {
            if (!monotonic_supported()) {
                printl_s("unsupported");
                return 0;
            }

            let a_opt = monotonic_now();
            let b_opt = monotonic_now();
            if (a_opt == null || b_opt == null) {
                printl_s("null");
                return 0;
            }

            let a = a_opt as MonotonicTime;
            let b = b_opt as MonotonicTime;
            let d_opt = monotonic_diff(a, b);
            if (d_opt == null) {
                printl_s("diff-null");
                return 0;
            }

            let d = d_opt as Duration;
            printl_i(d.sec);
            printl_i(d.nsec);
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr

    lines = stdout.strip().splitlines()
    assert len(lines) >= 1
    if lines[0] == "unsupported":
        return

    assert lines[0] != "null"
    assert lines[0] != "diff-null"
    assert len(lines) == 2
    sec = int(lines[0])
    nsec = int(lines[1])
    assert sec >= 0
    assert 0 <= nsec < 1_000_000_000


def test_time_codegen_uses_snapshot_calls(codegen_single):
    c_code, _ = codegen_single(
        "time_codegen_uses_snapshot_calls",
        """
        module time_codegen_uses_snapshot_calls;

        import std.time;

        func main() -> int {
            let _w = wall_now();
            let _m = monotonic_now();
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    assert "rt_time_unix(" in c_code
    assert "rt_time_monotonic(" in c_code
    assert "rt_time_unix_sec" not in c_code
    assert "rt_time_unix_nsec" not in c_code
    assert "rt_time_monotonic_sec" not in c_code
    assert "rt_time_monotonic_nsec" not in c_code
