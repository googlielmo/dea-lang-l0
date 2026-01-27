#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

def test_codegen_enum_tagging_and_match_switch(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        enum Option { None; Some(value: int); }

        func main() -> int {
            let opt: Option = Some(42);
            match (opt) {
                None => { return 0; }
                Some(v) => { return v; }
            }
        }
        """,
    )

    if c_code is None:
        return

    assert "enum l0_main_Option_tag" in c_code
    assert "l0_main_Option_None" in c_code
    assert "l0_main_Option_Some" in c_code
    assert "switch (_scrutinee.tag)" in c_code


def test_codegen_struct_field_access_and_nullability(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        struct Point { x: int; }

        func get_x(p: Point) -> int { return p.x; }
        func get_x_ptr(p: Point*) -> int { return p.x; }

        func main() -> int {
            let n: int? = null;
            let p: int*? = null;
            return get_x(new Point(1));
        }
        """,
    )

    if c_code is None:
        return

    assert "(p).x" in c_code
    assert "(p)->x" in c_code
    assert "l0_opt_int" in c_code
    assert "l0_int* p = NULL;" in c_code


def test_codegen_string_refcounts_and_cleanup_order(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        func main() -> int {
            let a: string = "a";
            let b: string = a;
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    assert "rt_string_retain(b);" in c_code

    b_release = c_code.find("rt_string_release(b);")
    a_release = c_code.find("rt_string_release(a);")
    assert b_release != -1 and a_release != -1
    assert b_release < a_release


def test_codegen_struct_cleanup_order_for_owned_fields(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        struct Pair {
            first: string;
            second: string;
        }

        func main() -> int {
            let p: Pair* = new Pair("a", "b");
            drop p;
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    first_release = c_code.find("rt_string_release(p->first);")
    second_release = c_code.find("rt_string_release(p->second);")
    assert first_release != -1 and second_release != -1
    assert first_release < second_release


def test_codegen_line_directives_and_mangling(codegen_single):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        let static: int = 1;

        func f(inline: int) -> int {
            let l0_val: int = inline;
            let _tmp: int = l0_val;
            return _tmp;
        }

        func main() -> int { return f(1); }
        """,
    )

    if c_code is None:
        return

    assert "#line" in c_code
    assert ".l0\"" in c_code
    assert "l0_main_l0_kw_static" in c_code
    assert "inline__v" in c_code
    assert "l0_val__v" in c_code
    assert "_tmp__v" in c_code


# ---------------------------------------------------------------------------
# Runtime-backed tests
# ---------------------------------------------------------------------------


def test_codegen_runtime_match_output(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        extern func rt_print_int(x: int) -> void;
        extern func rt_println() -> void;

        enum Option { None; Some(value: int); }

        func main() -> int {
            let opt: Option = Some(42);
            match (opt) {
                None => { rt_print_int(0); rt_println(); }
                Some(v) => { rt_print_int(v); rt_println(); }
            }
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr
    assert stdout.strip() == "42"


def test_codegen_runtime_short_circuiting(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        extern func rt_print_int(x: int) -> void;

        func side() -> bool {
            rt_print_int(1);
            return true;
        }

        func main() -> int {
            let x: bool = false && side();
            if (x) { rt_print_int(2); }
            return 0;
        }
        """,
    )

    if c_code is None:
        return

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert ok, stderr
    assert stdout.strip() == ""


def test_codegen_runtime_integer_overflow_panics(codegen_single, compile_and_run, tmp_path):
    c_code, _ = codegen_single(
        "main",
        """
        module main;

        func main() -> int {
            let x: int = 2147483647;
            let y: int = x + 1;
            return y;
        }
        """,
    )

    if c_code is None:
        return

    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert not ok
    assert "integer addition overflow" in stderr
