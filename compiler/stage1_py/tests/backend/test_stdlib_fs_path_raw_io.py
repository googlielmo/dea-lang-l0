#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz


def test_shared_stdlib_path_and_fs_helpers_runtime(
    codegen_single, compile_and_run, tmp_path
):
    file_path = (tmp_path / "shared-stdlib-fs-path.txt").as_posix()
    missing_path = (tmp_path / "shared-stdlib-fs-path-missing.txt").as_posix()

    c_code, _ = codegen_single(
        "shared_stdlib_path_fs_helpers",
        f"""
        module shared_stdlib_path_fs_helpers;

        import std.fs;
        import std.io;
        import std.path;
        import std.string;

        func bool_to_int(v: bool) -> int {{
            if (v) {{
                return 1;
            }}
            return 0;
        }}

        func main() -> int {{
            printl_i(bool_to_int(is_sep('/' as byte)));
            printl_i(bool_to_int(is_sep('\\\\' as byte)));
            printl_i(bool_to_int(is_absolute("/tmp/demo.l0")));
            printl_i(bool_to_int(is_absolute("C:\\\\tmp\\\\demo.l0")));
            printl_i(bool_to_int(!is_absolute("demo.l0")));
            printl_i(bool_to_int(has_parent("src/demo.l0")));
            printl_s(basename("src/demo.l0"));
            printl_s(parent("src/demo.l0"));
            printl_s(stem("src/demo.name.l0"));
            printl_s(join("src", "demo.l0"));
            printl_i(bool_to_int(has_extension("src/demo.l0", ".l0")));
            printl_i(bool_to_int(has_extension("src/demo.l0", "l0")));
            printl_i(bool_to_int(!has_extension(".gitignore", "gitignore")));

            let missing = stat("{missing_path}");
            printl_i(bool_to_int(!missing.exists));

            let wrote = write_file("{file_path}", "abc");
            if (wrote == null) {{
                return 11;
            }}

            let info = stat("{file_path}");
            printl_i(bool_to_int(info.exists));
            printl_i(bool_to_int(info.is_file));
            printl_i(bool_to_int(!info.is_dir));
            printl_i(bool_to_int(is_dir(".")));

            let size = file_size("{file_path}");
            if (size == null) {{
                return 12;
            }}
            printl_i(size as int);

            let mtime = mtime_sec("{file_path}");
            if (mtime == null) {{
                printl_i(-1);
            }} else {{
                printl_i(bool_to_int((mtime as int) >= 0));
            }}

            let deleted = delete_file("{file_path}");
            if (deleted == null) {{
                return 13;
            }}
            printl_i(bool_to_int(!file_exists("{file_path}")));
            return 0;
        }}
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr
    assert stdout.splitlines() == [
        "1",
        "1",
        "1",
        "1",
        "1",
        "1",
        "demo.l0",
        "src",
        "demo.name",
        "src/demo.l0",
        "1",
        "1",
        "1",
        "1",
        "1",
        "1",
        "1",
        "1",
        "3",
        "1",
        "1",
    ]


def test_shared_raw_stdio_runtime(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "shared_raw_stdio_runtime",
        """
        module shared_raw_stdio_runtime;

        import std.io;
        import sys.unsafe;

        func main() -> int {
            with (
                let stdout_buf = rt_calloc(3, 1) as void* => rt_free(stdout_buf),
                let stderr_buf = rt_calloc(3, 1) as void* => rt_free(stderr_buf),
                let probe_buf = rt_calloc(1, 1) as void* => rt_free(probe_buf)
            ) {
                let out0 = rt_array_element(stdout_buf, 1, 0) as byte*;
                let out1 = rt_array_element(stdout_buf, 1, 1) as byte*;
                let out2 = rt_array_element(stdout_buf, 1, 2) as byte*;
                *out0 = 65 as byte;
                *out1 = 0 as byte;
                *out2 = 66 as byte;

                let err0 = rt_array_element(stderr_buf, 1, 0) as byte*;
                let err1 = rt_array_element(stderr_buf, 1, 1) as byte*;
                let err2 = rt_array_element(stderr_buf, 1, 2) as byte*;
                *err0 = 88 as byte;
                *err1 = 0 as byte;
                *err2 = 89 as byte;

                let wrote_stdout = write_stdout_some(stdout_buf as byte*, 3);
                if (wrote_stdout == null || (wrote_stdout as int) != 3) {
                    return 11;
                }

                let wrote_stderr = write_stderr_all(stderr_buf as byte*, 3);
                if (wrote_stderr == null) {
                    return 12;
                }

                let nread = read_stdin_some(probe_buf as byte*, 1);
                if (nread == null) {
                    return 13;
                }
                if ((nread as int) != 0) {
                    return 14;
                }
            }
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, stderr
    assert stdout == "A\x00B"
    assert stderr == "X\x00Y"
