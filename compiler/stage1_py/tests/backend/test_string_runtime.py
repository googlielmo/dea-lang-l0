#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz


def test_string_search_helpers_runtime(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "string_search_helpers",
        """
        module string_search_helpers;

        import std.io;
        import std.string;

        func bool_to_int(v: bool) -> int {
            if (v) {
                return 1;
            }
            return 0;
        }

        func main() -> int {
            printl_i(find_s("banana", "ana"));
            printl_i(find_s("banana", "xyz"));
            printl_i(find_s("banana", ""));

            printl_i(find_from_s("banana", "ana", 0));
            printl_i(find_from_s("banana", "ana", 2));
            printl_i(find_from_s("banana", "ana", 4));
            printl_i(find_from_s("banana", "", 6));
            printl_i(find_from_s("banana", "", 7));

            printl_i(bool_to_int(contains_s("banana", "nan")));
            printl_i(bool_to_int(contains_s("banana", "zzz")));

            printl_i(bool_to_int(starts_with_s("banana", "ban")));
            printl_i(bool_to_int(starts_with_s("banana", "ana")));
            printl_i(bool_to_int(starts_with_s("banana", "")));

            printl_i(bool_to_int(ends_with_s("banana", "ana")));
            printl_i(bool_to_int(ends_with_s("banana", "ban")));
            printl_i(bool_to_int(ends_with_s("banana", "")));
            printl_i(bool_to_int(ends_with_s("abcabc", "abc")));

            return 0;
        }
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr
    assert stdout.strip().splitlines() == [
        "1",
        "-1",
        "0",
        "1",
        "3",
        "-1",
        "6",
        "-1",
        "1",
        "0",
        "1",
        "0",
        "1",
        "1",
        "0",
        "1",
        "1",
    ]


def test_string_byte_conversions_runtime(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "string_byte_conversions",
        """
        module string_byte_conversions;

        import std.io;
        import std.string;
        import sys.unsafe;

        func main() -> int {
            let one: string = byte_to_s(65 as byte);
            printl_i(len_s(one));
            printl_i(char_at_s(one, 0) as int);

            let raw: void* = rt_calloc(3, 1) as void*;
            let b0: byte* = rt_array_element(raw, 1, 0) as byte*;
            let b1: byte* = rt_array_element(raw, 1, 1) as byte*;
            let b2: byte* = rt_array_element(raw, 1, 2) as byte*;
            *b0 = 88 as byte;
            *b1 = 89 as byte;
            *b2 = 90 as byte;

            let many: string = bytes_to_s(raw as byte*, 3);
            printl_i(len_s(many));
            printl_i(char_at_s(many, 0) as int);
            printl_i(char_at_s(many, 1) as int);
            printl_i(char_at_s(many, 2) as int);
            rt_free(raw);
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr
    assert stdout.strip().splitlines() == [
        "1",
        "65",
        "3",
        "88",
        "89",
        "90",
    ]


def test_std_io_stale_errno_does_not_cause_false_failures(
    codegen_single, compile_and_run, tmp_path
):
    missing_path = (tmp_path / "definitely-missing-for-errno-probe.txt").as_posix()
    valid_path = (tmp_path / "io-errno-probe.txt").as_posix()

    c_code, _ = codegen_single(
        "std_io_errno_probe",
        f"""
        module std_io_errno_probe;

        import std.io;
        import std.string;
        import sys.rt;

        func main() -> int {{
            // Seed errno with a failing file probe before std.io calls.
            let missing = rt_file_exists("{missing_path}");
            if (missing) {{
                return 11;
            }}

            let w = write_file("{valid_path}", "ok");
            if (w == null) {{
                printl_s("write-null");
                return 12;
            }}

            let rd = read_file("{valid_path}");
            if (rd == null) {{
                printl_s("read-null");
                return 13;
            }}

            if (!eq_s(rd as string, "ok")) {{
                printl_s("mismatch");
                return 14;
            }}

            printl_s("ok");
            return 0;
        }}
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr
    assert stdout.strip() == "ok"
